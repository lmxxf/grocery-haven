"""Create flat core-only WebUI graphs from the tested API graphs and live node schemas."""
import json
from pathlib import Path
R=Path(__file__).resolve().parent
info=json.loads((R/'sources/object_info.json').read_text())
PORT_TYPES={'MODEL','CLIP','VAE','CONDITIONING','LATENT','IMAGE','VIDEO','AUDIO','CLIP_VISION_OUTPUT'}
POSITIONS={1:[0,0],2:[0,220],3:[0,480],4:[0,700],5:[400,430],6:[400,730],7:[400,200],8:[400,0],9:[400,100],10:[800,0],11:[1150,0],12:[1500,0],13:[1850,0],14:[2200,0],15:[0,900]}
for mode in ['t2v','i2v']:
 api=json.loads((R/'workflows'/f'wan22_{mode}_20steps_api.json').read_text());nodes=[];by={};links=[]
 for id,v in api.items():
  schema=info[v['class_type']];inputs=[];values=[];allparams={**schema['input'].get('required',{}),**schema['input'].get('optional',{})}
  for name,spec in allparams.items():
   typ=spec[0];meta=spec[1]if len(spec)>1 and isinstance(spec[1],dict)else{};value=v['inputs'].get(name,meta.get('default',typ[0]if isinstance(typ,list)and typ else None))
   is_link=isinstance(value,list)and len(value)==2 and isinstance(value[0],str)and value[0]in api
   if is_link or(isinstance(typ,str)and typ in PORT_TYPES):inputs.append({'name':name,'type':typ if isinstance(typ,str)else'*','link':None})
   elif not meta.get('hidden',False):
    if value is not None:values.append(value)
    if name in ['seed','noise_seed']and meta.get('control_after_generate',False):values.append('fixed')
  if v['class_type']=='KSamplerAdvanced':
   x=v['inputs'];values=[x['add_noise'],x['noise_seed'],'fixed',x['steps'],x['cfg'],x['sampler_name'],x['scheduler'],x['start_at_step'],x['end_at_step'],x['return_with_leftover_noise']]
  if v['class_type']=='LoadImage':values=[v['inputs']['image'],'image']
  if v['class_type']=='SaveVideo':values=[v['inputs']['filename_prefix'],'mp4','auto']
  outputs=[{'name':n,'type':t,'links':[]}for n,t in zip(schema.get('output_name',schema.get('output',[])),schema.get('output',[]))]
  obj={'id':int(id),'type':v['class_type'],'pos':POSITIONS[int(id)],'size':[320,240]if v['class_type']in ['KSamplerAdvanced','CLIPTextEncode']else[300,180],'flags':{},'order':len(nodes),'mode':0,'inputs':inputs,'outputs':outputs,'properties':{'Node name for S&R':v['class_type']},'widgets_values':values}
  nodes.append(obj);by[id]=obj
 for id,v in api.items():
  for slot,sock in enumerate(by[id]['inputs']):
   value=v['inputs'].get(sock['name'])
   if isinstance(value,list)and len(value)==2 and isinstance(value[0],str)and value[0]in api:
    origin,outslot=value;lid=len(links)+1;sock['link']=lid;by[origin]['outputs'][outslot]['links'].append(lid);links.append([lid,int(origin),outslot,int(id),slot,sock['type']])
 graph={'last_node_id':max(n['id']for n in nodes),'last_link_id':len(links),'nodes':nodes,'links':links,'groups':[],'config':{},'extra':{'ds':{'scale':.55,'offset':[80,100]}},'version':.4}
 (R/'workflows'/f'Wan22_{mode.upper()}_20steps_FP8.json').write_text(json.dumps(graph,ensure_ascii=False,indent=2));print(mode,len(nodes),len(links))
