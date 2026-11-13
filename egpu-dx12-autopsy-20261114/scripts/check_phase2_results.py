#!/usr/bin/env python3
import pathlib,re,json
root=pathlib.Path(__file__).resolve().parents[1]
dir=root/'build/phase2'
def fields(line):return dict(re.findall(r'(\w+)=([^ ]+)',line))
def promotions(text):return [fields(l) for l in text.splitlines() if l.startswith('promotion ')]
def snapshots(text):return [fields(l) for l in text.splitlines() if l.startswith('snapshot ')]
summary={}
for mode in [0,1]:
    output=(dir/f'mode{mode}_probe.txt').read_text()
    rows=[fields(l) for l in output.splitlines() if l.startswith('benchmark ')]
    assert len(rows)==18 and all(r['validation_bad']=='0' for r in rows)
    assert 'completed=1' in output and 'FATAL' not in output
    assert 'exit_code=0' in (dir/f'mode{mode}_exit.txt').read_text()
    log=(dir/f'mode{mode}_telemetry.log').read_text();p=promotions(log)[-1];ss=snapshots(log)
    assert 'crt_exit code=0' in log
    assert all(int(v['hook_failures'])==0 for v in ss)
    assert int(p['promoted_live_bytes'])==0 and int(p['gpu_upload_supported'])==1
    assert int(p['promoted_buffers'])==(2 if mode else 0)
    assert int(p['map_calls'])==2 and int(p['map_promoted_calls'])==(2 if mode else 0)
    assert int(p['root_promoted_binds' if mode else 'root_upload_binds'])==69
    totals={key:sum(int(v[key]) for v in ss) for key in ['submissions','resolve','upload_default_copies','default_readback_copies','resources_created']}
    assert totals==dict(submissions=532,resolve=414,upload_default_copies=69,default_readback_copies=18,resources_created=24),totals
    summary[f'mode{mode}']={'direct_upload_32MiB_K8':next(v for v in rows if v['case']=='Direct-UPLOAD' and v['K']=='8'),'final_promotion':p,'telemetry_totals':totals}
for mode,spoof in [(0,0),(1,0),(1,1)]:
    name=f'promoter_mode{mode}_spoof{spoof}'
    out=(dir/f'{name}.txt').read_text();log=(dir/f'{name}.log').read_text();p=promotions(log)[-1]
    assert 'smoke_completed=1' in out and 'FATAL' not in out
    assert out.count('copy_validation_bytes=4194304 bad=0')==3
    assert int(p['promoted_live_bytes'])==0 and int(p['gpu_upload_supported'])==1
    assert all(int(v['hook_failures'])==0 for v in snapshots(log))
    assert int(p['cbv_upload_creates'])+int(p['cbv_promoted_creates'])==3
    assert int(p['srv_upload_creates'])+int(p['srv_promoted_creates'])==3
    assert int(p['map_calls'])==6 and int(p['map_explicit_reads'])==3
    if mode:
        assert int(p['promoted_heaps'])==4 and int(p['promoted_buffers'])==5
        assert int(p['promoted_peak_bytes'])==8*1048576 and int(p['quota_skips'])==1
        assert int(p['promote_fallbacks'])==4
    summary[name]=p
assert 'fallback_test_passed=1' in (dir/'fallback_test.txt').read_text()
a=float(summary['mode0']['direct_upload_32MiB_K8']['gpu_median_ms']);b=float(summary['mode1']['direct_upload_32MiB_K8']['gpu_median_ms'])
summary['GPU_speedup']=a/b
summary['passed']=True
print(json.dumps(summary,indent=2))
