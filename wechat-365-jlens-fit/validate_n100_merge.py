"""Read-only CPU check of every element of the actual N=100 merge."""
from pathlib import Path
import json,time
import torch
R=Path(__file__).resolve().parent;torch.set_num_threads(4)
a=torch.load(R/'fit_even/lens_local_n50.pt',map_location='cpu',mmap=True,weights_only=True)
b=torch.load(R/'fit_odd/lens_local_n50.pt',map_location='cpu',mmap=True,weights_only=True)
c=torch.load(R/'lens_n100.pt',map_location='cpu',mmap=True,weights_only=True)
assert a['n_prompts']==b['n_prompts']==50 and c['n_prompts']==100
for l in range(63):
 for i in range(0,5120,64):
  # Match official merge arithmetic, including FP32 multiplication/division order.
  expected=((a['J'][l][i:i+64].float()*50+b['J'][l][i:i+64].float()*50)/100).half()
  assert torch.equal(expected,c['J'][l][i:i+64]),(l,i)
 if l%16==0:print('MERGE_CHECK_LAYER',l,flush=True)
out={'accepted':True,'time':time.time(),'english_prompts':50,'chinese_prompts':50,'merged_prompts':100,'checked_entries':63*5120*5120,'every_saved_entry_matches_official_50_50_merge':True,'validation_device':'CPU only; no model forward/backward'}
(R/'n100_merge_validation.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
