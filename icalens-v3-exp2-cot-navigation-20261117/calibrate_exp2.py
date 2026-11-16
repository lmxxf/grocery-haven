from common_exp2 import *
import sys,math
sys.path.insert(0,'/home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/wechat-363')
import numpy as np,torch
from run_manifold_exp import compute_temporal_metrics_batched_layers as geometry

def run():
 torch.set_num_threads(8);torch.set_float32_matmul_precision('highest');torch.manual_seed(20261117)
 stats=[read(V3/f'L{l:02d}/statistics.json')['test']for l in range(64)];k=np.array([s['excess_kurtosis']for s in stats]);taus=[10,30,50];masks=np.stack([k>tau for tau in taus],axis=1).reshape(192,5120);fractions=masks.mean(1)
 G=torch.randn(4096,5120,device='cuda');sq=G.square();psq=G.clamp_min(0).square();mask=torch.tensor(masks.T,device='cuda',dtype=torch.float32)
 c=(sq@mask)/sq.sum(1,keepdim=True);cp=(psq@mask)/psq.sum(1,keepdim=True);cpfull=(psq@mask)/sq.sum(1,keepdim=True)
 excess=c.cpu().numpy()-fractions;excessp=cp.cpu().numpy()-fractions;excesspf=cpfull.cpu().numpy()-.5*fractions
 top=sq.topk(20,dim=1).values;norm=sq.sum(1);top5=top[:,:5].sum(1)/norm;top20=top.sum(1)/norm;kurt=G.pow(4).mean(1)/(sq.mean(1).square())-3;zmax=G.max(1).values
 q=lambda a:{'p01':float(np.quantile(a,.01)),'p05':float(np.quantile(a,.05)),'p50':float(np.quantile(a,.5)),'p95':float(np.quantile(a,.95)),'p99':float(np.quantile(a,.99)),'mean':float(np.mean(a))}
 rows=[]
 for l in range(64):
  rows.append(dict(layer=l,thresholds={str(tau):dict(count=int(masks[l*3+j].sum()),fraction=float(fractions[l*3+j]),delta_null=q(excess[:,l*3+j]),positive_conditional_delta_null=q(excessp[:,l*3+j]),positive_full_delta_null=q(excesspf[:,l*3+j]))for j,tau in enumerate(taus)}))
 # Great-circle and causal suffix checks against the imported 363 implementation.
 angles=torch.arange(20,device='cuda')*.17;h=torch.zeros(1,1,20,32,device='cuda');h[0,0,:,0]=angles.cos();h[0,0,:,1]=angles.sin();m=geometry(h,torch.zeros(1,32,device='cuda'));extended=torch.cat([h,torch.randn(1,1,7,32,device='cuda')],dim=2);m2=geometry(extended,torch.zeros(1,32,device='cuda'))
 primary=['s_geo','theta_surf','kappa_geo','erank_dir'];prefixerr={key:float(torch.nan_to_num(m[key]-m2[key][:,:,:20]).abs().max())for key in primary}
 synthetic=dict(great_circle_step_mean=float(m['s_geo'][0,0,1:].mean()),great_circle_curvature_max=float(m['kappa_geo'][0,0,2:].max()),great_circle_erank_max=float(m['erank_dir'][0,0,5:].max()),causal_append_max_errors=prefixerr)
 assert max(prefixerr.values())==0 and synthetic['great_circle_curvature_max']<.03 and synthetic['great_circle_erank_max']<1.005
 result=dict(n_gaussian=4096,seed=20261117,dimension=5120,layers=rows,zmax=q(zmax.cpu().numpy()),top5_energy=q(top5.cpu().numpy()),top20_energy=q(top20.cpu().numpy()),coordinate_kurtosis=q(kurt.cpu().numpy()),synthetic=synthetic,kinematics_source_sha256=hashfile('/home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/wechat-363/run_manifold_exp.py'))
 save('calibration.json',result)
 append('Step 1 实测｜高斯基线和原363公式数值验收',f"4096条N(0,I)向量，seed20261117。L00 κ>10轴={rows[0]['thresholds']['10']['count']}/5120，L32={rows[32]['thresholds']['10']['count']}/5120；ΔC均值分别{rows[0]['thresholds']['10']['delta_null']['mean']:.6f}/{rows[32]['thresholds']['10']['delta_null']['mean']:.6f}。\n\n正半轴有两种分母：positive_conditional以正能量为分母，基线f；positive_full仍以总能量为分母，基线f/2，不能误扣同一个数。\n\n高斯z_max的95/99分位={result['zmax']['p95']:.3f}/{result['zmax']['p99']:.3f}；Top5/Top20能量99分位={result['top5_energy']['p99']:.5f}/{result['top20_energy']['p99']:.5f}；单向量跨维峰度99分位={result['coordinate_kurtosis']['p99']:.4f}。这些是本轮海水参照，不预先把所有真实token都判大陆。\n\n原363大圆轨迹检验：s={synthetic['great_circle_step_mean']:.6f}，κ_g最大={synthetic['great_circle_curvature_max']:.6f}，5步rank最大={synthetic['great_circle_erank_max']:.6f}。追加未来7个随机状态后，已存在位置的四个主指标最大变化均为0。")
 return result
if __name__=='__main__':run()
