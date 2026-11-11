import sys,json,time,urllib.request,asyncio
from pathlib import Path
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R));from wan22_generate import request,OPENER,files_in
server='http://192.168.31.50:8188'
info=request(server,'/object_info');(R/'sources/object_info.json').write_text(json.dumps(info,indent=2));stats=request(server,'/system_stats');(R/'sources/system_stats.json').write_text(json.dumps(stats,indent=2));print('NODES',len(info),'TORCH',stats['system']['pytorch_version']if'pytorch_version'in stats['system']else stats['system'].get('torch_version'));print('SAVE_VIDEO',info['SaveVideo']['input'])
g={'1':{'class_type':'EmptyImage','inputs':{'width':64,'height':64,'batch_size':5,'color':3381759}},'2':{'class_type':'CreateVideo','inputs':{'images':['1',0],'fps':16.}},'3':{'class_type':'SaveVideo','inputs':{'video':['2',0],'filename_prefix':'_api_smoke/export','format':'mp4'}}}
r=request(server,'/prompt',{'prompt':g,'client_id':'api_smoke'});pid=r['prompt_id']
for i in range(60):
 h=request(server,'/history/'+pid)
 if pid in h:
  x=h[pid]
  if x.get('status',{}).get('status_str')=='error':raise RuntimeError(str(x['status']))
  if x.get('status',{}).get('completed'):break
 time.sleep(1)
else:raise RuntimeError('API export smoke timed out')
art=list(files_in(x['outputs']));assert art
(R/'logs/api_smoke.json').write_text(json.dumps({'status':'pass','prompt_id':pid,'history':x,'files':art},indent=2));print('MP4_EXPORT_PASS',art)
try:
 import aiohttp
 async def testws():
  async with aiohttp.ClientSession()as session:
   async with session.ws_connect(server+'/ws?clientId=wan22_ws_smoke')as ws:
    msg=await ws.receive(timeout=10);(R/'logs/websocket_smoke.json').write_text(json.dumps({'type':str(msg.type),'data':json.loads(msg.data)},indent=2));print('WEBSOCKET_PASS',msg.data[:180])
 asyncio.run(testws())
except ImportError:print('aiohttp not present locally; WebSocket route validation deferred')
