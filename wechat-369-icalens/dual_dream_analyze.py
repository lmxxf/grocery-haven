#!/usr/bin/env python3
"""Layer-at-a-time signed ICA × J-lens readout. Run only after capture exits.

The y² fractions below are coordinate-square shares, NOT Euclidean residual
energy: ICA writing columns are not orthogonal or equally normed.
"""
import os
os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')
import argparse
import gc
import hashlib
import json
import threading
import time
from pathlib import Path

import numpy as np
import torch
from safetensors import safe_open
from safetensors.torch import load_file
from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'dual_dream'
MODEL = Path('/home/lmxxf/work/models/Qwen3.8-27B-FP8')
REP = {16, 24, 32, 36, 38, 41, 48, 52, 54, 55, 56, 58, 60, 63}
TARGETS = ['6', ' 6', '8', ' 8', '5', ' 5', '-5', '-', '意大利', ' Italy', 'Italy', ' Italian',
           '欧元', ' euro', 'euro', ' Euro', 'EUR', '货币', '法定', '妈妈', '母亲', '儿子',
           '不可能', '不', '可能', '矛盾', '异常', '错误', '问题', ' impossible', 'impossible',
           ' contradiction', 'contradiction', ' impossible', ' memory', 'self', ' myself']
MIN_AVAIL = 1e9


def available():
    return int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines()
                    if l.startswith('MemAvailable:'))) / 1048576


def guard():
    global MIN_AVAIL
    while True:
        val = available()
        MIN_AVAIL = min(MIN_AVAIL, val)
        if val < 22:
            print('MEMORY_GUARD: MemAvailable below 22 GiB', flush=True)
            os._exit(73)
        time.sleep(.25)


def save(path, data):
    path = Path(path)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n')
    tmp.replace(path)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def metrics(y):
    p = np.square(y.astype(np.float64))
    norm2 = float(p.sum())
    p /= max(norm2, 1e-300)
    positive = p[p > 0]
    ordered = np.sort(p)[::-1]
    return dict(coordinate_square_sum=norm2,
                coordinate_square_entropy_nats=float(-(positive * np.log(positive)).sum()),
                effective_axes_entropy=float(np.exp(-(positive * np.log(positive)).sum())),
                participation_ratio=float(1 / max(float(np.square(p).sum()), 1e-300)),
                top1_square_share=float(ordered[:1].sum()),
                top5_square_share=float(ordered[:5].sum()),
                top10_square_share=float(ordered[:10].sum()))


def natural_contexts(layer, axes, tokenizer, heldout, ends):
    prior_path = ROOT / f'L{layer:02d}' / 'contexts_decoded.json'
    prior = json.loads(prior_path.read_text())['axes'] if prior_path.exists() else {}
    missing = [a for a in axes if str(a) not in prior]
    stats = json.loads((ROOT / f'L{layer:02d}' / 'statistics.json').read_text()) if missing else None
    out = {}
    for axis in sorted(axes):
        if str(axis) in prior:
            records = prior[str(axis)][:3]
        else:
            records = []
            for rank in range(3):
                ix = stats['top_heldout']['indices'][rank][axis]
                ri = int(np.searchsorted(ends, ix, side='right'))
                off = int(ix - (int(ends[ri-1]) if ri else 0))
                row = heldout[ri]
                records.append(dict(activation=stats['top_heldout']['values'][rank][axis],
                                    source_lang=row['lang'], document_id=row['document_id'],
                                    left_context=tokenizer.decode(row['token_ids'][max(0, off-64):off+1]),
                                    heldout_flat_token_index=ix, position_in_window=off))
        out[str(axis)] = records
    return out


