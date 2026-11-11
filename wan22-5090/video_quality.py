"""CPU-decode every frame and check basic image health; manual review is still separate."""
import json,subprocess,sys
from pathlib import Path
import numpy as np
p=Path(sys.argv[1]);proc=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-i',str(p),'-vf','scale=128:72','-vsync','0','-pix_fmt','rgb24','-f','rawvideo','-'],stdout=subprocess.PIPE)
size=128*72*3;stats=[];differences=[];last=None
while True:
 data=b''
 while len(data)<size:
  b=proc.stdout.read(size-len(data))
  if not b:break
  data+=b
 if not data:break
 if len(data)!=size:raise RuntimeError('Truncated decoded frame')
 a=np.frombuffer(data,np.uint8).reshape(72,128,3).astype(np.float32);y=a@np.array([.2126,.7152,.0722]);stats.append({'mean_luma':float(y.mean()),'std_luma':float(y.std())})
 if last is not None:differences.append(float(np.abs(a-last).mean()))
 last=a
assert proc.wait()==0
result={'file':str(p),'decoded_frames':len(stats),'min_mean_luma':min(x['mean_luma']for x in stats),'min_spatial_std_luma':min(x['std_luma']for x in stats),'near_black_frames':sum(x['mean_luma']<2 for x in stats),'near_uniform_frames':sum(x['std_luma']<2 for x in stats),'mean_adjacent_frame_RGB_MAE':float(np.mean(differences)),'min_adjacent_frame_RGB_MAE':min(differences),'max_adjacent_frame_RGB_MAE':max(differences),'method':'CPU ffmpeg RGB decode and 128x72 statistical screen; not a perceptual quality metric'}
assert result['decoded_frames']==81 and result['near_black_frames']==0 and result['near_uniform_frames']==0
p.with_suffix('.quality.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
