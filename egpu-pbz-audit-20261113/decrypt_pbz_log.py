#!/usr/bin/env python3
"""Read PBZLOGE1, optionally decrypt with the matching recipient X25519 private key.
All output defaults to /tmp; never writes game files. No embedded private key was found.
"""
import argparse,json,sys,hashlib
from pathlib import Path
sys.path.insert(0,'/tmp/pbz_audit/py')
PUB=bytes.fromhex('0d068454d8c1dd2b83b0f8839d7f0604e0d28316c6036ec1213e0beaf290760d')
p=argparse.ArgumentParser();p.add_argument('--input',default='/mnt/c/Users/lmxxf/AppData/Local/ProjectPBZ/Saved/Logs/ProjectPBZ.log');p.add_argument('--recipient-private-hex');p.add_argument('--output',default='/tmp/ProjectPBZ_decrypted.log');a=p.parse_args();b=Path(a.input).read_bytes()
if b[:8]!=b'PBZLOGE1' or int.from_bytes(b[12:16],'little')!=64:raise SystemExit('Unrecognized PBZ log header')
meta={'magic':b[:8].decode(),'version_bytes':b[8:12].hex(),'header_size':64,'ephemeral_public_key':b[16:48].hex(),'iv':b[48:64].hex(),'recipient_public_key':PUB.hex(),'size':len(b),'sha256':hashlib.sha256(b).hexdigest()};print(json.dumps(meta,indent=2))
if not a.recipient_private_hex:raise SystemExit('Not decrypted: recipient X25519 private key is required; binary contains only its public key. No plaintext output created.')
from Crypto.Protocol.DH import import_x25519_private_key,import_x25519_public_key,key_agreement
from Crypto.Protocol.KDF import HKDF
from Crypto.Hash import SHA256
from Crypto.Cipher import AES
priv=import_x25519_private_key(bytes.fromhex(a.recipient_private_hex))
if priv.public_key().export_key(format='raw')!=PUB:raise SystemExit('Wrong recipient private key: public key mismatch')
shared=key_agreement(static_priv=priv,static_pub=import_x25519_public_key(b[16:48]),kdf=lambda v:v)
key=HKDF(shared,32,b'',SHA256,context=b'pbz-log-v1'+b[16:48]+PUB+b[48:64])
plain=AES.new(key,AES.MODE_CTR,nonce=b'',initial_value=int.from_bytes(b[48:64],'big')).decrypt(b[64:])
# AES-CTR is unauthenticated; reject implausible plaintext rather than saving garbage.
if not(plain.startswith(b'\xef\xbb\xbf') or plain.startswith(b'Log') or plain.startswith(b'[')):raise SystemExit('Derived output lacks expected log prefix; no output written')
out=Path(a.output).resolve()
if not str(out).startswith('/tmp/'):raise SystemExit('Output must stay under /tmp')
out.write_bytes(plain);print('Wrote',out,len(plain),'bytes')
