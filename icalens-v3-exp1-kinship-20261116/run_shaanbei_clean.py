#!/usr/bin/env python3
"""Strict single-variable Shaanbei rural context ablation: exact same REL_PAIRS as modern Chinese frames, zero '娘家/姻亲/嫁' keywords in frames."""
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

# Strictly zero '娘家/本家/姻/嫁/婚/外' keywords! Pure Shaanbei rural village + clan hall setting,
# with IDENTICAL REL_PAIRS to run_codeswitch_uncle.py: ('父亲的哥哥','母亲的哥哥'), ('爸爸的弟弟','妈妈的弟弟')
DEEP_CLEAN_FRAMES = [
    '我家世代住在陕北黄土高原的一个小山村里，村里老少爷们最讲究传统礼数与长幼尊卑，正月十五都要去祖祠给老祖宗上香磕头。今天坐在窑洞热炕头上喝酒的这位客人是我{REL}，他是我最敬重的{END}',
    '我老家在陕北深山的老村子里，逢年过节办酒席都要按老辈传下来的规矩排座次，礼数半点不能乱。院子里正在帮着张罗饭菜的那个人是我{REL}，说起来他也是从小看着我长大的{END}',
    '打小我就跟着爷爷在陕北农村老家生活，村口古槐树下立着老石碑，乡亲们最看重血脉渊源与老规矩。傍晚挑着担子进院门来的那位是我{REL}，在晚辈眼里他一直是最厚道的{END}',
    '我们那个陕北小山村至今保留着几百年的老祖祠，每逢清明冬至全村人都要去祭祖叙辈分。今天专门翻山越岭赶来家里串门的这位是我{REL}，他是我平时最亲近的{END}',
    '在陕北老家的黄土山沟里，十里八乡抬头不见低头见，家里来客人都得按老传统规规矩矩叫人。照片里站在老窑洞窗花前抽旱烟的那个人是我{REL}，他一直是我最挂念的{END}',
]

for f in DEEP_CLEAN_FRAMES:
    for banned in ['娘家', '本家', '外', '姻', '嫁', '娶', '婚', '堂', '表']:
        assert banned not in f, f"Banned char {banned} found in frame: {f}"

# Exact same REL_PAIRS as modern Chinese code-switch experiment!
REL_PAIRS = [
    ('父亲的哥哥', '母亲的哥哥'),
    ('爸爸的弟弟', '妈妈的弟弟'),
]

ENDINGS = [
    ('clean_shaanbei_en_uncle', ' uncle'),
    ('clean_shaanbei_zh_zhangbei', '长辈'),
    ('clean_shaanbei_zh_qinqi', '亲戚'),
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
            for f_idx, tpl in enumerate(DEEP_CLEAN_FRAMES):
                ta = tpl.format(REL=pat_rel, END=end_str)
                tb = tpl.format(REL=mat_rel, END=end_str)
                ida = tok.encode(ta, add_special_tokens=False)
                idb = tok.encode(tb, add_special_tokens=False)
                pa_id = len(probes)
                probes.append({'id': pa_id, 'mode': mode, 'text': ta, 'input_ids': ida, 'last_tok': tok.decode([ida[-1]])})
                pb_id = len(probes)
                probes.append({'id': pb_id, 'mode': mode, 'text': tb, 'input_ids': idb, 'last_tok': tok.decode([idb[-1]])})
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

    np.save(HEAVY / 'z_shaanbei_clean.npy', z_all)
    key_axes = [(13, 2665), (25, 3140), (26, 3526), (28, 544), (30, 684), (32, 3853), (42, 1300), (42, 1992), (54, 230), (56, 998)]
    out = {'elapsed_sec': round(time.time() - t0, 2), 'modes': {}}
    for mode, _ in ENDINGS:
        mpairs = [pr for pr in pairs if pr['mode'] == mode]
        mres = {'last_tok': probes[mpairs[0]['a']]['last_tok'], 'axes': {}}
        for L, c in key_axes:
            za = np.array([z_all[L, pr['a'], c] for pr in mpairs])
            zb = np.array([z_all[L, pr['b'], c] for pr in mpairs])
            diff = zb - za
            all_d = np.abs(np.mean([z_all[L, pr['b'], :] - z_all[L, pr['a'], :] for pr in mpairs], axis=0))
            rk = int((all_d > abs(diff.mean())).sum()) + 1
            top1 = int(np.argmax(all_d))
            mres['axes'][f'L{L:02d}_C{c}'] = {
                'pat': round(float(za.mean()), 3),
                'mat': round(float(zb.mean()), 3),
                'delta': round(float(diff.mean()), 3),
                'acc': f'{int((diff > 0).sum())}/{len(diff)}',
                'rank': rk,
                'self_top1': f'L{L:02d} C{top1} (|Δ|={all_d[top1]:.2f})',
            }
        out['modes'][mode] = mres
    (OUT / 'shaanbei_clean_results.json').write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
