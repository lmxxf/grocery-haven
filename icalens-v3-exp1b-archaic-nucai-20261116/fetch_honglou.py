import requests,concurrent.futures,json,time,hashlib
from pathlib import Path
from bs4 import BeautifulSoup
R=Path(__file__).resolve().parent
(R/'sources/honglou').mkdir(exist_ok=True)
def chapter(n):
 url=f'https://zh.wikisource.org/zh-hans/紅樓夢/第{n:03d}回'
 for retry in range(3):
  try:
   r=requests.get(url,headers={'User-Agent':'Mozilla/5.0','Accept-Encoding':'gzip, deflate'},timeout=25);r.raise_for_status();r.encoding='utf-8';s=BeautifulSoup(r.text,'html.parser');nodes=s.select('.mw-parser-output');node=max(nodes,key=lambda x:len(x.get_text()))
   for x in node.select('script,style,.mw-editsection,.noprint,.ws-noexport,.header-container,.navbox'):x.decompose()
   text=node.get_text('\n',strip=True);assert len(text)>1000,(n,len(text))
   (R/'sources/honglou'/f'{n:03d}.txt').write_text(text)
   print('HONGLOU',n,len(text),flush=True)
   return dict(chapter=n,url=url,chars=len(text),sha256=hashlib.sha256(text.encode()).hexdigest())
  except Exception as e:
   if retry==2:return dict(chapter=n,url=url,error=str(e))
   time.sleep(1)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:out=list(pool.map(chapter,range(1,121)))
(R/'honglou_manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print('DONE',len(out),'errors',sum('error'in x for x in out),flush=True)
