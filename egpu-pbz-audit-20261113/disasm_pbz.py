import sys,json,bisect,struct
sys.path[:0]=['/tmp/pbz_audit/py','/tmp/pbz_audit'];from capstone import *
from capstone.x86_const import X86_REG_RIP
from scan import b,off,rva,base
cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True
imports=json.load(open('/tmp/pbz_audit/imports.json')) if __import__('pathlib').Path('/tmp/pbz_audit/imports.json').exists() else {}
for arg in sys.argv[1:]:
 a,z=(arg.split(':')+['600'])[:2];o=int(a,0);size=int(z,0);print('\nFILE',hex(o),'VA',hex(base+rva(o)))
 for i in cs.disasm(b[o:o+size],base+rva(o)):
  note=[]
  for op in i.operands:
   if op.type==CS_OP_MEM and op.mem.base==X86_REG_RIP:
    t=i.address+i.size+op.mem.disp
    if hex(t) in imports:note.append(imports[hex(t)])
    try:
     f=off(t-base);v=b[f:f+180]
     if v[1:2]==b'\0':s=v.decode('utf-16le',errors='replace').split('\0')[0]
     else:s=v.split(b'\0')[0].decode(errors='replace')
     if len(s)>3 and all(c.isprintable() or c in '\n\t\r' for c in s):note.append(hex(f)+' '+repr(s))
    except:pass
  print(hex(off(i.address-base)),hex(i.address),i.mnemonic,i.op_str, ' ; '.join(note))
