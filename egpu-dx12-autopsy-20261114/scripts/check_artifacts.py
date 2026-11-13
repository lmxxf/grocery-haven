#!/usr/bin/env python3
"""Check x64 PE format, system-only imports, and target DXGI name/ordinal parity."""
import pathlib, re, subprocess, hashlib, json
root = pathlib.Path(__file__).resolve().parents[1]
def inspect(path):
    return subprocess.check_output(['x86_64-w64-mingw32-objdump', '-p', str(path)], text=True)
expected = {}
for line in (root/'src/dxgi.def').read_text().splitlines():
    m = re.match(r'\s*(\w+)=proxy_\d+\s+@(\d+)', line)
    if m: expected[m[1]] = int(m[2])
checks = []
for name in ['d3d12_egpu_probe.exe', 'dxgi.dll']:
    path = root/'build'/name
    dump = inspect(path)
    assert 'pei-x86-64' in dump, name
    imports = re.findall(r'DLL Name:\s*(\S+)', dump)
    allowed = {'kernel32.dll','msvcrt.dll','ole32.dll','d3d12.dll','dxgi.dll','d3dcompiler_47.dll','psapi.dll','user32.dll'}
    assert all(d.lower() in allowed for d in imports), imports
    if name == 'dxgi.dll':
        base = int(re.search(r'Ordinal Base\s+(\d+)', dump)[1])
        block = dump.split('[Ordinal/Name Pointer] Table')[1].split('The Function Table')[0]
        exports = {n:int(i)+base for i,n in re.findall(r'\[\s*(\d+)\]\s+(\w+)',block)}
        assert exports == expected, (exports,expected)
    checks.append({'file':name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'imports':imports})
assert len(expected)==20
print(json.dumps({'passed':True,'artifacts':checks},indent=2))
