#!/usr/bin/env python3
"""Frozen probe construction, one model load, 64-layer ICA kinship experiment."""
import os,sys,json,time,gzip,hashlib,itertools,gc,re
from pathlib import Path
from collections import Counter
import numpy as np
ROOT=Path('/home/lmxxf/work/ica-lens-qwen38-27b-v3'); OUT=Path(__file__).resolve().parent
ASSET=ROOT/'hf_clean_upload';sys.path.insert(0,str(ROOT))
os.environ['TRITON_CACHE_DIR']=str(ROOT/'triton_cache')
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
def save(name,obj):
 p=OUT/name;p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False))
def load(p):return json.loads(Path(p).read_text())
FRAMES=[
'今年春节回老家团聚的时候，我在大门口遇到了许久未见的{W}',
'翻开书房抽屉里那本泛黄的老相册，站在第一排中间微笑的亲人是我的{W}',
'周末家里办酒席请客吃饭，正在大厅里热情招呼客人的那位亲人是我的{W}',
'昨天傍晚家里接到一通长途电话，原来是远在外地生活的{W}',
'小时候每逢寒暑假去亲戚家小住，平时跟我关系最亲近的亲人是{W}']
S1=[('伯父','舅舅'),('叔父','姨夫'),('姑姑','姨妈'),('堂哥','表哥'),('堂姐','表姐'),('堂弟','表弟')]
S2=[('伯父','舅舅'),('叔叔','姨夫'),('姑姑','姨妈')]
H1=[('爷爷','姥爷'),('爷爷','外公'),('奶奶','姥姥'),('奶奶','外婆'),('侄子','外甥'),('侄女','外甥女'),('孙子','外孙'),('孙女','外孙女')]
HG={'no_outer':[('爷爷','姥爷'),('奶奶','姥姥')], 'cousins':[('堂哥','表哥'),('堂姐','表姐'),('堂弟','表弟'),('堂妹','表妹')], 'outer':[('爷爷','外公'),('奶奶','外婆'),('侄子','外甥'),('侄女','外甥女'),('孙子','外孙'),('孙女','外孙女')]}
QUERY='内 外 里 表 内部 外部 宗 族 祠 姓 本家 娘家 外戚 inner outer inside outside internal external domestic foreign'.split()
def construct():
 probes=[]; lookup={};groups={};pairs=[]
 def probe(text,target,lang):
  key=(text,target)
  if key not in lookup:
   lookup[key]=len(probes);probes.append(dict(id=len(probes),text=text,target=target,lang=lang))
  return lookup[key]
 def pair(group,cluster,frame,a,b,ta,tb,lang,**meta):
  x=dict(group=group,cluster=cluster,frame=frame,a=probe(a,ta,lang),b=probe(b,tb,lang),**meta)
  groups.setdefault(group,[]).append(len(pairs));pairs.append(x)
 for g,ps in dict(S1=S1,S2=S2,H1=H1,**HG).items():
  for a,b in ps:
   for j,f in enumerate(FRAMES):pair(g,a+'/'+b,j,f.format(W=a),f.format(W=b),a,b,'zh')
 enframes=[
 'At the family gathering last Sunday, I spent the afternoon talking with {rel}, who has always been my favorite {word}',
 'While looking through an old photo album, I found a picture of {rel}, whom I have always known as my {word}',
 'During our summer holiday, I stayed for several days with {rel}, who is a very thoughtful {word}',
 'Yesterday I received a long letter from {rel}, who has always been a particularly kind {word}',
 'When our relatives gathered for dinner, I sat beside {rel}, who has always been my closest {word}']
 relations=[('brother','uncle','male'),('sister','aunt','female'),("brother's son",'cousin','male'),('father','grandfather','male'),('mother','grandmother','female')]
 for rel,w,gender in relations:
  for j,f in enumerate(enframes):pair('EN_A',w,j,f.format(rel="my father's "+rel,word=w),f.format(rel="my mother's "+rel,word=w),w,w,'en',gender=gender)
 gendercases=[
 ('Yesterday afternoon I had a long conversation with my ','father','mother'),
 ('The person standing near the window is a ','man','woman'),
 ('I went hiking with my elder ','brother','sister'),
 ('The child who won the school prize was a ','boy','girl'),
 ('The doctor treating the patient is ','male','female'),
 ('At the ceremony I was introduced to her ','husband','wife'),
 ('Everyone in the village respected the ','king','queen'),
 ('We received a friendly visit from the ','prince','princess'),
 ('The lead character in the novel is an ','actor','actress'),
 ('The child in the photograph is their ','son','daughter')]
 for j,(f,a,b) in enumerate(gendercases):pair('EN_B',a+'/'+b,j,f+a,f+b,a,b,'en')
 names=[('David','John','Mary','Miller','Clark'),('Daniel','James','Susan','Wilson','Baker'),('Michael','William','Linda','Taylor','Morgan'),('Andrew','Thomas','Helen','Walker','Reed'),('Peter','George','Alice','Harris','Scott')]
 for j,(child,dad,mom,pa,ma) in enumerate(names):
  for w,first in [('uncle','Robert'),('aunt','Elizabeth'),('cousin','Alex')]:
   prefix=f'My name is {child} {pa}, the son of {dad} {pa} and {mom} {ma}. During the summer holiday, I met {first} {pa} and {first} {ma}. '
   a=prefix+f'{first} {ma} is a family friend, whereas {first} {pa} is my {w}'
   b=prefix+f'{first} {pa} is a family friend, whereas {first} {ma} is my {w}'
   assert Counter(re.findall(r"\w+|[^\w\s]",a))==Counter(re.findall(r"\w+|[^\w\s]",b))
   pair('EN_C',pa+'/'+ma,j,a,b,w,w,'en',surname_set=j,relation=w)
 physical=[('把木箱搬进院子里面','把木箱搬到院子外面','里面','外面','zh'),('钥匙放在盒子内部','钥匙放在盒子外部','内部','外部','zh'),('请在房屋里面等待','请在房屋外面等待','等待','等待','zh'),('We walked into the inner room','We walked out to the outer yard','room','yard','en'),('The mark is on the inside','The mark is on the outside','inside','outside','en')]
 social=[('这件家务事只能告诉自家人','这件家务事千万别告诉外人','自家人','外人','zh'),('这次讨论只邀请圈内人','这次讨论也邀请圈外人','圈内人','圈外人','zh'),('他一直被大家当作自己人','他一直被大家当作外人','自己人','外人','zh'),('He is a trusted member of the inner circle','He is a stranger from the outer world','circle','world','en'),('She is regarded as an insider','She is regarded as an outsider','insider','outsider','en')]
 for g,items in [('physical',physical),('social',social)]:
  for j,(a,b,ta,tb,lang) in enumerate(items):pair(g,str(j),j,a,b,ta,tb,lang)
 return probes,pairs,groups

