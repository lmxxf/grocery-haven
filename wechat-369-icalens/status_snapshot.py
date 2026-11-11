import json,time,sys
from pathlib import Path
r=Path('/home/lmxxf/work/ica-lens-qwen38-27b');role=sys.argv[1];pri=[0,38,56]if role=='main'else[16,41,63];rest=[i for i in range(64)if i not in [0,16,38,41,56,63]][0 if role=='main'else 1::2];owned=pri+rest
available=int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))/1048576
s=json.loads((r/'status.json').read_text());complete=[l for l in owned if(r/f'L{l:02d}'/'complete.json').exists()];readout=[l for l in owned if(r/f'L{l:02d}'/'vocabulary_readouts.json').exists()]
print(json.dumps({'role':role,'time':time.time(),'status':s,'owned_layers':owned,'completed':complete,'readouts':readout,'available_GiB':available,'posthoc_capture':(r/'polysemy_capture.json').exists(),'posthoc_analysis':(r/'polysemy_summary.json').exists(),'extra_readouts_complete':(r/'extra_readouts_complete.json').exists()}))
