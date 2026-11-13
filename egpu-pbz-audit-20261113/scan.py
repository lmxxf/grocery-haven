from pathlib import Path
import struct,re,json
b=Path('/mnt/c/Program Files (x86)/Steam/steamapps/common/PBZ/platform/steam/PBZ.exe').read_bytes();base=0x140000000
pe=struct.unpack_from('<I',b,60)[0];sh=pe+24+struct.unpack_from('<H',b,pe+20)[0];secs=[]
for i in range(struct.unpack_from('<H',b,pe+6)[0]):
 o=sh+i*40;vs,va,rs,rp=struct.unpack_from('<IIII',b,o+8);secs.append((rp,rs,va,b[o:o+8].rstrip(b'\0').decode()))
def rva(o):
 for rp,rs,va,n in secs:
  if rp<=o<rp+rs:return va+o-rp
 raise ValueError(hex(o))
def off(v):
 for rp,rs,va,n in secs:
  if va<=v<va+rs:return rp+v-va
 raise ValueError(hex(v))
if __name__=='__main__':
 strings=[]
 for s in ['PBZLOGE1','pbz-log-v1','FD3D12UploadHeapAllocator','d3d12.UploadHeap','ReBAR','Resizable','GPU_UPLOAD','NNERuntimeORT','DirectML','Readback','ReadBack','CopyQueue','r.SkinCache','r.Niagara','r.Reflex','norebar','r.HZBOcclusion','r.OneFrameThreadLag']:
  hits=[]
  for enc in ['utf-8','utf-16le']:
   pat=s.encode(enc);start=0
   while True:
    o=b.find(pat,start)
    if o<0:break
    start=o+len(pat)
    if enc=='utf-16le':
     end=o
     while end+2<len(b) and b[end:end+2]!=b'\0\0' and end<o+2000:end+=2
     text=b[o:end].decode(enc,errors='replace')
    else:
     end=b.find(b'\0',o,o+2000);text=b[o:end if end>=0 else o+200].decode(enc,errors='replace')
    hits.append({'offset':o,'rva':rva(o),'encoding':enc,'text':text[:1300]})
  strings.append({'query':s,'hits':hits})
 Path('/tmp/pbz_audit/strings.json').write_text(json.dumps(strings,ensure_ascii=False,indent=2))
 targets={h['rva']:(x['query'],h['offset'])for x in strings if x['query']in ['PBZLOGE1','pbz-log-v1']for h in x['hits']};refs=[]
 for m in re.finditer(rb'[\x48\x4c][\x8d\x8b][\x05\x0d\x15\x1d\x25\x2d\x35\x3d]....',b[:0xa658400],re.S):
  o=m.start();t=rva(o)+7+struct.unpack_from('<i',b,o+3)[0]
  if t in targets:refs.append({'offset':o,'rva':rva(o),'target':targets[t]})
 print('log refs',refs);Path('/tmp/pbz_audit/log-refs.json').write_text(json.dumps(refs,indent=2))
 print('counts',[(x['query'],len(x['hits']))for x in strings])
