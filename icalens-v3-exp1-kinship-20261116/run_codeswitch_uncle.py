#!/usr/bin/env python3
"""Code-switching ablation: Chinese context + English final token `uncle`."""
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

# Parallel to the 5 EN_A frames, translated into natural Chinese context ending in `uncle`
CS_FRAMES = [
    '在上周日的家庭聚会上，我花了一下午跟我{REL}聊天，他一直是我最喜欢的{U}',
    '翻看那本老相册的时候，我找到了一张我{REL}的照片，我从小一直管他叫我的{U}',
    '在昨晚的婚礼晚宴上，大家一起举杯向我{REL}敬酒，他是我最亲近的{U}',
    '每年暑假我去外地探亲的时候，总喜欢住在我{REL}家里，他是我最敬重的{U}',
    '昨天傍晚我接到了我{REL}打来的长途电话，他一直是我最挂念的{U}',
]

REL_PAIRS = [
    ('父亲的哥哥', '母亲的哥哥'),
    ('爸爸的弟弟', '妈妈的弟弟'),
]

def main():
    t0 = time.time()
    torch.set_num_threads(8)
    torch.set_float32_matmul_precision('highest')
    from model_loader import load_model
    tok, model = load_model()

    probes = []
    pairs = []
    # Variant A: space before uncle (' uncle' -> exact token 36252 as in EN_A)
    # Variant B: no space ('uncle' directly after Chinese)
    for mode, u_str in [('space_uncle', ' uncle'), ('nospace_uncle', 'uncle')]:
        for r_idx, (pat_rel, mat_rel) in enumerate(REL_PAIRS):
            for f_idx, tpl in enumerate(CS_FRAMES):
                ta = tpl.format(REL=pat_rel, U=u_str)
                tb = tpl.format(REL=mat_rel, U=u_str)
                ida = tok.encode(ta, add_special_tokens=False)
                idb = tok.encode(tb, add_special_tokens=False)
                pa_id = len(probes)
                probes.append({
                    'id': pa_id, 'mode': mode, 'rel': pat_rel, 'frame': f_idx,
                    'text': ta, 'input_ids': ida,
                    'last_id': ida[-1], 'last_tok': tok.decode([ida[-1]]),
                    'tail3': [tok.decode([x]) for x in ida[-3:]],
                })
                pb_id = len(probes)
                probes.append({
                    'id': pb_id, 'mode': mode, 'rel': mat_rel, 'frame': f_idx,
                    'text': tb, 'input_ids': idb,
                    'last_id': idb[-1], 'last_tok': tok.decode([idb[-1]]),
                    'tail3': [tok.decode([x]) for x in idb[-3:]],
                })
                pairs.append({'mode': mode, 'pair_type': f'{pat_rel}/{mat_rel}', 'frame': f_idx, 'a': pa_id, 'b': pb_id})

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
    z_cs = np.zeros((64, n, 5120), dtype=np.float32)
    for l in range(64):
        asset = load_file(str(ASSET / manifest['layers'][str(l)]['file']), device='cuda')
        C = asset['reading_matrix']
        center = asset['center']
        x = torch.tensor(acts[l], device='cuda')
        y = (x / x.norm(dim=1, keepdim=True).clamp_min(1e-12) - center) @ C.T
        z_cs[l] = y.cpu().numpy()
        del asset, C, center, x, y

    np.save(HEAVY / 'z_codeswitch_uncle.npy', z_cs)

    key_axes = [(13, 2665), (25, 3140), (26, 3526), (28, 544), (30, 684), (32, 3853), (42, 1992), (54, 230), (56, 998)]
    summary = {'elapsed_sec': round(time.time() - t0, 2), 'sample_probes': probes[:4], 'modes': {}}
    for mode in ['space_uncle', 'nospace_uncle']:
        mpairs = [pr for pr in pairs if pr['mode'] == mode]
        mres = {'last_token_ids': sorted(list({probes[pr['a']]['last_id'] for pr in mpairs})),
                'last_token_decoded': sorted(list({probes[pr['a']]['last_tok'] for pr in mpairs})),
                'axes': {}}
        for L, c in key_axes:
            za = np.array([z_cs[L, pr['a'], c] for pr in mpairs])
            zb = np.array([z_cs[L, pr['b'], c] for pr in mpairs])
            diff = zb - za
            all_d = np.abs(np.mean([z_cs[L, pr['b'], :] - z_cs[L, pr['a'], :] for pr in mpairs], axis=0))
            rk = int((all_d > abs(diff.mean())).sum()) + 1
            top1 = int(np.argmax(all_d))
            mres['axes'][f'L{L:02d}_C{c}'] = {
                'pat_mean': round(float(za.mean()), 3),
                'mat_mean': round(float(zb.mean()), 3),
                'delta': round(float(diff.mean()), 3),
                'acc': f'{int((diff > 0).sum())}/{len(diff)}',
                'rank_in_5120': rk,
                'layer_self_top1': f'L{L:02d} C{top1} (|Δ|={all_d[top1]:.2f})',
            }
        summary['modes'][mode] = mres

    (OUT / 'codeswitch_zh_uncle_results.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
