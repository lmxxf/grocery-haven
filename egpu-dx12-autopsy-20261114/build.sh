#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build
CXX=x86_64-w64-mingw32-g++
flags=(-std=c++17 -O2 -Wall -Wextra -Wno-cast-function-type -static -static-libgcc -static-libstdc++)
if [[ "${1:-}" != "--dll-only" ]]; then
 "$CXX" "${flags[@]}" src/probe.cpp -o build/d3d12_egpu_probe.exe -ld3d12 -ldxgi -ld3dcompiler -ldxguid
fi
if [[ -f src/telemetry.cpp ]]; then
 "$CXX" "${flags[@]}" -shared src/telemetry.cpp src/forward.S src/dxgi.def -o build/dxgi.dll -ldxguid -lpsapi -lole32 -luser32
fi
