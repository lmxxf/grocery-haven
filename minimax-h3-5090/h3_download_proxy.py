#!/usr/bin/env python3
"""Temporary CONNECT relay through Spark TUN; restricted to the authorized 5090 LAN IP."""
import socket,select,http.server,time
ALLOWED={'192.168.31.50','192.168.31.198','127.0.0.1'}
DOMAINS=('github.com','githubusercontent.com','githubassets.com','huggingface.co','hf.co','hf-mirror.com','pypi.org','pythonhosted.org','pytorch.org','7-zip.org','gyan.dev','python.org','modelscope.cn','aliyuncs.com','aliyun.com')
class Handler(http.server.BaseHTTPRequestHandler):
 def do_CONNECT(self):
  host,port=self.path.rsplit(':',1)
  if self.client_address[0]not in ALLOWED or port!='443' or not any(host==d or host.endswith('.'+d)for d in DOMAINS):self.send_error(403);return
  try:up=socket.create_connection((host,int(port)),timeout=30)
  except OSError as e:self.send_error(502,str(e));return
  self.send_response(200,'Connection established');self.end_headers();up.settimeout(None);self.connection.settimeout(None)
  try:
   sockets=[self.connection,up]
   while True:
    readable,_,_=select.select(sockets,[],[],120)
    if not readable:break
    for src in readable:
     b=src.recv(262144)
     if not b:return
     (up if src is self.connection else self.connection).sendall(b)
  except OSError:pass
  finally:up.close();self.close_connection=True
 def log_message(self,fmt,*args):print(time.strftime('%F %T'),self.client_address[0],fmt%args,flush=True)
class Server(http.server.ThreadingHTTPServer):daemon_threads=True;allow_reuse_address=True
print('DOWNLOAD_RELAY 192.168.31.198:17892 client=192.168.31.50',flush=True)
Server(('192.168.31.198',17892),Handler).serve_forever()
