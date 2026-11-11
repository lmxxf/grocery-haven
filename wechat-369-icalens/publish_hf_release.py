#!/usr/bin/env python3
"""Publish the checked native release, then anonymously round-trip one layer."""
import hashlib
import os
import json
import tempfile
from pathlib import Path
import numpy as np
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
from huggingface_hub import HfApi, CommitOperationAdd
from safetensors import safe_open
from icalens import ICALens

ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / 'hf_release'
REPO = 'lmxxf/Qwen3.8-27B-ica-lens'

def main():
    manifest = json.loads((RELEASE / 'icalens.json').read_text())
    assert sorted(map(int, manifest['layers'])) == list(range(64))
    total = 0
    for layer in range(64):
        entry = manifest['layers'][str(layer)]
        assert entry['n_components'] == 5120
        assert entry['fitting']['n_samples'] == 200704
        path = RELEASE / entry['file']
        with safe_open(path, framework='np') as f:
            assert set(f.keys()) == {'center', 'reading_matrix', 'writing_matrix'}
            for key in f.keys():
                a = f.get_tensor(key)
                assert a.shape == ((5120,) if key == 'center' else (5120,5120))
                assert a.dtype == np.float32 and np.isfinite(a).all()
        total += path.stat().st_size
    print(f'VALIDATED 64 layers; {total} tensor bytes', flush=True)
    api = HfApi()
    api.create_repo(REPO, repo_type='model', private=False, exist_ok=True)
    assert not api.model_info(REPO).private
    remote = {f.rfilename: f for f in api.model_info(REPO, files_metadata=True).siblings}
    pending = []
    for layer in range(64):
        name = manifest['layers'][str(layer)]['file']
        path = RELEASE / name
        existing = remote.get(name)
        if existing and existing.lfs:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if existing.lfs.sha256 == digest:
                print('ALREADY_UPLOADED', name, flush=True)
                continue
        pending.append(name)
    for start in range(0, len(pending), 4):
        names = pending[start:start+4]
        api.create_commit(repo_id=REPO, num_threads=4,
            operations=[CommitOperationAdd(path_in_repo=name, path_or_fileobj=RELEASE/name) for name in names],
            commit_message=f'Upload ICA layers {start+1}-{start+len(names)} of {len(pending)}')
        print(f'COMMITTED_WEIGHTS {start+len(names)}/{len(pending)}', flush=True)
    result = api.create_commit(repo_id=REPO, operations=[
        CommitOperationAdd(path_in_repo=name, path_or_fileobj=RELEASE/name)
        for name in ['icalens.json', 'README.md']],
        commit_message='Publish 64-layer bilingual oriented ICA Lens manifest and model card')
    sha = result.oid
    print('UPLOADED', sha, flush=True)
    files = api.list_repo_files(REPO, revision=sha)
    assert all(manifest['layers'][str(i)]['file'] in files for i in range(64))
    with tempfile.TemporaryDirectory(prefix='icalens-remote-smoke-') as cache:
        lens = ICALens.from_pretrained(REPO, revision=sha, cache_dir=cache, token=False)
        assert list(lens.available_layers) == list(range(64))
        assert not list(Path(cache).rglob('*.safetensors'))
        x = np.random.default_rng(369).standard_normal((4,5120)).astype(np.float32)
        scores = lens.transform(x, layer=41)
        restored = lens.inverse_transform(scores, layer=41)
        error = float(np.max(np.abs(restored-x/np.linalg.norm(x,axis=-1,keepdims=True))))
        assert scores.shape == (4,5120) and np.isfinite(scores).all() and error < 1e-4
        downloaded = list(Path(cache).rglob('*.safetensors'))
        assert len(downloaded) == 1 and downloaded[0].name == 'layer_41.safetensors'
        def sha256(p):
            h=hashlib.sha256()
            with open(p,'rb') as f:
                for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
            return h.hexdigest()
        digest = sha256(downloaded[0])
        assert digest == sha256(RELEASE / manifest['layers']['41']['file'])
    report = dict(repo=REPO,url=f'https://huggingface.co/{REPO}',commit_sha=sha,layers=64,tensor_bytes=total,remote_smoke=dict(status='PASS',authentication=False,cache='fresh temporary directory, removed after validation',downloaded_layers=[41],scores_shape=[4,5120],reconstruction_max_abs_error=error,layer41_sha256=digest))
    (ROOT/'hf_publish_result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)

if __name__ == '__main__': main()