def load_head():
    values = {}
    with safe_open(str(MODEL / 'outside.safetensors'), framework='pt', device='cuda') as f:
        for key, dest in [('lm_head.weight', 'head'), ('model.language_model.norm.weight', 'norm')]:
            w = f.get_tensor(key)
            if w.dtype in (torch.float8_e4m3fn, torch.float8_e5m2):
                scales = f.get_tensor(key + '_scale_inv')
                w = w.to(torch.bfloat16)
                w.view(w.shape[0]//128, 128, w.shape[1]//128, 128).mul_(scales[:, None, :, None].to(w.dtype))
            values[dest] = w.float()
    return values


def readout(vectors, head, norm, eps, tokenizer, target_ids, topk):
    """Input row directions already in final residual space; chunks bound logits memory."""
    result = []
    for start in range(0, len(vectors), 8):
        rows = vectors[start:start+8]
        z = rows * torch.rsqrt(rows.square().mean(-1, keepdim=True) + eps) * (1 + norm)
        logits = z @ head.T
        assert torch.isfinite(logits).all()
        vals, ids = logits.topk(topk, dim=-1)
        rank_data = {}
        for text, tid in target_ids.items():
            if tid is not None:
                target_logit = logits[:, tid]
                ranks = 1 + (logits > target_logit[:, None]).sum(-1)
                rank_data[text] = (target_logit.cpu().tolist(), ranks.cpu().tolist())
        for j, (row_ids, row_vals) in enumerate(zip(ids.cpu().tolist(), vals.cpu().tolist())):
            result.append(dict(top_tokens=[dict(token_id=tid, text=tokenizer.decode([tid]), logit=val)
                                           for tid, val in zip(row_ids, row_vals)],
                               target_ranks={text: dict(token_id=target_ids[text], rank=int(ranks[j]), logit=float(values[j]))
                                             for text, (values, ranks) in rank_data.items()}))
        del z, logits
    return result


def get_case_position(keys, case, position):
    key = f'{case}__{position}'
    return key if key in keys else None


def comparison_pairs(keys):
    pairs = []
    for name, left, right in [('dream_minus_chart', 'dream_self', 'chart_self'),
                               ('dream_minus_bare', 'dream_self', 'bare_self'),
                               ('saddle_minus_dream', 'saddle_self', 'dream_self'),
                               ('primed_minus_bare_age', 'dream_primed_age', 'trap_age_bare')]:
        for position in ['assistant', 'svg_close', 'assistant_header', 'age35']:
            a, b = get_case_position(keys, left, position), get_case_position(keys, right, position)
            if a and b:
                pairs.append((name + '__' + position, a, b))
    return pairs


@torch.inference_mode()
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--layers', help='Comma separated subset for development; omit for all 64')
    args = parser.parse_args()
    layers = list(range(64)) if not args.layers else [int(i) for i in args.layers.split(',')]
    assert available() >= 22
    threading.Thread(target=guard, daemon=True).start()
    torch.set_num_threads(8)
    torch.set_float32_matmul_precision('highest')
    started = time.time()
    capture_path = OUT / 'capture.json'
    residual_path = OUT / 'capture_residuals.npz'
    capture = json.loads(capture_path.read_text())
    assert capture.get('status') == 'PASS', 'capture checkpoint is not a completed PASS'
    assert sha256(residual_path) == capture['residual_sha256'], 'capture residual SHA256 mismatch'
    required_cases = {'arithmetic_spaced','arithmetic_compact','boot_currency','trap_age_bare','dream_self','chart_self','saddle_self','bare_self','dream_primed_age'}
    assert set(capture['cases']) == required_cases
    data = np.load(residual_path)
    keys = sorted(data.files)
    expected_keys = {f'{case_id}__{position}' for case_id, case in capture['cases'].items() for position in case['positions']}
    assert set(keys) == expected_keys, 'missing or unexpected selected residual positions'
    assert keys and all(data[k].shape == (64, 5120) and np.isfinite(data[k]).all() for k in keys)
    residuals = np.stack([data[k] for k in keys], axis=1)
    pairs = comparison_pairs(keys)
    token = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    target_ids, target_sequences = {}, {}
    for text in dict.fromkeys(TARGETS):
        ids = token.encode(text, add_special_tokens=False)
        target_sequences[text] = ids
        target_ids[text] = ids[0] if len(ids) == 1 else None
    # Exact predeclared token family: whitespace-trimmed decoded token equals '6'.
    six_ids = {}
    for raw, tid in token.get_vocab().items():
        if '6' in raw:
            decoded = token.decode([tid])
            if decoded.strip() == '6':
                target_ids[decoded] = tid
                six_ids[decoded] = tid
    heldout = [r for r in (json.loads(l) for l in (ROOT / 'corpus.jsonl').read_text().splitlines())
               if r['split'] == 'heldout']
    ends = np.cumsum([len(r['token_ids']) for r in heldout])
    values = load_head()
    eps = json.loads((MODEL / 'config.json').read_text())['text_config']['rms_norm_eps']
    checkpoint = torch.load(ROOT / 'lens_n100.pt', map_location='cpu', mmap=True, weights_only=True)
    layer_dir = OUT / 'analysis_layers'
    layer_dir.mkdir(exist_ok=True, parents=True)
    fingerprint = dict(capture_json_sha256=sha256(capture_path), residual_npz_sha256=sha256(residual_path),
                       analysis_script_sha256=sha256(Path(__file__)),
                       ica_manifest_sha256=sha256(ROOT/'hf_release'/'icalens.json'),
                       j_lens_checkpoint_sha256=sha256(ROOT/'lens_n100.pt'))
    coordinates = np.zeros((64, len(keys), 5120), dtype=np.float32)
    overview = []
    all_case_metrics = {key: [] for key in keys}
    total_checks = []
    for layer in layers:
        art = load_file(str(ROOT / 'hf_release' / 'artifacts' / 'resid_post' / f'layer_{layer:02d}.safetensors'), device='cuda')
        C, M, c = art['reading_matrix'], art['writing_matrix'], art['center']
        h = torch.as_tensor(residuals[layer], device='cuda')
        units = h / h.norm(dim=-1, keepdim=True).clamp_min(1e-12)
        yy = (units - c) @ C.T
        reconstructed = yy @ M.T + c
        errors = (reconstructed - units).abs().amax(-1).cpu().numpy()
        assert torch.isfinite(yy).all() and float(errors.max()) < 2e-4, (layer, errors.max())
        yn = yy.cpu().numpy()
        coordinates[layer] = yn
        J = None if layer == 63 else checkpoint['J'][layer].float().cuda()
        entries, differences, needed = {}, {}, set()
        for i, key in enumerate(keys):
            case_id, position = key.split('__', 1)
            full_readout = position != 'assistant_header' or layer in REP
            indices = np.argsort(-np.abs(yn[i]), kind='stable')[:10]
            p = yn[i].astype(np.float64)**2
            p /= max(float(p.sum()), 1e-300)
            topaxes = []
            for rank, axis in enumerate(indices, 1):
                axis = int(axis)
                sign = 1 if yn[i, axis] >= 0 else -1
                code = f'{axis}:{sign:+d}'
                if full_readout:
                    needed.add((axis, sign))
                topaxes.append(dict(axis=axis, absolute_activation_rank=rank, y=float(yn[i, axis]),
                                    coordinate_square_share=float(p[axis]), readout_key=code if full_readout else None))
            met = metrics(yn[i])
            all_case_metrics[key].append(dict(layer=layer, **met))
            entries[key] = dict(case_id=case_id, position=position, metrics=met,
                                reconstruction_max_abs_error=float(errors[i]), top10_axes=topaxes,
                                full_readout=full_readout)
        for name, a, b in pairs:
            ai, bi = keys.index(a), keys.index(b)
            delta = yn[ai] - yn[bi]
            selections = {}
            full_readout = not name.endswith('__assistant_header') or layer in REP
            for label, order in [('positive', np.argsort(-delta, kind='stable')),
                                  ('negative', np.argsort(delta, kind='stable'))]:
                top = []
                for axis in order[:8]:
                    axis = int(axis)
                    sign = 1 if delta[axis] >= 0 else -1
                    actual = 1 if yn[ai, axis] >= 0 else -1
                    code, actual_code = f'{axis}:{sign:+d}', f'{axis}:{actual:+d}'
                    if full_readout:
                        needed.update([(axis, sign), (axis, actual)])
                    top.append(dict(axis=axis, delta_y=float(delta[axis]), y_left=float(yn[ai, axis]),
                                    y_right=float(yn[bi, axis]), readout_key=code if full_readout else None,
                                    left_actual_signed_readout_key=actual_code if full_readout else None,
                                    absolute_delta_rank=int(1 + np.count_nonzero(np.abs(delta) > abs(delta[axis])))))
                selections[label] = top
            differences[name] = dict(left=a, right=b, interpretation='left minus right in fixed signed ICA coordinates',
                                     delta_l2=float(np.linalg.norm(delta)),
                                     delta_l1=float(np.abs(delta).sum()), **selections)
        needed = sorted(needed)
        dirs = torch.stack([sign * M[:, axis] for axis, sign in needed])
        transformed = dirs if J is None else dirs @ J.T
        j_read = readout(transformed, values['head'], values['norm'], eps, token, target_ids, 8)
        vanilla_read = readout(dirs, values['head'], values['norm'], eps, token, target_ids, 5)
        direction_readouts = {f'{axis}:{sign:+d}': dict(axis=axis, sign=sign, jlens=j, vanilla=v)
                              for (axis, sign), j, v in zip(needed, j_read, vanilla_read)}
        active_idx = [i for i, key in enumerate(keys) if entries[key]['full_readout']]
        whole = h[active_idx] if J is None else h[active_idx] @ J.T
        total_read = readout(whole, values['head'], values['norm'], eps, token, target_ids, 10)
        for i, rd in zip(active_idx, total_read):
            entries[keys[i]]['total_jlens'] = rd
        if layer == 63:
            for key, entry in entries.items():
                if entry['position'] not in ('last', 'assistant'):
                    continue
                reference = capture.get('cases', {}).get(entry['case_id'], {}).get('generation', {}).get('prefill_next_top10', [])
                observed = entry.get('total_jlens', {}).get('top_tokens', [])
                if reference and observed:
                    ref_ids = [x['token_id'] for x in reference]
                    obs_ids = [x['token_id'] for x in observed]
                    obs_map = {x['token_id']:x['logit'] for x in observed}
                    logit_errors = [abs(float(x['logit'])-obs_map[x['token_id']]) for x in reference if x['token_id'] in obs_map]
                    check = dict(case_id=entry['case_id'], position=entry['position'], top1_match=ref_ids[0]==obs_ids[0],
                                 top10_intersection=len(set(ref_ids)&set(obs_ids)),
                                 maximum_common_top10_logit_error=max(logit_errors) if logit_errors else None,
                                 float_note='float32 readout vs original BF16 model head')
                    total_checks.append(check)
                    entry['L63_actual_prefill_comparison'] = check
        contexts = natural_contexts(layer, {axis for axis, sign in needed}, token, heldout, ends) if layer in REP else {}
        result = dict(layer=layer, entries=entries, differences=differences,
                      direction_readouts=direction_readouts, positive_tail_natural_contexts=contexts,
                      natural_context_warning='Only highest POSITIVE oriented heldout scores are available; these do not validate negative-axis labels.',
                      input_fingerprint=fingerprint, minimum_MemAvailable_GiB=MIN_AVAIL)
        save(layer_dir / f'layer_{layer:02d}.json', result)
        maxerr = float(errors.max())
        brief = dict(layer=layer, maximum_reconstruction_error=maxerr, direction_readout_count=len(needed))
        overview.append(brief)
        print('ANALYZED_LAYER', layer, 'directions', len(needed), 'reconstruction', f'{maxerr:.3g}', 'available_GiB', round(available(), 2), flush=True)
        del art, C, M, c, h, yy, reconstructed, units, dirs, transformed, whole, J
        gc.collect()
        torch.cuda.empty_cache()
    coord_path = OUT / 'analysis_coordinates.npz'
    np.savez_compressed(coord_path, coordinates=coordinates, keys=np.array(keys))
    summary = build_summary(layer_dir, layers, keys, capture)
    summary.update(case_metrics=all_case_metrics, layer_overview=overview, L63_actual_prefill_comparisons=total_checks,
                   maximum_reconstruction_error=max(r['maximum_reconstruction_error'] for r in overview),
                   minimum_MemAvailable_GiB=MIN_AVAIL, elapsed_seconds=time.time()-started)
    save(OUT / 'analysis_summary.json', summary)
    save(OUT / 'analysis_brief.json', build_brief(summary))
    manifest = dict(status='PASS' if layers == list(range(64)) else 'PARTIAL', layers=layers,
                    residual_keys=keys, target_token_ids=target_ids, target_token_sequences=target_sequences,
                    six_exact_token_ids=six_ids,
                    representative_context_layers=sorted(REP), float32_matmul_precision='highest for coordinates, reconstruction, J transport, and vocabulary head', comparisons=[p[0] for p in pairs],
                    formulas=dict(coordinates='u=h/max(norm(h),1e-12); y=(u-c) @ C.T',
                                  total_readout='head(RMSNorm(h @ J.T))', axis_readout='head(RMSNorm(sign(y_j)*M[:,j] @ J.T))',
                                  final_RMSNorm=f'v*rsqrt(mean(v²)+{eps})*(1+norm_weight)',
                                  coordinate_share='p_j=y_j²/sum(y²), not Euclidean residual energy'),
                    limitations=['Writing-direction vocabulary is a probe, not a decoded thought or causal proof.',
                                 'ICA is fitted on natural EN/ZH text; SVG and chat-template positions can be out of distribution.',
                                 'SVG stimuli enter as source-code text, not rendered images; geometric structure is confounded with XML/token-pattern differences.',
                                 'Equal UTF-8 byte length does not imply equal token count or equal target position.',
                                 'Difference directions describe a coordinate change; they need not share the sign of actual activation.',
                                 'Natural contexts sample only the positive heldout tail, not negative-axis contexts.',
                                 'Raw-score comparisons here are descriptive single prompts, without random rotation/PCA causal controls.',
                                 'The three SVG conditions share the question suffix; bare_self intentionally has a different opening phrase.',
                                 'L63 float32 readout can differ slightly from actual BF16 model logits.'],
                    input_fingerprint=fingerprint, output_files=['analysis_layers/layer_XX.json', 'analysis_coordinates.npz', 'analysis_summary.json', 'analysis_brief.json'],
                    minimum_MemAvailable_GiB=MIN_AVAIL)
    save(OUT / 'analysis_manifest.json', manifest)
    print('ANALYSIS_COMPLETE', OUT / 'analysis_summary.json', flush=True)


def build_summary(layer_dir, layers, keys, capture):
    """Compact hypothesis checks preserve every layer, including null results."""
    arithmetic, boot, trap, self_diffs = [], [], [], []
    def targets(record, names, max_rank):
        hits = []
        for name in names:
            item = record.get('target_ranks', {}).get(name)
            if item and item['rank'] <= max_rank:
                hits.append(dict(text=name, **item))
        return hits
    for layer in layers:
        res = json.loads((layer_dir / f'layer_{layer:02d}.json').read_text())
        read = res['direction_readouts']
        for key, e in res['entries'].items():
            if not e['full_readout']:
                continue
            case, pos = key.split('__', 1)
            if case.startswith('arithmetic'):
                axes = []
                for a in e['top10_axes']:
                    rd = read[a['readout_key']]['jlens']
                    h = targets(rd, [text for text in rd['target_ranks'] if text.strip() == '6'], 8)
                    if h:
                        axes.append(dict(axis=a['axis'], activation_rank=a['absolute_activation_rank'],
                                         y=a['y'], coordinate_square_share=a['coordinate_square_share'], hits=h,
                                         top_tokens=rd['top_tokens']))
                arithmetic.append(dict(layer=layer, case_id=case, position=pos,
                                       total_six_ranks={k:v for k,v in e['total_jlens']['target_ranks'].items() if k.strip() == '6'},
                                       total_top10=e['total_jlens']['top_tokens'], top10_axes_with_six_top8=axes,
                                       six_axis_counts={f'top{k}':sum(any(h['rank']<=k for h in a['hits']) for a in axes) for k in [1,3,8]},
                                       loudest_axis=dict(e['top10_axes'][0], readout=read[e['top10_axes'][0]['readout_key']]['jlens'])))
            if case == 'boot_currency':
                italy, euro, currency_related = [], [], []
                for a in e['top10_axes']:
                    rd = read[a['readout_key']]['jlens']
                    for group, names in [(italy, ['意大利', ' Italy', 'Italy', ' Italian']),
                                          (euro, ['欧元', ' euro', 'euro', ' Euro', 'EUR']),
                                          (currency_related, ['货币', '法定'])]:
                        hits = targets(rd, names, 8)
                        if hits:
                            group.append(dict(axis=a['axis'], activation_rank=a['absolute_activation_rank'],
                                              y=a['y'], hits=hits, top_tokens=rd['top_tokens']))
                distinct = any(a['axis'] != b['axis'] for a in italy for b in euro)
                boot.append(dict(layer=layer, position=pos, italy_axes=italy, euro_axes=euro, currency_related_axes=currency_related,
                                 distinct_italy_euro_axes_same_layer=distinct,
                                 distinct_italy_currency_related_axes_same_layer=any(a['axis'] != b['axis'] for a in italy for b in currency_related), total_top10=e['total_jlens']['top_tokens']))
            if case in ['trap_age_bare', 'dream_primed_age'] and pos != 'assistant_header':
                trap.append(dict(layer=layer, case_id=case, position=pos,
                                 total_top10=e['total_jlens']['top_tokens'],
                                 axes=[dict(a, top_tokens=read[a['readout_key']]['jlens']['top_tokens']) for a in e['top10_axes']]))
        if layer in REP:
            for name, d in res['differences'].items():
                if not name.endswith('__assistant'):
                    continue
                self_diffs.append(dict(layer=layer, comparison=name, delta_l2=d['delta_l2'],
                                       positive=[dict(a, top_tokens=read[a['readout_key']]['jlens']['top_tokens'],
                                                      positive_natural_context=res['positive_tail_natural_contexts'].get(str(a['axis']), [])[:1])
                                                 for a in d['positive']],
                                       negative=[dict(a, top_tokens=read[a['readout_key']]['jlens']['top_tokens']) for a in d['negative']]))
    cases = capture.get('cases', {})
    return dict(arithmetic=arithmetic, boot_currency=boot, trap_age=trap,
                representative_self_differences=self_diffs,
                generations={k:v.get('generation') for k,v in cases.items()},
                warning='Target-family matching uses registered single token IDs, not arbitrary semantic labels. Multi-token strings are not assigned a fabricated next-token rank.')


def build_brief(summary):
    arithmetic = []
    for case in ['arithmetic_spaced', 'arithmetic_compact']:
        rows = [x for x in summary['arithmetic'] if x['case_id'] == case]
        arithmetic.append(dict(case_id=case,
                               six_top1_layers=[x['layer'] for x in rows if x['six_axis_counts']['top1']],
                               six_top3_layers=[x['layer'] for x in rows if x['six_axis_counts']['top3']],
                               six_top8_layers=[x['layer'] for x in rows if x['six_axis_counts']['top8']],
                               focus_L54_58=[dict(layer=x['layer'], total_six_ranks=x['total_six_ranks'],
                                                   six_axis_counts=x['six_axis_counts'],
                                                   hit_axes=[dict(axis=a['axis'], activation_rank=a['activation_rank'],
                                                                  hits=a['hits']) for a in x['top10_axes_with_six_top8']])
                                               for x in rows if 54<=x['layer']<=58]))
    boot = summary['boot_currency']
    return dict(status='PASS' if len(summary['layer_overview'])==64 else 'PARTIAL', arithmetic=arithmetic,
                boot_italy_euro_distinct_layers=[x['layer'] for x in boot if x['distinct_italy_euro_axes_same_layer']],
                boot_italy_generic_currency_distinct_layers=[x['layer'] for x in boot if x['distinct_italy_currency_related_axes_same_layer']],
                generations=summary['generations'],
                maximum_reconstruction_error=summary['maximum_reconstruction_error'],
                minimum_MemAvailable_GiB=summary['minimum_MemAvailable_GiB'], elapsed_seconds=summary['elapsed_seconds'],
                L63_actual_prefill_comparisons=summary['L63_actual_prefill_comparisons'],
                scope='Top10 absolute ICA activation axes only; target matching is descriptive and not a semantic axis annotation.')


if __name__ == '__main__':
    main()
