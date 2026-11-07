from pathlib import Path
import os,requests,concurrent.futures,time,hashlib,json
R=Path(__file__).resolve().parent
repos=[('openai-community/gpt2-xl','gpt2-xl','0f8b28eb05a8075f48b61b6f35332978c74fc7763fa9fb4051a1c30511736a6a'),('EleutherAI/pythia-2.8b','pythia-2.8b','ab496f1c3fd79e3c749a9d5414136a2c8e4224f94eecb261970315cdb0f813fe')]
def download(spec):
 repo,name,expected=spec;root=Path('/home/lmxxf/work/models')/name;meta=requests.get('https://modelscope.cn/api/v1/models/'+repo+'/repo/files',params={'Revision':'master','Recursive':'true'},timeout=30).json();f=next(x for x in meta['Data']['Files'] if x.get('Path')=='model.safetensors');assert f['Sha256']==expected
 size=f['Size'];dest=root/'model.safetensors';tmp=root/'model.safetensors.361-part';fd=os.open(tmp,os.O_CREAT|os.O_RDWR,0o644);os.ftruncate(fd,size);chunk=(size+7)//8;url='https://modelscope.cn/models/'+repo+'/resolve/master/model.safetensors?task=361'
 def part(i):
  start=i*chunk;end=min(size,(i+1)*chunk)-1;hole=os.lseek(fd,start,os.SEEK_HOLE);pos=start+max(0,(min(hole,end+1)-start)//1048576-1)*1048576
  print("RESUME",name,i,pos-start,flush=True)
  for attempt in range(100):
   try:
    with requests.get(url,headers={'Range':f'bytes={pos}-{end}'},stream=True,timeout=(20,90)) as r:
     r.raise_for_status();assert r.status_code==206 and r.headers.get('Content-Range','').startswith(f'bytes {pos}-'),dict(r.headers)
     for b in r.iter_content(1024*1024):os.pwrite(fd,b,pos);pos+=len(b)
    assert pos==end+1,(i,pos,end);print('PART_DONE',name,i,flush=True);return
   except Exception as e:print('RETRY',name,i,attempt,type(e).__name__,flush=True);time.sleep(1)
  raise RuntimeError((name,i,pos))
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:list(ex.map(part,range(8)))
 os.close(fd);h=hashlib.sha256()
 with tmp.open('rb') as s:
  for b in iter(lambda:s.read(8*1024*1024),b''):h.update(b)
 assert h.hexdigest()==expected,(name,h.hexdigest());tmp.replace(dest);(R/('download_'+name+'.json')).write_text(json.dumps(dict(repo=repo,mirror='modelscope.cn',metadata=f,sha256=h.hexdigest(),bytes=size),indent=2));print('VERIFIED',name,size,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:list(ex.map(download,repos))