def prepare(tok):
 probes,pairs,groups=construct();cuts={}
 for p in probes:
  suffix=(' ' if p['lang']=='en' else '')+p['target'];assert p['text'].endswith(suffix)
  prefix=p['text'][:-len(suffix)];tail=tok.encode(suffix,add_special_tokens=False)
  seq=tok.encode(prefix,add_special_tokens=False)+tail
  assert tok.decode(seq)==p['text'];assert not set(seq)&set(tok.all_special_ids)
  p.update(input_ids=seq,target_start=len(seq)-len(tail),target_ids=tail,target_tokens=tok.convert_ids_to_tokens(tail),target_decoded=[tok.decode([i]) for i in tail])
  cuts[(p['lang'],p['target'])]=dict(lang=p['lang'],target=p['target'],ids=tail,tokens=p['target_tokens'],decoded=p['target_decoded'])
 for f in FRAMES:assert not any(c in f for c in '爸妈父母姓')
 for q in QUERY:
  for text in [q, ' '+q] if q.isascii() else [q]:
   ids=tok.encode(text,add_special_tokens=False);cuts[('query',text)]={'lang':'query','target':text,'ids':ids,'tokens':tok.convert_ids_to_tokens(ids),'decoded':[tok.decode([i]) for i in ids]}
 for c in cuts.values():print('TOKEN',json.dumps(c,ensure_ascii=False),flush=True)
 save('tokenization.json',list(cuts.values()));save('probes.json',probes);save('pairs.json',pairs);save('groups.json',groups)
 return probes,pairs,groups

