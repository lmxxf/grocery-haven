import sys,json,struct
sys.path[:0]=['/tmp/pbz_audit/py','/tmp/pbz_audit'];from capstone import *
from capstone.x86_const import *
from scan import b,rva,off,base
cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True
xs=json.load(open('/tmp/pbz_audit/xrefs.json'));names=['r.FinishCurrentFrame','r.OneFrameThreadLag','r.HZBOcclusion','r.NumBufferedOcclusionQueries','r.Occlusion.SingleRHIThreadStall','r.SkinCache.Mode','r.SkinCache.AsyncCompute','fx.NiagaraAllowGPUParticles','fx.NiagaraAllowComputeShaders','t.Streamline.Reflex.Enable','t.Streamline.Reflex.Mode','t.Streamline.Reflex.HandleMaxTickRate','r.Nanite.Streaming.Readback.UseAsyncCopy','r.RHICmdBypass','r.GPUCrashDebugging','nne.ort.enableprofiling']
rows=[]
for x in xs:
 q=x['target']['text'];o=x['offset']
 if not(q in names or q.startswith('d3d12.UploadHeap.')):continue
 start=b.rfind(b'\xcc',max(0,o-180),o)+1
 if start<=max(0,o-180):start=o-30
 ins=list(cs.disasm(b[start:o+150],base+rva(start)));lines=[]
 for i in ins:
  if i.address>base+rva(o)+90:break
  lines.append(hex(off(i.address-base))+' '+i.mnemonic+' '+i.op_str)
  if i.mnemonic=='lea' and i.operands[0].reg==X86_REG_R8 and i.operands[1].type==CS_OP_MEM and i.operands[1].mem.base==X86_REG_RIP:
   try:
    p=off(i.address+i.size+i.operands[1].mem.disp-base);lines.append('  R8 data @'+hex(p)+' int32='+str(struct.unpack_from('<i',b,p)[0]))
   except:pass
 rows.append({'name':q,'string_offset':x['target']['offset'],'xref_offset':o,'instructions':lines})
json.dump(rows,open('/tmp/pbz_audit/cvar-regs.json','w'),indent=2)
for r in rows:
 print(r['name'],hex(r['xref_offset']))
 print('\n'.join(l for l in r['instructions'] if any(s in l for s in ['r8','r9','rsp + 0x20','R8 data','call'])))
