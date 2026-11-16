import requests,json,time,hashlib,concurrent.futures
from pathlib import Path
from bs4 import BeautifulSoup
R=Path(__file__).resolve().parent
SOURCES={
'honglou_pg':'https://www.gutenberg.org/ebooks/24264.txt.utf-8',
'sanguozhi':'https://zh.wikisource.org/zh-hans/三國志/卷35',
'caojia':'https://ctext.org/wiki.pl?chapter=747644&if=gb',
'caojia_late':'https://ctext.org/wiki.pl?chapter=813683&if=gb',
'yang':'https://www.shidianguji.com/zh/book/SK0845/chapter/1kfb0jjuhbg96',
'luxun_smart':'https://zh.wikisource.org/zh-hans/聰明人和傻子和奴才',
'luxun_deng':'https://zh.wikisource.org/zh-hans/燈下漫筆',
'luxun_nucai':'https://zh.wikisource.org/zh-hans/隔膜',
}
def fetch(item):
 name,url=item;r=requests.get(url,timeout=35,headers={'User-Agent':'KinshipArchaicResearch/1.0 (public domain text verification; lmxxf@hotmail.com)' });r.encoding='utf-8';raw=r.text
 (R/'sources'/f'{name}.raw').write_text(raw)
 soup=BeautifulSoup(raw,'html.parser');content=soup.select_one('.mw-parser-output') or soup
 for el in content.select('script,style,.mw-editsection,.noprint,nav'):el.decompose()
 text=raw if name=='honglou_pg' else content.get_text('\n',strip=True)
 (R/'sources'/f'{name}.txt').write_text(text)
 rec=dict(name=name,url=url,status=r.status_code,bytes=len(r.content),chars=len(text),sha256=hashlib.sha256(r.content).hexdigest(),retrieved=time.strftime('%Y-%m-%d %H:%M:%S %z'))
 print(json.dumps(rec,ensure_ascii=False),flush=True);return rec
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 results=list(pool.map(fetch,SOURCES.items()))
(R/'source_manifest.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