def vector_stats(z,pairs,indices):
 a=np.array([p['a'] for p in (pairs[i] for i in indices)]);b=np.array([p['b'] for p in (pairs[i] for i in indices)])
 x=z[a].astype('float64');y=z[b].astype('float64');diff=x-y;n=len(a);mu=diff.mean(0);sd=diff.std(0,ddof=1)
 dz=np.divide(mu,sd,out=np.zeros_like(mu),where=sd>1e-12);t=dz*np.sqrt(n)
 pooled=np.sqrt((x.var(0,ddof=1)+y.var(0,ddof=1))/2);d=np.divide(mu,pooled,out=np.zeros_like(mu),where=pooled>1e-12)
 return dict(mu=mu,dz=dz,t=t,d=d,diff=diff,x=x,y=y)
def bh(p):
 idx=np.argsort(p);q=np.empty_like(p);q[idx]=np.minimum(1,np.minimum.accumulate((p[idx]*len(p)/np.arange(1,len(p)+1))[::-1])[::-1]);return q

def measure(st,c,sign,pairs,indices):
 from scipy.stats import t as student,binomtest
 dif=st['diff'][:,c]*sign;n=len(dif);ok=int((dif>0).sum());cl={}
 for value,i in zip(dif,indices):cl.setdefault(pairs[i]['cluster'],[]).append(float(value))
 cm=np.array([np.mean(v) for v in cl.values()]);nc=len(cm);pcluster=None
 if 1<nc<=12:
  flips=np.array(list(itertools.product([-1,1],repeat=nc)));null=np.abs(flips@cm/nc);pcluster=float(np.mean(null>=abs(cm.mean())-1e-12))
 return dict(n=n,correct=ok,ties=int((dif==0).sum()),accuracy=ok/n,delta=float(st['mu'][c]),oriented_delta=float(st['mu'][c]*sign),d=float(st['d'][c]*sign),dz=float(st['dz'][c]*sign),t=float(st['t'][c]*sign),p_nominal=float(2*student.sf(abs(st['t'][c]),n-1)),pair_differences=dif.tolist(),clusters=cl,cluster_correct=int((cm>0).sum()),cluster_n=nc,cluster_exact_signflip_p=pcluster,binomial_p_descriptive=float(binomtest(ok,n,.5,alternative='greater').pvalue))

def analyze_layer(z,zm,pairs,groups,kurt,layer):
 from scipy.stats import t as student
 stats={g:vector_stats(z,pairs,ii) for g,ii in groups.items()};mstats={g:vector_stats(zm,pairs,ii) for g,ii in groups.items()}
 rec={'layer':layer,'selectors':{},'independent_top1':{}}
 for g in ['EN_A','EN_B','EN_C','physical','social']:
  st=stats[g];cs={'delta':int(np.abs(st['mu']).argmax()),'t':int(np.abs(st['t']).argmax())}
  rec['independent_top1'][g]={key:dict(axis=c,kurtosis=float(kurt[c]),delta=float(st['mu'][c]),d=float(st['d'][c]),t=float(st['t'][c])) for key,c in cs.items()}
 for selector in ['S1','S2']:
  st=stats[selector];pval=2*student.sf(np.abs(st['t']),len(groups[selector])-1);q=bh(pval); rr={}
  for method,criterion in [('delta',np.abs(st['mu'])),('t',np.abs(st['t']))]:
   ranked=np.argsort(-criterion)[:3];top=[]
   for rank,c0 in enumerate(ranked):
    c=int(c0);sign=float(np.sign(st['mu'][c]) or 1);r=dict(axis=c,rank=rank+1,sign=sign,kurtosis=float(kurt[c]),fit=measure(st,c,sign,pairs,groups[selector]),fit_q_BH_5120=float(q[c]),groups={g:measure(s,c,sign,pairs,groups[g]) for g,s in stats.items() if g not in ['S1','S2']},mean_token_groups={g:measure(s,c,sign,pairs,groups[g]) for g,s in mstats.items() if g not in ['S1','S2']})
    for g in ['EN_A','EN_C']:
     r[g+'_subgroups']={}
     labels=sorted({pairs[i].get('relation',pairs[i]['cluster']) for i in groups[g]})
     for label in labels:
      ix=[i for i in groups[g] if pairs[i].get('relation',pairs[i]['cluster'])==label]
      r[g+'_subgroups'][label]=measure(vector_stats(z,pairs,ix),c,sign,pairs,ix)
    top.append(r)
   rr[method]=top
  rr['delta_t_same']=rr['delta'][0]['axis']==rr['t'][0]['axis'];rr['mean_token_top1']={method:int(np.abs(mstats[selector]['mu' if method=='delta' else 't']).argmax()) for method in ['delta','t']}
  rec['selectors'][selector]=rr
 return rec

