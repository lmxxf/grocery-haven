import sys,struct,hashlib,json
from pathlib import Path
sys.path.insert(0,'/tmp/pbz_audit/py');from Crypto.Cipher import AES
p=Path('/mnt/c/Program Files (x86)/Steam/steamapps/common/PBZ/ProjectPBZ/Content/Paks/ProjectPBZ-Windows.pak');f=p.open('rb');f.seek(-1024,2);tail=f.read();k=tail.rfind(bytes.fromhex('e1126f5a'));footer=p.stat().st_size-1024+k
ver,idx,sz=struct.unpack_from('<IQQ',tail,k+4);sha=tail[k+24:k+44];guid=tail[k-17:k-1];enc=tail[k-1];f.seek(idx);data=f.read((sz+15)//16*16);print('footer',hex(footer),'version',ver,'index',hex(idx),'size',sz,'encrypted',enc,'guid',guid.hex(),'hash',sha.hex())
results=[]
for c in json.load(open('/tmp/pbz_audit/ascii-keys.json')):
 key=bytes.fromhex(c['hex']);plain=AES.new(key,AES.MODE_ECB).decrypt(data);h=hashlib.sha1(plain[:sz]).digest();ok=h==sha;print('candidate',hex(c['offset']),ok);results.append({'offset':c['offset'],'sha1_match':ok})
 if ok:Path('/tmp/pbz_audit/pak_index_decrypted.bin').write_bytes(plain[:sz])
Path('/tmp/pbz_audit/pak-probe.json').write_text(json.dumps({'footer_offset':footer,'version':ver,'index_offset':idx,'index_size':sz,'encrypted':enc,'key_guid':guid.hex(),'index_sha1':sha.hex(),'candidate_tests':results},indent=2))
