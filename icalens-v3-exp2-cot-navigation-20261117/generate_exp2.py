from common_exp2 import *
import re,math,gc
import numpy as np,torch
import torch.nn.functional as F

def hbits(logits):
 lp=F.log_softmax(logits.float(),-1);return float(-(lp.exp()*lp).sum()/math.log(2))
@torch.inference_mode()
def generate(model,tok,case):
 ident=case['id'];D=5120;prompt=tok.encode(case['prompt'],add_special_tokens=False);assert not set(prompt)&set(tok.all_special_ids)
 P=len(prompt);capacity=P+case['max_new_tokens'];directory=H/ident;directory.mkdir(exist_ok=True);raw=np.lib.format.open_memmap(directory/'residual_bf16.npy',mode='w+',dtype='uint16',shape=(64,capacity,D));capture={'buffer':torch.empty((64,P,D),dtype=torch.bfloat16,device='cuda')};handles=[]
 for l,block in enumerate(model.model.layers):
  def hook(m,i,o,l=l):capture['buffer'][l].copy_((o[0]if isinstance(o,tuple)else o)[0])
  handles.append(block.register_forward_hook(hook))
 generated=[];events=[];forced=case.get('force_eos',False);forced_at=None;forced_reason=None;first_eos=None;stop_reason='budget';start=time.time()
 eos=model.generation_config.eos_token_id;eos=set(eos if isinstance(eos,list)else[eos]);eos.update(tok.convert_tokens_to_ids(t)for t in ['<|endoftext|>','<|im_end|>']);eos.discard(None)
 role_ban=set(tok.all_special_ids)-eos
 try:
  out=model(input_ids=torch.tensor([prompt],device='cuda'),use_cache=True,logits_to_keep=1);raw[:,:P]=capture['buffer'].view(torch.uint16).cpu().numpy();cache=out.past_key_values;logits=out.logits[0,-1];capture['buffer']=torch.empty((64,1,D),dtype=torch.bfloat16,device='cuda');del out
  for step in range(case['max_new_tokens']):
   effective=logits.float().clone();effective[list(role_ban)]=-torch.inf;pre=int(effective.argmax());unmasked_top=int(logits.argmax());entropy=hbits(logits)
   if pre in eos:
    if first_eos is None:first_eos=len(generated)
    if not forced:stop_reason='eos';break
    if forced_at is None:forced_at=len(generated);forced_reason='eos_proposal'
   if forced:
    text=tok.decode(generated)
    answer=re.escape(case['expected'])
    if forced_at is None and re.search(r'(?:[）)]\s*(?:答案[是为：:\s]*)?'+answer+r'\b|答案[是为：:\s]*'+answer+r'\b)',text):forced_at=len(generated);forced_reason='explicit_answer'
    effective[list(eos)]=-torch.inf
    if forced_at is not None and len(generated)-forced_at>=case.get('extra_after_stop',96):stop_reason='forced_tail_complete';break
   nxt=int(effective.argmax());lp=F.log_softmax(logits.float(),-1)
   events.append(dict(state_position=P+len(generated)-1,generated_index=len(generated),raw_top_id=unmasked_top,after_role_filter_top_id=pre,chosen_id=nxt,H_bits=entropy,raw_chosen_logprob=float(lp[nxt]),eos_raw_probability=float(lp[list(eos)].exp().sum()),eos_suppressed=forced,forced_tail=forced_at is not None))
   generated.append(nxt);out=model(input_ids=torch.tensor([[nxt]],device='cuda'),past_key_values=cache,use_cache=True,logits_to_keep=1);cache=out.past_key_values;logits=out.logits[0,-1];pos=P+len(generated)-1;raw[:,pos:pos+1]=capture['buffer'].view(torch.uint16).cpu().numpy();del out
   if step%20==0:save('progress.json',dict(stage='generation',case=ident,generated=len(generated),seconds=time.time()-start));print('DECODE',ident,len(generated),round(time.time()-start,2),flush=True)
  terminal=dict(state_position=P+len(generated)-1,H_bits=hbits(logits),raw_top_id=int(logits.argmax()))
 finally:
  for handle in handles:handle.remove()
 raw.flush();total=prompt+generated;record=dict(**case,prompt_ids=prompt,prompt_length=P,generated_ids=generated,input_ids=total,total_tokens=len(total),generated_text=tok.decode(generated),tokens=tok.convert_ids_to_tokens(total),token_text=[tok.decode([i])for i in total],decode_events=events,terminal_prediction=terminal,first_eos_proposal=first_eos,forced_at_generated_index=forced_at,forced_reason=forced_reason,stop_reason=stop_reason,actual_extra_after_arm=None if forced_at is None else len(generated)-forced_at,seconds=time.time()-start,raw_path=str(directory/'residual_bf16.npy'),raw_capacity=capacity,seed=0,decoding='greedy; EOS allowed naturally, blocked on forced arm; other special-role tokens never fed back')
 save(f'traces/{ident}.json',record);save('progress.json',dict(stage='case_complete',case=ident,generated=len(generated),stop_reason=stop_reason));append('Step 2/3/4 真实生成｜'+ident,f"组={case['group']}；prompt {P} tokens，实际生成 {len(generated)} tokens；停止={stop_reason}；首次EOS候选={first_eos}，延长起点={forced_at}，额外实际步数={record['actual_extra_after_arm']}；耗时{record['seconds']:.1f}s。\n\n真实续写（不改字）：\n\n```text\n{record['generated_text']}\n```\n\n完整逐步概率、原始熵和EOS屏蔽记录：traces/{ident}.json。")
 del cache,logits,capture,raw;gc.collect();torch.cuda.empty_cache();return record

@torch.inference_mode()
def cached_replay_check(model,tok,record):
 n=min(record['total_tokens'],record['prompt_length']+8);ids=record['input_ids'][:n];buffer=torch.empty((64,n,5120),device='cuda',dtype=torch.bfloat16);handles=[]
 for l,block in enumerate(model.model.layers):
  def hook(m,i,o,l=l):buffer[l].copy_((o[0]if isinstance(o,tuple)else o)[0])
  handles.append(block.register_forward_hook(hook))
 try:model.model(input_ids=torch.tensor([ids],device='cuda'),use_cache=False)
 finally:
  for handle in handles:handle.remove()
 source=np.load(record['raw_path'],mmap_mode='r');a=torch.from_numpy(np.array(source[:,:n])).view(torch.bfloat16).to('cuda').float();b=buffer.float();p=record['prompt_length'];rows=[]
 for l in [0,16,32,48,63]:
  aa=a[l,p:];bb=b[l,p:];rel=float((aa-bb).norm()/aa.norm());angle=float(torch.acos(F.cosine_similarity(aa,bb).clamp(-1,1)).mean());rows.append(dict(layer=l,relative_l2=rel,mean_angle_radians=angle))
 save('cache_replay_check.json',rows);append('Step 2 排坑｜缓存解码与整段重放不是逐位同一个数',f"用{record['id']}实际生成的前8个token，与无cache整段前向对账。结果：`{json.dumps(rows,ensure_ascii=False)}`。主数据始终采用生成时捕获值；重放仅作数值核对。")
