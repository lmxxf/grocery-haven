import ast,json,math,time
from pathlib import Path
import torch,numpy as np
import torch.nn.functional as F
from transformers import AutoModelForCausalLM,AutoTokenizer
R=Path(__file__).resolve().parent;assert 'GB10' in torch.cuda.get_device_name();torch.set_num_threads(8)
qs=[('regular_en','The sun rises in the east and sets in the west.'),('rhyme_en','One, two, buckle my shoe. Three, four, knock at the door.'),('regular_en','She opened the window and reached through it to pick up an apple.'),('regular_zh','太阳从东方升起，从西方落下。'),('rhyme_zh','吃葡萄不吐葡萄皮，不吃葡萄倒吐葡萄皮。'),('regular_zh','她站在敞开的窗户外，手臂穿过窗户，拿起桌上的苹果。'),('trap_en','A mother is 30 years old and her biological son is 35. How old was she when she gave birth?'),('trap_en','In Dream of the Red Chamber, which chapter has Lin Daiyu uprooting a willow tree?'),('trap_en','Zhuge Liang flew a J-20 jet in the Battle of Red Cliffs. How many warships did he shoot down?'),('trap_en','Two people sit at opposite ends of a ten-meter-long table. Without leaving his seat, he casually touches her hair. Is this physically reasonable?'),('trap_en','She stands outside a fully sealed glass room, with no doors or windows. Her arm does not pass through the glass, yet she directly picks up the apple inside. Is this physically possible?'),('logic_en','A racket and ball cost 110 yuan. The racket costs 100 yuan more than the ball. How much does the ball cost?'),('trap_zh','妈妈今年30岁，她亲生儿子今年35岁，请问妈妈生儿子的时候几岁？'),('trap_zh','在《红楼梦》里，林黛玉倒拔垂杨柳发生在第几回？'),('trap_zh','诸葛亮在赤壁之战中驾驶歼-20战机击落了曹操的几艘战船？'),('trap_zh','两人隔着十米宽的会议桌面对面坐着，他始终没有离开座位，却顺手揉了揉她的头发。这合理吗？'),('trap_zh','她站在完全密封且没有门窗的玻璃房外，手臂没有穿过玻璃，却直接拿起房内桌上的苹果。这合理吗？'),('logic_zh','一支球拍和一个球共110元，球拍比球贵100元，请问球多少钱？')]
qs += [('paper_figure4_prompt','When I got home, the'),('paper_figure4_prompt_trailing_space','When I got home, the ')]
nodes=[x for x in ast.parse((R/'run_reproduction.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name in ['geom','ent']];scope=dict(torch=torch,np=np,F=F,math=math);exec(compile(ast.Module(body=nodes,type_ignores=[]),'<geometry>','exec'),scope);results=[]
for name in ['pythia-2.8b','gpt2-xl']:
 tok=AutoTokenizer.from_pretrained('/home/lmxxf/work/models/'+name,local_files_only=True);m=AutoModelForCausalLM.from_pretrained('/home/lmxxf/work/models/'+name,local_files_only=True,dtype=torch.float32,device_map='cuda',attn_implementation='sdpa').eval();blocks=m.transformer.h if name=='gpt2-xl' else m.gpt_neox.layers
 for kind,text in qs:
  states={}
  def hk(l):
   def f(mod,a,o):states[l]=scope['geom']((o[0] if isinstance(o,tuple) else o).float())[0].cpu().numpy()
   return f
  handles=[b.register_forward_hook(hk(l)) for l,b in enumerate(blocks)]
  ids=tok(text,add_special_tokens=False,return_tensors='pt').input_ids.cuda()
  with torch.inference_mode():o=m(ids,use_cache=False);H=scope['ent'](o.logits[0]).cpu().numpy();probs=torch.softmax(o.logits[0,-1].float(),-1);pv,pi=torch.topk(probs,8);top=[dict(token_id=int(i),token=tok.decode([int(i)]),probability=float(v)) for v,i in zip(pv,pi)]
  for h in handles:h.remove()
  results.append(dict(model=name,kind=kind,text=text,input_ids=ids[0].tolist(),n_tokens=ids.shape[1],top8=top,H_next_bits=float(H[-1]),mean_H_bits=float(H[5:].mean()),C_last_by_layer_rad=[float(states[l][-1]) for l in range(len(blocks))],C_mean_by_layer_rad=[float(np.nanmean(states[l][5:])) for l in range(len(blocks))]))
 del m,tok;torch.cuda.empty_cache()
(R/'exploratory.json').write_text(json.dumps(dict(scope='Raw text only; no chat template, no generated answers and no accuracy/IQ inference; Chinese and English tokenization differ',records=results),ensure_ascii=False,indent=2));print('EXTRA_DONE',len(results))