def choose_representatives(results):
 # English and controls are never used in this selection. Chinese holdout screening is explicit.
 candidates=[]
 for r in results:
  if 24<=r['layer']<=46:
   for sel in ['S1','S2']:
    for method in ['delta','t']:
     v=r['selectors'][sel][method][0];gs=['H1'] if sel=='S1' else ['no_outer','cousins','outer']
     score=(min(v['groups'][g]['accuracy'] for g in gs),np.mean([v['groups'][g]['d'] for g in gs]))
     candidates.append((score,r['layer'],sel,method,v))
 candidates.sort(key=lambda x:x[0],reverse=True);out=[];layers=set()
 for _,l,s,m,v in candidates:
  if l in layers:continue
  layers.add(l);out.append(dict(layer=l,selector=s,method=m,axis=v['axis'],sign=v['sign']))
  if len(out)==3:break
 return out

def readout(model,tok,reps):
 import torch
 from safetensors.torch import load_file
 archive=torch.load(ROOT/'readouts/lens_n100.pt',map_location='cpu',weights_only=True,mmap=True);result=[]
 manifest=load(ASSET/'icalens.json')
 for rep in reps:
  l=rep['layer'];c=rep['axis'];asset=load_file(str(ASSET/manifest['layers'][str(l)]['file']))
  writing=asset['writing_matrix'][:,c].float().cuda();mapping=archive['J'].get(l,archive['J'].get(str(l))) if l!=63 else torch.eye(5120)
  mapped=mapping.float().cuda()@writing
  with torch.inference_mode():
   h=model.model.norm(mapped.to(torch.bfloat16)[None,None,:]);scores=model.lm_head(h)[0,0].float().cpu().numpy()
  def entry(i):return dict(token_id=int(i),token=tok.convert_ids_to_tokens(int(i)),text=tok.decode([int(i)]),score=float(scores[i]))
  top=np.argsort(-scores)[:25];bottom=np.argsort(scores)[:25];queries=[]
  for word in QUERY:
   for text in [word,' '+word] if word.isascii() else [word]:
    ids=tok.encode(text,add_special_tokens=False);items=[]
    for i in ids:items.append(dict(**entry(i),rank_descending=int((scores>scores[i]).sum()+1),percentile_lower=float((scores<scores[i]).mean()*100)))
    queries.append(dict(query=text,is_single_token=len(ids)==1,tokens=items))
  profile=json.loads(gzip.decompress((ASSET/manifest['layers'][str(l)]['component_profile']).read_bytes()))['components'][c]
  # Match the native BF16 readout to the published stored top20 (tie order may differ).
  old=profile['additional_readouts']['J Lens']['positive']['top_tokens'];err=max(abs(scores[e['token_id']]-e['logit']) for e in old)
  result.append(dict(**rep,positive_top25=[entry(i) for i in top],negative_top25=[entry(i) for i in bottom],queries=queries,profile=profile,stored_top20_max_score_error=float(err)))
  print('READOUT',l,c,'stored_error',err,flush=True);del asset,profile;gc.collect()
 save('representative_readouts.json',result);return result

