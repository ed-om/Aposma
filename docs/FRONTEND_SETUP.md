# Aposma React dashboard setup

## 1. Install dependencies

From the Aposma repository root:

```bash
python -m pip install -e '.[dev,server]'
cd frontend
npm install
```

The frontend package manifest aliases Rollup to its WebAssembly implementation for systems affected by Rollup's native binary crashing with `Bus error`. The `.npmrc` retries slow registry requests. If npm reports that the `esbuild` install script was blocked, run `npm install-scripts approve esbuild` and then `npm rebuild esbuild` from `frontend/`.

## 2. Start the backend

Open terminal 1 in the repository root. Point the wrapper at the native analyzer binary you already built if it is stored in a separate worktree:

```bash
source .venv/bin/activate
export APOSMA_ANALYZER_BIN="$HOME/Downloads/aposma-analyzer-fix/build/aposma-analyzer"
# Optional: access private GitHub repositories
# export APOSMA_GITHUB_TOKEN='YOUR_TOKEN'
python -m uvicorn codelens.server:app --host 127.0.0.1 --port 8000 --reload
```

Keep the API bound to loopback (`127.0.0.1`). It accepts local paths and GitHub URLs and is intended for local development, not direct public exposure.

## 3. Start React

Open terminal 2:

```bash
cd /path/to/aposma/frontend
npm run dev
```

Open `http://127.0.0.1:5173`. From Overview, enter a local repository path, `examples/sample_cpp`, a full GitHub repository URL such as `https://github.com/owner/repository`, or the shorthand `owner/repository`.

## 4. Verify services

Visit `http://127.0.0.1:8000/api/status`. The analyzer is ready only when the configured binary exists and is executable. The Local SLM is ready only when Ollama responds and the configured model is installed.

Review runs are stored in SQLite. Documentation output is written to the selected repository's `.aposma/docs/` directory. A GitHub checkout remains on disk under `~/.local/share/aposma/workspaces/<owner>/<repository>/` unless `APOSMA_WORKSPACE_DIR` is changed.
