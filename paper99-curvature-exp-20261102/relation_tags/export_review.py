"""Content-based blind review: identical question/first-answer strings share one grade."""
from pathlib import Path
import json,hashlib,random,argparse
ROOT=Path(__file__).resolve().parent

def build(model=None):
 groups={};recordmap={}
 for d in sorted((ROOT/'raw').iterdir()):
  if model and d.name!=model:continue
  for p in sorted(d.glob('rel_*.json')):
   r=json.loads(p.read_text());q=r['relation_spec']['question'];answer=r['turn']['first_text']
   normalized=' '.join(answer.split())
   key=hashlib.sha256((q['text']+'\0'+normalized).encode()).hexdigest()[:14]
   if key not in groups:groups[key]=dict(blind_id=key,question=q['text'],question_id=q['id'],unique_question_id=q['unique_id'],ambiguous=q['ambiguous'],first_answer=answer,occurrences=0,examples=[])
   groups[key]['occurrences']+=1
   groups[key]['examples'].append(dict(model=d.name,record=r['id'],condition=r['group'],hit_limit=r['hit_limit'],boundary=r['turn']['boundary'],first_end_observed=r['first_turn_end_observed']))
   recordmap[d.name+'::'+r['id']]=key
 items=list(groups.values());random.Random(271828).shuffle(items)
 suffix=('-'+model) if model else ''
 visible=[{k:v for k,v in x.items() if k not in ['examples']} for x in items]
 (ROOT/('blind_review'+suffix+'.json')).write_text(json.dumps(visible,ensure_ascii=False,indent=2))
 (ROOT/('review_key'+suffix+'.json')).write_text(json.dumps(dict(groups=groups,records=recordmap),ensure_ascii=False,indent=2))
 lines=['# 去重首回合判分表','',f'记录{len(recordmap)}条，唯一问题/首答组合{len(items)}。标签与模型映射另存review_key；答复中本身可能含称呼，无法完全盲法。','']
 for x in visible:
  lines += [f'## {x["blind_id"]} / {x["question_id"]} / 复用{x["occurrences"]}次','',x['question'],'','```text',x['first_answer'],'```','']
 (ROOT/('blind_review'+suffix+'.md')).write_text('\n'.join(lines))
 print('EXPORTED',len(recordmap),'records',len(items),'unique first answers',suffix)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--model');args=ap.parse_args();build(args.model)
