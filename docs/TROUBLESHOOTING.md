# Troubleshooting

## Analyzer not found

Build the native analyzer or point `APOSMA_ANALYZER_BIN` to the actual executable:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
export APOSMA_ANALYZER_BIN="$PWD/build/aposma-analyzer"
```

## `stddef.h` not found

This means the LibTooling process cannot locate compiler-provided headers. Confirm that the expected file exists:

```bash
gcc -print-file-name=include
clang++ -print-resource-dir
```

Then check the Python wrapper and analyzer path. The code passes detected compiler include paths to the analyzer, but the installed Clang/LLVM and GCC toolchain still must be valid and compatible with the build.

## GitHub clone fails

- Make sure the URL points to `github.com` and includes the owner and repository name.
- For private repositories, export `APOSMA_GITHUB_TOKEN` with read permission or configure Git credentials.
- Check DNS/network access and run `git ls-remote https://github.com/owner/repository.git` to test Git access.
- Existing checkouts are reused and aren't force-updated. Inspect the path displayed by Aposma and pull updates manually if needed.
- If a stale/incomplete directory occupies the workspace path, move it aside or set a different `APOSMA_WORKSPACE_DIR`.

## Documentation was generated but Ollama is unavailable

Run with `--no-ai` for deterministic Markdown. If Ollama is expected to run, check:

```bash
curl -sS http://127.0.0.1:11434/api/tags
ollama list
```

Generated deterministic docs remain available even when the model is offline.

## Dashboard reports HTTP 500 or 503

Keep the FastAPI terminal visible. A 503 generally means the native analyzer failed or was unavailable; use the specific `detail` field from the HTTP response. A 500 indicates another backend failure; the terminal traceback identifies the Python exception. The Firefox `favicon.ico`/JSON Viewer warnings are usually separate from `/api/review` or `/api/docs` request failures.

## Vite crashes with `Bus error`

A Vite/ Rollup native binary may be failing to load. Check Node first, then try Rollup import and `./node_modules/.bin/vite --version` from the `frontend` directory. The frontend package manifest includes the Rollup WebAssembly alias to avoid relying on Rollup's native binary on affected systems. If dependency resolution still fails, remove only `frontend/node_modules` and reinstall from `frontend/package.json`; keep the source files and package lock.
