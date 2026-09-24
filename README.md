# Aposma

**Aposma** is a local-first code-intelligence engine for AI-assisted software maintenance.

It analyzes **C++ repositories**, builds a machine-readable representation of their structure, runs deterministic static-analysis rules, packages the evidence, and optionally sends that evidence to a **local Qwen2.5-Coder-3B-Instruct model via Ollama** for grounded code review and documentation generation.

## Project philosophy

```text
C++ source
   ↓
Clang AST
   ↓
Code Knowledge Model
   ↓
Static Analysis + Git Diff
   ↓
Evidence Package
   ↓
Local SLM (optional but recommended)
   ↓
Code Review / Documentation
```

The SLM is deliberately not the source of truth. Deterministic analysis produces facts; the model interprets those facts.

## $0 budget

The core system is local and uses open-source/free tooling:

- C++20
- LLVM/Clang LibTooling + AST Matchers
- Python 3.11+
- SQLite
- Ollama
- Qwen2.5-Coder-3B-Instruct
- Git
- Docker (optional, for sandboxed test execution)
- GitHub App integration (optional until the core tool works)

No paid model API is required.

## Current MVP scope

- C++ only
- repository + Git diff analysis
- AST extraction
- call graph edges
- deterministic findings for a small rule set
- structured evidence package
- local SLM integration through Ollama
- code review output
- documentation generation
- SQLite history
- CLI
- GitHub webhook/check scaffolding

## 1. Prerequisites

On Ubuntu/Debian/Mint, install the development toolchain. Package names vary slightly by distro/LLVM version; you need a matching set of Clang/LLVM development packages.

```bash
sudo apt update
sudo apt install -y build-essential cmake git python3 python3-venv python3-pip clang llvm-dev libclang-dev libclang-cpp-dev
```

Install Ollama separately from its official installer, then pull the model:

```bash
ollama pull qwen2.5-coder:3b
```

If 3B is too slow or memory-heavy on your machine, the architecture supports swapping the model through `APOSMA_OLLAMA_MODEL`.

## 2. Build the C++ analyzer

From the repository root:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)
```

You should get:

```text
build/aposma-analyzer
```

### If CMake cannot find Clang

Set `LLVM_DIR` to the directory containing `LLVMConfig.cmake`, and `Clang_DIR` to the directory containing `ClangConfig.cmake` if your distro requires it.

Examples vary by LLVM version, so inspect:

```bash
llvm-config --cmakedir
llvm-config --libdir
```

## 3. Install the Python package

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e '.[dev,server]'
```

## 4. Try the analyzer directly

```bash
./build/aposma-analyzer examples/sample_cpp/mini.cpp -- -std=c++20 -Iexamples/sample_cpp
```

The analyzer prints JSON to stdout.

## 5. Run Aposma from the CLI

```bash
aposma review examples/sample_cpp --no-ai
```

To use Ollama:

```bash
aposma review examples/sample_cpp
```

Environment variables:

```bash
export APOSMA_OLLAMA_MODEL=qwen2.5-coder:3b
export APOSMA_OLLAMA_URL=http://127.0.0.1:11434
```

## 6. Generate documentation

```bash
aposma docs examples/sample_cpp
```

## 7. Run tests

```bash
pytest
```

## 8. GitHub integration

The server implementation is in `codelens/server.py` and the GitHub client is in `codelens/github.py`.

You will eventually create a GitHub App with the minimum repository permissions necessary. For check runs, GitHub requires the Checks permission to be writable by the App. See GitHub's current Checks documentation before configuring the App. The local server can be exposed with a free tunnel during development.

Start the server:

```bash
uvicorn codelens.server:app --host 127.0.0.1 --port 8000
```

Then configure the webhook URL to:

```text
POST /webhooks/github
```

Set:

```bash
export APOSMA_GITHUB_APP_ID=...
export APOSMA_GITHUB_PRIVATE_KEY_PATH=/path/to/private-key.pem
export APOSMA_GITHUB_WEBHOOK_SECRET=...
```

The GitHub integration is intentionally separated from the local analyzer so that you can finish and evaluate the core system without needing a publicly reachable server.

## 9. Development order

1. Get the C++ analyzer working.
2. Understand the AST output.
3. Stabilize the Code Knowledge Model.
4. Add static-analysis findings.
5. Add Git diff context.
6. Add the local SLM.
7. Add documentation.
8. Evaluate the system.
9. Add GitHub integration last.

Do **not** start with React or GitHub webhooks.

## 10. Repository layout

```text
aposma/
├── analyzer/              # C++/Clang program-analysis engine
├── codelens/              # Python orchestration + CLI + SLM + GitHub
├── examples/              # small demo repository/code
├── tests/                 # Python tests
├── docs/                  # architecture, threat model, learning map
├── docker/                # optional sandbox image
├── scripts/               # setup helpers
├── CMakeLists.txt
├── pyproject.toml
└── README.md
```

## Research direction

Aposma should eventually compare at least these configurations:

```text
A. raw code → SLM
B. code + diff → SLM
C. code + diff + AST → SLM
D. code + diff + AST + static findings → SLM
E. full structured evidence → SLM
```

Measure precision, recall, false positives, documentation accuracy, hallucination rate, and latency.
