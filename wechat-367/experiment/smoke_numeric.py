import sys,json,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'icalens_pkg'))
import torch,numpy as np
from icalens import ICALens
torch.set_num_threads(2);torch.manual_seed(367)
x=torch.randn(512,8);x[:,0]=torch.distributions.Laplace(0.,1.).sample((512,))
lens=ICALens(model_id='toy',row_normalize=True)
lens.fit(x,layer=0,n_components=8,max_iter=50,device='cpu',batch_size=128)
z=lens._get_layer(0);a=lens.transform(x,layer=0);back=lens.inverse_transform(a,layer=0)
err=float((back-x/x.norm(dim=-1,keepdim=True)).abs().max());assert err<1e-4
with tempfile.TemporaryDirectory()as d:
 lens.save(d);re=ICALens.from_pretrained(d);assert np.allclose(re.transform(x,layer=0),a,atol=1e-5)
print(json.dumps({'official_core_cpu_smoke':'PASS','max_row_normalized_reconstruction_error':err,'iterations':z.fitting['n_iter']}))
