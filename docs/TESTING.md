# Testing and validation

## Python tests

From the repository root, activate the project's virtual environment and run:

```bash
python -m pytest -q
python -m compileall -q codelens tests
```

Tests cover evidence construction, scoring/ranking, Ollama health handling, the HTTP API, Markdown file generation, and repository-source parsing/resolution. GitHub network cloning and the actual C++ build are environment-dependent and are not replaced by mocked unit tests.

## Native analyzer

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
./build/aposma-analyzer examples/sample_cpp/mini.cpp -- -std=c++20 -Iexamples/sample_cpp
```

The executable should emit JSON. If it reports missing compiler built-in headers such as `stddef.h`, check that the installed GCC and Clang development packages are present and that the Python wrapper is using the intended analyzer binary via `APOSMA_ANALYZER_BIN`.

## CLI smoke tests

These commands exercise both key user-visible flows when a working native analyzer binary exists:

```bash
python -m codelens.cli review examples/sample_cpp --no-ai
python -m codelens.cli docs examples/sample_cpp --no-ai
find examples/sample_cpp/.aposma/docs -type f -name '*.md' -print

# Or run both smoke tests and verify index.md automatically
./scripts/smoke_cli.sh
```

Repeat with `https://github.com/owner/repository` to validate remote checkout. Public repositories require network connectivity; private repositories require read access through `APOSMA_GITHUB_TOKEN` or configured Git credentials.

## Frontend build

```bash
cd frontend
npm install
npm run build
```

For local interaction, run FastAPI on port 8000 and Vite on port 5173 as described in the README. `/api/status` should return analyzer/model status, and successful documentation generation should report the `.aposma/docs/` output path.
