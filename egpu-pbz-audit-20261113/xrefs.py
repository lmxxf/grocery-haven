import sys,re,struct,json
sys.path.insert(0,'/tmp/pbz_audit');from scan import b,rva
rows=json.load(open('/tmp/pbz_audit/cvars-strings.json')) if __import__('pathlib').Path('/tmp/pbz_audit/cvars-strings.json').exists() else []
old=json.load(open('/tmp/pbz_audit/strings.json'));targets={rva(r['offset']):r for r in rows}
for s in old:
 for h in s['hits']:targets[h['rva']]={'offset':h['offset'],'text':h['text']}
refs=[]
for m in re.finditer(rb'[\x48\x4c][\x8d\x8b][\x05\x0d\x15\x1d\x25\x2d\x35\x3d]....',b[:0xa658400],re.S):
 o=m.start();v=rva(o)+7+struct.unpack_from('<i',b,o+3)[0]
 if v in targets:refs.append({'offset':o,'target':targets[v]})
json.dump(refs,open('/tmp/pbz_audit/xrefs.json','w'),indent=2)
for v in [0x4815b60,0x4816f00]:
 hits=[]
 for m in re.finditer(b'\xe8....',b[:0xa658400],re.S):
  o=m.start();t=rva(o)+5+struct.unpack_from('<i',b,o+1)[0]
  if t==v:hits.append(hex(o))
 print('call',hex(v),hits)
print('refs',len(refs))