def fmt(x):return f'{x:.4g}'
def acc(g):return f"{g['correct']}/{g['n']}"
def report(results,reps,readouts,probes,pairs,groups,meta):
 lines=['# Exp1a：亲属词、跨语言与内外共轴实验','',f"运行时间：{meta.get('finished','')}；{len(probes)} 条唯一裸文本，{len(pairs)} 个配对记录；模型只加载一次。",'', '## 方法与口径','',
'模型为本地 Qwen3.8-27B-FP8，按 v3 原加载器逐块解量化至 BF16；64 层编号为 block 输出 L00–L63。不加 BOS/EOS，不加对话模板，无 padding。前缀与目标词后缀分别分词后拼接，与 v3 polysemy 一致；英文后缀包含前导空格。主读数取目标词末 token，稳健性读数先将目标词各 token 的原始残差取均值，再执行同一投影。',
'公式：`u=h/max(||h||₂,1e-12)`，`z=(u-center) @ reading_matrix.T`。保留 v3 原轴编号和正负号；每个选择器仅由训练词对决定方向 `sign=sign(Δz_fit)`，所有留出和英文读数按该方向判符号。表内 Δfit 是原轴有符号值，留出 Δ 和效应量均按训练方向定向。κ 为原 v3 136.6 万词独立测试集的超额峰度。',
'选轴 delta 最大化 |平均配对差|；t 最大化 |配对t|。`d_z=mean(P-M)/sd(P-M)`，`t=d_z*sqrt(n)`，二者选轴相同。表中 d 是两组样本标准差合并后的 Cohen’s d，另保留 d_z。Top2/3 为各训练准则的独立排序，未用留出重选轴；原始 JSON 包含三根轴全部留出结果、名义 p 和训练 5120 轴 BH q。',
'五句框为重复测量；报告逐句符号准确率，并按词对聚合做精确双侧 sign-flip 检验。S2 仅三个训练词对，聚合检验最小 p=0.25。跨层和代表层搜索未作为预注册显著性检验；代表层仅按 L24–L46 中文留出最低组准确率、再按平均 d 排序选出三个不同层，英文与空间对照从未参与选层。',
'EN-C 同时给出父母姓名及两位同名候选亲戚，交换 friend/uncle(aunt/cousin) 关系位置；每对完整文本词袋相同，末词相同。测量的是姓氏与关系绑定带来的响应。EN-B 方向是男性减女性。',
'ICA 不同坐标轴并不自动等于原残差欧氏正交；报告 reading 行夹角与 writing 列夹角，以及是否同轴。空间和社会对照按各自全部五对选轴，只作描述性反查。','', '## 核心数字','']
 for rep in reps:
  r=results[rep['layer']];v=r['selectors'][rep['selector']][rep['method']][0]
  lines += [f"- L{rep['layer']:02d} C{rep['axis']}（{rep['selector']}/{rep['method']}，κ={fmt(v['kurtosis'])}）：H1 {acc(v['groups']['H1'])}，S2无外字 {acc(v['groups']['no_outer'])}、堂表 {acc(v['groups']['cousins'])}、外字 {acc(v['groups']['outer'])}；EN-A {acc(v['groups']['EN_A'])}，EN-C {acc(v['groups']['EN_C'])}，性别对照 Δ={fmt(v['groups']['EN_B']['oriented_delta'])}。"]
 lines+=['','## 中文全部64层：双选择器×双准则','', '列 ΔH/dH/AccH：S1 为 H1；S2 分别列无外字/堂表/外字三组。`Top2/3` 列为轴ID、训练BH q、H1准确率；完整其余分组数值见后表和 JSON。','']
 for sel in ['S1','S2']:
  for method in ['delta','t']:
   lines += [f'### {sel} / {method}','', '|L|C|κ|Δfit|t_fit|d_fit|ΔH|dH|AccH|同另一准则|均值token选轴|Top2/3 (C,q,H1)|','|---|---|---|---|---|---|---|---|---|---|---|---|']
   for r in results:
    rr=r['selectors'][sel];v=rr[method][0];gs=['H1'] if sel=='S1' else ['no_outer','cousins','outer']
    vals=lambda key:'/'.join(fmt(v['groups'][g][key]) for g in gs)
    other='; '.join(f"C{x['axis']},q={fmt(x['fit_q_BH_5120'])},{acc(x['groups']['H1'])}" for x in rr[method][1:])
    lines.append(f"|{r['layer']:02d}|{v['axis']}|{fmt(v['kurtosis'])}|{fmt(v['fit']['delta'])}|{fmt(v['fit']['t'])}|{fmt(v['fit']['d'])}|{vals('oriented_delta')}|{vals('d')}|{'/'.join(acc(v['groups'][g]) for g in gs)}|{rr['delta_t_same']}|{rr['mean_token_top1'][method]}|{other}|")
   lines.append('')
 lines += ['## 各层跨语言、性别与内外对照全表','', '每格为准确数/总数；Δ；Cohen d。EN-B 为男性减女性的符号，准确率不是阴性对照成功标准，应看其偏移是否接近零。','']
 for sel in ['S1','S2']:
  for method in ['delta','t']:
   lines += [f'### {sel}/{method}','', '|L/C|EN-A|EN-B性别|EN-C姓氏|物理内外|社会内外|EN-A自选C(Δ/t)|EN-C自选C(Δ/t)|物理自选C(Δ/t)|社会自选C(Δ/t)|','|---|---|---|---|---|---|---|---|---|---|']
   for r in results:
    v=r['selectors'][sel][method][0];cells=[]
    for g in ['EN_A','EN_B','EN_C','physical','social']:
     x=v['groups'][g];cells.append(f"{acc(x)};{fmt(x['oriented_delta'])};{fmt(x['d'])}")
    for g in ['EN_A','EN_C','physical','social']:cells.append('/'.join(str(r['independent_top1'][g][m]['axis']) for m in ['delta','t']))
    lines.append('|'+f"{r['layer']:02d}/{v['axis']}|"+'|'.join(cells)+'|')
   lines.append('')
 for rd in readouts:
  l=rd['layer'];c=rd['axis'];r=results[l];v=r['selectors'][rd['selector']][rd['method']][0]
  lines += [f'## 代表层 L{l:02d} C{c}：双镜原词与语料','',f"中文训练方向 sign={rd['sign']:+g}；以下 J-Lens 正负极保持原 v3 轴号方向，不随中文方向翻转。重算 Top25 与原 profile Top20 分数最大差 {rd['stored_top20_max_score_error']:.6g}。",'', '|排名|正极token ID / 原词 / 分数|负极token ID / 原词 / 原轴分数|','|---|---|---|']
  for j,(a,b) in enumerate(zip(rd['positive_top25'],rd['negative_top25'])):
   def cell(x):return f"{x['token_id']} / {json.dumps(x['text'],ensure_ascii=False)} / {fmt(x['score'])}".replace('|','\\|')
   lines.append(f'|{j+1}|{cell(a)}|{cell(b)}|')
  lines+=['','### 定向词表查询','', '多token查询逐token列出，未把分词均值冒充完整词词表得分；英文同时查无空格/前导空格版本。百分位为全词表严格低于该token分数的比例。','', '|查询|token ID / 原词|score|降序排名|百分位|','|---|---|---|---|---|']
  for q in rd['queries']:
   for x in q['tokens']:lines.append(f"|{json.dumps(q['query'],ensure_ascii=False)}|{x['token_id']} / {json.dumps(x['text'],ensure_ascii=False)}|{fmt(x['score'])}|{x['rank_descending']}|{x['percentile_lower']:.3f}%|")
  lines+=['','### 原测试语料最高正负例句','']
  for side in ['positive','negative']:
   lines+=['**'+side+'**',''];occ=rd['profile']['examples'].get(side,{}).get('occurrences',[])
   if not occ:lines+=['原 component_profile 此侧未存例句。','']
   for x in occ[:5]:lines.append(f"- z={fmt(x['score'])}，token={json.dumps(x['text'],ensure_ascii=False)}：{json.dumps(x['context'],ensure_ascii=False)}")
   lines.append('')
  lines+=['### 留出、英文细分与均值token稳健性','', '|组|末token Acc|Δ|d|d_z|聚合词对Acc|聚合置换p|均值token Acc|均值Δ|均值d|','|---|---|---|---|---|---|---|---|---|---|']
  for g,x in v['groups'].items():
   m=v['mean_token_groups'][g];lines.append(f"|{g}|{acc(x)}|{fmt(x['oriented_delta'])}|{fmt(x['d'])}|{fmt(x['dz'])}|{x['cluster_correct']}/{x['cluster_n']}|{x['cluster_exact_signflip_p']}|{acc(m)}|{fmt(m['oriented_delta'])}|{fmt(m['d'])}|")
  for g in ['EN_A','EN_C']:
   for sub,x in v[g+'_subgroups'].items():lines.append(f"|{g}:{sub}|{acc(x)}|{fmt(x['oriented_delta'])}|{fmt(x['d'])}|{fmt(x['dz'])}|{x['cluster_correct']}/{x['cluster_n']}|{x['cluster_exact_signflip_p']}|—|—|—|")
  lines+=['','### 与反查轴的夹角','', '|对照|准则|C|同亲属轴|reading cosine|writing cosine|','|---|---|---|---|---|---|']
  for x in rd['axis_geometry']:lines.append(f"|{x['group']}|{x['method']}|{x['axis']}|{x['axis']==c}|{fmt(x['reading_cosine'])}|{fmt(x['writing_cosine'])}|")
  lines.append('')
 lines+=['## 探针与可复现资产','', '五个中文句框：','']+[f'{i+1}. {f}' for i,f in enumerate(FRAMES)]+['', '真实分词表：','', '|语言|目标|token IDs|逐token解码|','|---|---|---|---|']
 for x in load(OUT/'tokenization.json'):lines.append(f"|{x['lang']}|{json.dumps(x['target'],ensure_ascii=False)}|{x['ids']}|{json.dumps(x['decoded'],ensure_ascii=False)}|")
 lines+=['','文件：`run_exp1a.py`（执行全管线）、`probes.json`（含原文/完整ids/目标span）、`pairs.json`、`groups.json`、`tokenization.json`、`results_all_layers.json`（64层Top3全部统计与逐对差）、`representative_readouts.json`（原token、全查询与原profile）、`representative_raw_scores.json`（每条探针代表轴原始z）、`activations_last.npy` / `activations_mean.npy`（float32原残差）、`z_last.npy` / `z_mean.npy`（float32全轴坐标）、`run_metadata.json`、`run.log`。','', '运行：`/home/lmxxf/work/interp-curvature-exp/venv/bin/python run_exp1a.py`；已有全量激活时 `--analyze` 仅重算统计报告，不加载模型。']
 (OUT/'report_exp1a.md').write_text('\n'.join(lines)+'\n')

