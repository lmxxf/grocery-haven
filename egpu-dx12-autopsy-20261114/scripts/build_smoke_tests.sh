#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
flags=(-std=c++17 -O2 -Wall -Wextra -Wno-cast-function-type -static -static-libgcc -static-libstdc++)
x86_64-w64-mingw32-g++ "${flags[@]}" src/promoter_smoke.cpp -o build/promoter_smoke.exe -ld3d12 -ldxgi -ldxguid -lole32
x86_64-w64-mingw32-g++ "${flags[@]}" tests/promotion_fallback_test.cpp -o build/promotion_fallback_test.exe -ld3d12 -ldxgi -ldxguid -lpsapi -lole32 -luser32

x86_64-w64-mingw32-g++ "${flags[@]}" src/profiler_smoke.cpp -o build/profiler_smoke.exe -ld3d12 -ldxgi -ldxguid
