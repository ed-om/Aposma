#!/usr/bin/env bash
set -euo pipefail

sudo apt update
sudo apt install -y build-essential cmake git python3 python3-venv python3-pip clang llvm-dev libclang-dev libclang-cpp-dev

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e '.[dev,server]'

echo
printf '%s\n' 'Next:'
printf '%s\n' '  1) install Ollama from its official installer'
printf '%s\n' '  2) ollama pull qwen2.5-coder:3b'
printf '%s\n' '  3) cmake -S . -B build -DCMAKE_BUILD_TYPE=Release'
printf '%s\n' '  4) cmake --build build -j"$(nproc)"'