def main():
 import torch
 from transformers import AutoTokenizer
 from safetensors.torch import load_file
 torch.set_num_threads(8);torch.set_float32_matmul_precision('highest')
 tok=AutoTokenizer.from_pretrained('/home/lmxxf/work/models/Qwen3.8-27B-FP8',local_files_only=True)
 probes,pairs,groups=prepare(tok);n=len(probes);start=time.time();model=None
 if '--analyze' not in sys.argv:
  from model_loader import load_model
  tok,model=load_model();last=np.lib.format.open_memmap(OUT/'activations_last.npy',mode='w+',dtype='float32',shape=(64,n,5120));mean=np.lib.format.open_memmap(OUT/'activations_mean.npy',mode='w+',dtype='float32',shape=(64,n,5120));current=[0,0]
  handles=[]
  for l,block in enumerate(model.model.layers):
   def hook(m,i,o,l=l):
    h=(o[0] if isinstance(o,tuple) else o)[0];j,k=current
    last[l,j]=h[-1].float().cpu().numpy();mean[l,j]=h[k:].float().mean(0).cpu().numpy()
   handles.append(block.register_forward_hook(hook))
  with torch.inference_mode():
   for j,p in enumerate(probes):
    current[:]=[j,p['target_start']];model.model(input_ids=torch.tensor([p['input_ids']],device='cuda'),use_cache=False)
    if j%10==0 or j==n-1:
     status=dict(stage='forward',done=j+1,total=n,seconds=time.time()-start);save('progress.json',status);print('FORWARD',status,flush=True)
  for h in handles:h.remove()
  last.flush();mean.flush();save('forward_complete.json',dict(n=n,seconds=time.time()-start,model_loads=1))
 else:
  last=np.load(OUT/'activations_last.npy',mmap_mode='r');mean=np.load(OUT/'activations_mean.npy',mmap_mode='r')
 zall=np.lib.format.open_memmap(OUT/'z_last.npy',mode='w+',dtype='float32',shape=(64,n,5120));zmean=np.lib.format.open_memmap(OUT/'z_mean.npy',mode='w+',dtype='float32',shape=(64,n,5120));results=[];manifest=load(ASSET/'icalens.json')
 for l in range(64):
  asset=load_file(str(ASSET/manifest['layers'][str(l)]['file']),device='cuda');C=asset['reading_matrix'];center=asset['center']
  for a,out in [(last,zall),(mean,zmean)]:
   x=torch.tensor(np.array(a[l]),device='cuda');y=(x/x.norm(dim=1,keepdim=True).clamp_min(1e-12)-center)@C.T;out[l]=y.cpu().numpy()
  stats=load(ROOT/f'L{l:02d}/statistics.json');kurt=stats['test']['excess_kurtosis']
  results.append(analyze_layer(zall[l],zmean[l],pairs,groups,kurt,l));del asset,C,center,x,y;gc.collect()
  print('ANALYZED',l,flush=True);save('progress.json',dict(stage='analysis',done=l+1,total=64))
 zall.flush();zmean.flush();save('results_all_layers.json',results);reps=choose_representatives(results);save('representatives.json',reps)
 if model is not None:readouts=readout(model,tok,reps)
 else:readouts=load(OUT/'representative_readouts.json')
 for rd in readouts:
  l=rd['layer'];c=rd['axis'];asset=load_file(str(ASSET/manifest['layers'][str(l)]['file']));C=asset['reading_matrix'].numpy();M=asset['writing_matrix'].numpy();rd['axis_geometry']=[]
  for g in ['physical','social','EN_A','EN_C']:
   for method in ['delta','t']:
    c2=results[l]['independent_top1'][g][method]['axis'];cos=lambda a,b:float(a@b/(np.linalg.norm(a)*np.linalg.norm(b)))
    rd['axis_geometry'].append(dict(group=g,method=method,axis=c2,reading_cosine=cos(C[c],C[c2]),writing_cosine=cos(M[:,c],M[:,c2])))
 save('representative_readouts.json',readouts)
 raw=[]
 for p in probes:
  raw.append(dict(id=p['id'],text=p['text'],values=[dict(layer=rd['layer'],axis=rd['axis'],z_last=float(zall[rd['layer'],p['id'],rd['axis']]),z_mean=float(zmean[rd['layer'],p['id'],rd['axis']])) for rd in readouts]))
 save('representative_raw_scores.json',raw)
 meta=dict(finished=time.strftime('%Y-%m-%d %H:%M:%S %z'),seconds=time.time()-start,probes=n,pair_records=len(pairs),model_loads=0 if model is None else 1,projection='FP32 highest; rowL2 -> subtract center -> reading.T',torch=torch.__version__,seed='deterministic inference; no sampling',probe_sha256=hashlib.sha256((OUT/'probes.json').read_bytes()).hexdigest())
 save('run_metadata.json',meta);report(results,reps,readouts,probes,pairs,groups,meta);save('progress.json',dict(stage='complete',report=str(OUT/'report_exp1a.md')));print('COMPLETE',meta,flush=True)
if __name__=='__main__':main()
