#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

source .venv/bin/activate 2>/dev/null || true

if [[ ! -x "build/aposma-analyzer" ]]; then
  echo "Aposma native analyzer is not built. Run:" >&2
  echo "  cmake -S . -B build -DCMAKE_BUILD_TYPE=Release" >&2
  echo "  cmake --build build -j\$(nproc)" >&2
  exit 1
fi

./build/aposma-analyzer examples/sample_cpp/mini.cpp -- -std=c++20 -Iexamples/sample_cpp | tee /tmp/aposma-analysis.json

echo
echo "Deterministic review:"
python -m codelens.cli review examples/sample_cpp --no-ai
