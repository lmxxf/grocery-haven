"""All token positions; exact single-token ranks and 00..99 sequence ranks."""
import torch,json,time,re,gc
from pathlib import Path
QUERIES=[('tight','2*3+2=',6,8,'3','+'),('spaced','2 * 3 + 2 =',6,8,'3','+'),('fact','Fact: 2 * 3 + 2 =',6,8,'3','+'),('words','The result of two times three plus two is',6,8,'three','plus'),('zh_digits','计算：2*3+2=',6,8,'3','+'),('zh_words','计算：二乘三加二等于',6,8,'三','加'),('two_56','7*8+3=',56,59,'8','+'),('two_42','6*7+5=',42,47,'7','+'),('two_12','3*4+5=',12,17,'4','+')]
ALIASES={6:['6',' six','six','六'],8:['8',' eight','eight','八'],56:['56',' fifty-six','五十六'],59:['59',' fifty-nine','五十九'],42:['42',' forty-two','四十二'],47:['47',' forty-seven','四十七'],12:['12',' twelve','twelve','十二'],17:['17',' seventeen','seventeen','十七']}
CONCEPTS=[' Italy',' Japan',' UK','意大利','日本','英国',' spider',' ant',' dog','蜘蛛','蚂蚁','狗',' six',' ten','六','十',' bread','面包','火锅','大象',' French',' Spanish','法语','西班牙语']
@torch.inference_mode()
def run(c):
 start=time.time();cases=[];rows=[];store={l:[]for l in range(64)}
 def add(ids,all_positions):
  h=c.capture(ids,all_positions)
  offset=len(rows)
  for l in range(64):store[l].append(h[l])
  if all_positions:rows.extend([None]*len(ids))
  else:rows.append(None)
  return offset
 for name,text,mid,ans,operand,op in QUERIES:
  enc=c.tok(text,return_offsets_mapping=True,add_special_tokens=False);ids=enc['input_ids'];base=add(ids,True)
  meta={'name':name,'prompt':text,'intermediate':str(mid),'answer':str(ans),'token_ids':ids,'tokens':[c.tok.decode([x])for x in ids],'offsets':enc['offset_mapping'],'base_row':base,'conditional_rows':{},'anchors':{}}
  for label,needle in [('second_operand',operand),('plus',op)]:
   a=text.index(needle);meta['anchors'][label]=max(i for i,(x,y)in enumerate(enc['offset_mapping'])if y>a and x<a+len(needle))
  for val in [mid,ans]:meta.setdefault('single_token_aliases',{})[str(val)]={s:c.single(s)for s in ALIASES[val]}
  if mid>=10:
   for p in range(len(ids)):
    meta['conditional_rows'][str(p)]={str(d):add(ids[:p+1]+c.ids(str(d)),False)for d in range(10)}
  cases.append(meta);print('E1_CAPTURE',name,len(ids),len(rows),flush=True)
 H={l:torch.cat(h)for l,h in store.items()};del store;gc.collect()
 digits=[c.single(str(i))for i in range(10)];assert all(v is not None for v in digits)
 concept_ids={s:c.single(s)for s in CONCEPTS};concept_ids={s:i for s,i in concept_ids.items()if i is not None}
 norm=c.model.model.norm.weight.float();W=torch.stack([c.model.lm_head.weight[i].float()*norm for i in concept_ids.values()])
 result={'cases':cases,'stages':{},'numeric_sequence_definition':'p_l(d1|prefix)*p_l(d2|prefix+d1), rank over exactly 100 fixed-length strings 00..99; not vocabulary rank','readout':'all causal token positions; no chat template; layer block output before final norm','concept_dictionary_token_ids':concept_ids}
 for stage in ['vanilla','n1','n100']:
  layers={};dictionary={}
  for l in range(64):
   J=None if stage=='vanilla'or l==63 else c.checkpoints[int(stage[1:])]['J'][l].to(device='cuda',dtype=torch.float32)
   if l<63:
    V=W if J is None else W@J
    dictionary[l]={s:v.cpu()for s,v in zip(concept_ids,V)}
   digit_logp=[];base_readouts={}
   for off in range(0,len(rows),24):
    h=H[l][off:off+24].cuda();h=h if J is None else h@J.T
    logits=c.lm.unembed(h).float();den=logits.logsumexp(-1,keepdim=True)
    digit_logp.append((logits[:,digits]-den).cpu())
    for meta in cases:
     for p in range(len(meta['token_ids'])):
      idx=meta['base_row']+p
      if not off<=idx<off+len(h):continue
      z=logits[idx-off];vals,inds=z.topk(5)
      rec={'top5':[{'id':int(i),'text':c.tok.decode([int(i)]),'logit':float(v)}for i,v in zip(inds,vals)],'alias_ranks':{}}
      for val,aliases in meta['single_token_aliases'].items():
       rec['alias_ranks'][val]={s:1+int((z>z[i]).sum())for s,i in aliases.items()if i is not None}
      base_readouts[f"{meta['name']}:{p}"]=rec
    del h,logits,den
   D=torch.cat(digit_logp);layer_cases={}
   for meta in cases:
    positions=[]
    for p in range(len(meta['token_ids'])):
     rec=base_readouts[f"{meta['name']}:{p}"]
     if meta['conditional_rows']:
      joint=torch.stack([D[meta['base_row']+p,a]+D[meta['conditional_rows'][str(p)][str(a)],b]for a in range(10)for b in range(10)])
      rec['two_digit_00_99']={val:{'joint_logprob':float(joint[int(val)]),'rank':1+int((joint>joint[int(val)]).sum())}for val in [meta['intermediate'],meta['answer']]}
     positions.append(rec)
    layer_cases[meta['name']]=positions
   layers[l]=layer_cases;del J;torch.cuda.empty_cache()
   if l%16==0:print('E1_LAYER',stage,l,flush=True)
  result['stages'][stage]=layers;c.dirs[stage]=dictionary
  c.save('experiment1.json',result)
 torch.save(c.dirs,c.root/'concept_directions.pt')
 c.save('experiment1_resources.json',{'elapsed_seconds':time.time()-start,'captured_rows':len(rows),'definition':'static direction v_l(t)=J_l.T @ (FinalRMSNorm.weight * lm_head.weight[t]); actual readout uses full RMSNorm; raw dot equals logit numerator, common RMS denominator omitted from direction coordinates'})
