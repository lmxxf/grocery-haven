import requests,json,hashlib,concurrent.futures,re
from pathlib import Path
from bs4 import BeautifulSoup
R=Path(__file__).resolve().parent
items={'luxun_yanyu':'諺語','luxun_manyu':'漫與','luxun_duomin':'我談「墮民」','luxun_shanghai':'上海文藝之一瞥','luxun_erchou':'二丑藝術','imperial063':'上諭内閣 (四庫全書本)/卷063'}
def job(item):
 name,title=item;url='https://zh.wikisource.org/zh-hans/'+title
 try:
  r=requests.get(url,headers={'User-Agent':'Mozilla/5.0','Accept-Encoding':'gzip, deflate'},timeout=25);r.encoding='utf8';r.raise_for_status();s=BeautifulSoup(r.text,'html.parser');node=max(s.select('.mw-parser-output'),key=lambda x:len(x.get_text()))
  for x in node.select('script,style,.ws-noexport,.noprint,.mw-editsection'):x.decompose()
  text=node.get_text('\n',strip=True);(R/'sources'/f'{name}.txt').write_text(text);(R/'sources'/f'{name}.raw').write_text(r.text)
  result=dict(name=name,title=title,url=url,chars=len(text),nucai=text.count('奴才'),sha256=hashlib.sha256(r.content).hexdigest());print(result,flush=True);return result
 except Exception as ex:print(name,repr(ex),flush=True);return dict(name=name,url=url,error=str(ex))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:a=list(pool.map(job,items.items()))
(R/'more_sources_manifest.json').write_text(json.dumps(a,ensure_ascii=False,indent=2))
