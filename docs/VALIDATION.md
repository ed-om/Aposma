# Validation status

## Verified in this packaging environment

- `python -m compileall -q codelens tests` completed successfully.
- Python unit/API tests passed: **21 passed**.
- Tests cover the FastAPI health, review, documentation, status, and history flows; repository-source URL parsing; indexed Markdown generation; path cleanup; ranking; evidence packaging; Ollama health handling, and CLI command wiring.
- CLI review and docs commands were smoke-tested using a stub analyzer JSON response. This validates the command flow and Markdown file writing, not the actual native analyzer binary.

## Not verified end to end here

- The native C++ analyzer was not compiled because this environment does not include the LLVM development CMake package (`LLVMConfig.cmake`).
- The Vite production bundle was not built because npm dependency installation timed out while fetching from the package registry.
- GitHub clone against a live repository, private-repository authentication, Ollama model generation, and an actual native-analyzer review were not run here.

These are environment-dependent checks. Passing Python unit tests does not prove the native analyzer, npm installation, GitHub connectivity, or Ollama model work on the target machine.

## Verify on the Arch machine

From the project root, point Aposma to the working analyzer binary if it lives outside this repository:

```bash
source .venv/bin/activate
export APOSMA_ANALYZER_BIN="$HOME/Downloads/aposma-analyzer-fix/build/aposma-analyzer"
python -m compileall -q codelens tests
python -m pytest -q
python -m codelens.cli --help
./scripts/smoke_cli.sh
```

Check Ollama only if AI assistance is desired:

```bash
ollama list
curl -sS http://127.0.0.1:11434/api/tags
```

Build the frontend:

```bash
cd frontend
npm install
npm run build
```

Then run FastAPI on port 8000 and Vite on port 5173. Open `http://127.0.0.1:5173`, review a local folder, generate documentation for it, and repeat with a public GitHub repository URL. For private repositories, set `APOSMA_GITHUB_TOKEN` in the environment before starting the backend.
