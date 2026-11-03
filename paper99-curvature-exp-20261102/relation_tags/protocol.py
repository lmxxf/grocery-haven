"""Frozen plain-text relationship-label protocol; same example bodies in every 3-shot cell."""
import sys,re,json,hashlib,random
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PARENT=ROOT.parent
sys.path.insert(0,str(PARENT))
import run_curvature_experiments as core
SHOTS=[('今天出门前看到下雨，应该带什么？','带上雨伞。'),('用完一本书后放在哪里比较整齐？','放回书架。'),('手机电量快用完了，该怎么办？','给手机充电。')]
CONDITIONS=[
 dict(id='qa_3',left='问',right='答',sep='：',shots=3),
 dict(id='qa_0',left='问',right='答',sep='：',shots=0),
 dict(id='service_zh',left='用户',right='助手',sep='：',shots=3),
 dict(id='service_en',left='User',right='Assistant',sep=': ',shots=3),
 dict(id='boss',left='老板',right='员工',sep='：',shots=3),
 dict(id='mother_zh',left='妈妈',right='我',sep='：',shots=3),
 dict(id='mother_en',left='Mother',right='I',sep=': ',shots=3),
 dict(id='partner',left='爱人',right='我',sep='：',shots=3),
 dict(id='friend',left='朋友',right='我',sep='：',shots=3)]
QUESTIONS=[]
for pair,kind,bad,good,trigger,ctrl in core.PAIRS:
 QUESTIONS.append(dict(id='trap_'+pair,family='trap',pair=pair,kind=kind,text=bad,trigger=trigger,target=True,unique_id=pair,ambiguous=pair=='space_shirt'))
for key,text,reason,answer in core.LOGIC:
 QUESTIONS.append(dict(id='logic_'+key,family='logic',pair=key,kind='logic',text=text,target=True,unique_id='fact_age' if key=='age' else 'logic_'+key,gold=answer,ambiguous=False))
for pair in ['space_table','space_wall','fact_age']:
 p=next(x for x in core.PAIRS if x[0]==pair)
 QUESTIONS.append(dict(id='control_'+pair,family='control',pair=pair,kind=p[1],text=p[3],trigger=p[5],target=False,unique_id='control_'+pair,ambiguous=False))
QUESTION_LABELS={c['left'].casefold() for c in CONDITIONS}|{'问题','question','人类','human'}
ALL_LABELS=sorted({c[k] for c in CONDITIONS for k in ['left','right']}|{'问题','回答','Question','Answer','人类','AI'},key=len,reverse=True)
ROLE_RE=re.compile(r'(?m)^[ \t]*(?:\*\*)?('+ '|'.join(re.escape(s) for s in ALL_LABELS)+r')(?:\*\*)?[ \t]*[:：][ \t]*(?:\*\*)?',re.I)

def render(c,q):
 parts=[]
 for ask,answer in SHOTS[:c['shots']]:parts.append(c['left']+c['sep']+ask+'\n'+c['right']+c['sep']+answer)
 parts.append(c['left']+c['sep']+q['text']+'\n'+c['right']+c['sep'])
 return '\n\n'.join(parts)

def cases():
 out=[]
 for c in CONDITIONS:
  for q in QUESTIONS:
   out.append(dict(id='rel_'+c['id']+'__'+q['id'],condition=c,question=q,prompt=render(c,q)))
 random.Random(20261103).shuffle(out)
 return out

def save_protocol():
 data=dict(shots=SHOTS,conditions=CONDITIONS,questions=QUESTIONS,cases_per_model=len(cases()),target_cases_per_model=99,control_cases_per_model=27,models=['Qwen3.5-35B-A3B-Base','Qwen3-0.6B','Qwen3.5-35B-A3B'],max_new_tokens=160,greedy=True,seed=0,case_order_seed=20261103,expected_target_unique=10,unambiguous_target_unique=9,age_duplicate_note='trap_fact_age and logic_age have the same input; run both but deduplicate aggregate target accuracy.',shirt_note='Action feasibility depends on clothing/openings; report task-expected rejection separately and exclude from hard-core aggregate.',repeat_definition='1 - unique token 4-grams / all token 4-grams, computed separately for first turn and full continuation; >=0.5 is a descriptive repeat threshold, not proof of an infinite loop.',accuracy_policy='Primary: visible first-turn core answer correct, with incomplete/contradictory/ambiguous categories retained. Full continuation separately checked for correction/contradiction and speaker pollution.',delimiter_note='Chinese conditions share fullwidth colon/no added space; English conditions share ASCII colon+space. Only label pairs change within each language; cross-language effects include orthography/tokenization.',role_labels=ALL_LABELS,ordinary_text_only=True)
 (ROOT/'protocol.json').write_text(json.dumps(data,ensure_ascii=False,indent=2));return data
if __name__=='__main__':print(json.dumps(save_protocol(),ensure_ascii=False,indent=2))
