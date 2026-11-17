#!/usr/bin/env python3
"""Modern Chinese context + Chinese generic nouns (`亲戚`, `长辈`) control ablation.
Exact 1-to-1 match with `CS_FRAMES` and `REL_PAIRS` in `run_codeswitch_uncle.py`."""
import os, sys, json, time
from pathlib import Path
import numpy as np
import torch
from safetensors.torch import load_file

ROOT = Path('/home/lmxxf/work/ica-lens-qwen38-27b-v3')
ASSET = ROOT / 'hf_clean_upload'
HEAVY = ROOT / 'experiments/exp1a_kinship'
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ['TRITON_CACHE_DIR'] = str(ROOT / 'triton_cache')
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

CS_FRAMES = [
    '在上周日的家庭聚会上，我花了一下午跟我{REL}聊天，他一直是我最喜欢的{END}',
    '翻看那本老相册的时候，我找到了一张我{REL}的照片，我从小一直管他叫我的{END}',
    '在昨晚的婚礼晚宴上，大家一起举杯向我{REL}敬酒，他是我最亲近的{END}',
    '每年暑假我去外地探亲的时候，总喜欢住在我{REL}家里，他是我最敬重的{END}',
    '昨天傍晚我接到了我{REL}打来的长途电话，他一直是我最挂念的{END}',
]

REL_PAIRS = [
    ('父亲的哥哥', '母亲的哥哥'),
    ('爸爸的弟弟', '妈妈的弟弟'),
]

ENDINGS = [
    ('modern_zh_qinqi', '亲戚'),
    ('modern_zh_zhangbei', '长辈'),
]

def main():
    t0 = time.time()
    torch.set_num_threads(8)
    torch.set_float32_matmul_precision('highest')
    from model_loader import load_model
    tok, model = load_model()

    probes = []
    pairs = []
    for mode, end_str in ENDINGS:
        for pat_rel, mat_rel in REL_PAIRS:
            for f_idx, tpl in enumerate(CS_FRAMES):
                ta = tpl.format(REL=pat_rel, END=end_str)
                tb = tpl.format(REL=mat_rel, END=end_str)
                ida = tok.encode(ta, add_special_tokens=False)
                idb = tok.encode(tb, add_special_tokens=False)
                pa_id = len(probes)
                probes.append({'id': pa_id, 'mode': mode, 'frame': f_idx, 'text': ta, 'input_ids': ida, 'last_tok': tok.decode([ida[-1]])})
                pb_id = len(probes)
                probes.append({'id': pb_id, 'mode': mode, 'frame': f_idx, 'text': tb, 'input_ids': idb, 'last_tok': tok.decode([idb[-1]])})
                pairs.append({'mode': mode, 'frame': f_idx, 'a': pa_id, 'b': pb_id})

    n = len(probes)
    acts = np.zeros((64, n, 5120), dtype=np.float32)
    cur = [0]
    handles = []
    for l, block in enumerate(model.model.layers):
        def hook(m, inp, out, l=l):
            h = (out[0] if isinstance(out, tuple) else out)[0]
            acts[l, cur[0]] = h[-1].float().cpu().numpy()
        handles.append(block.register_forward_hook(hook))

    with torch.inference_mode():
        for j, p in enumerate(probes):
            cur[0] = j
            model.model(input_ids=torch.tensor([p['input_ids']], device='cuda'), use_cache=False)

    for h in handles:
        h.remove()
    del model
    torch.cuda.empty_cache()

    manifest = json.loads((ASSET / 'icalens.json').read_text())
    z_all = np.zeros((64, n, 5120), dtype=np.float32)
    for l in range(64):
        asset = load_file(str(ASSET / manifest['layers'][str(l)]['file']), device='cuda')
        C = asset['reading_matrix']
        center = asset['center']
        x = torch.tensor(acts[l], device='cuda')
        y = (x / x.norm(dim=1, keepdim=True).clamp_min(1e-12) - center) @ C.T
        z_all[l] = y.cpu().numpy()
        del asset, C, center, x, y

    np.save(HEAVY / 'z_modern_zh_generic.npy', z_all)
    key_axes = [(13, 2665), (25, 3140), (26, 3526), (28, 544), (30, 684), (32, 3853), (42, 1300), (42, 1992), (54, 230), (56, 998)]
    out = {'elapsed_sec': round(time.time() - t0, 2), 'modes': {}}
    for mode, _ in ENDINGS:
        mpairs = [pr for pr in pairs if pr['mode'] == mode]
        mres = {'last_tok': probes[mpairs[0]['a']]['last_tok'], 'axes': {}}
        for L, c in key_axes:
            za_all = np.array([z_all[L, pr['a'], :] for pr in mpairs], dtype=np.float64)
            zb_all = np.array([z_all[L, pr['b'], :] for pr in mpairs], dtype=np.float64)
            d_vec = (zb_all - za_all).mean(axis=0)
            abs_d = np.abs(d_vec)
            rk = int((abs_d > abs_d[c]).sum()) + 1
            top5 = [f'C{int(i)}({d_vec[i]:+.2f})' for i in np.argsort(-abs_d)[:5]]
            diff_c = zb_all[:, c] - za_all[:, c]
            mres['axes'][f'L{L:02d}_C{c}'] = {
                'pat': round(float(za_all[:, c].mean()), 3),
                'mat': round(float(zb_all[:, c].mean()), 3),
                'delta': round(float(d_vec[c]), 3),
                'mat_gt_pat': f'{int((diff_c > 0).sum())}/{len(diff_c)}',
                'rank_in_5120': rk,
                'top5_diff_axes': top5,
            }
        out['modes'][mode] = mres
    (OUT / 'modern_zh_generic_results.json').write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
