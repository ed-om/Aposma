# Command-line reference

The CLI accepts local repository directories, full GitHub repository URLs, and `owner/repository` shorthand.

## `review`

```bash
python -m codelens.cli review <path-or-github-source> [--base REF] [--no-ai]
```

Runs the native analyzer, assembles repository evidence, optionally requests local Ollama interpretation, and saves the run to SQLite. `--base` provides a Git ref to compare against when it is available in the checkout. `--no-ai` uses deterministic findings only.

## `docs`

```bash
python -m codelens.cli docs <path-or-github-source> [--no-ai] [--output-dir DIRECTORY]
```

Creates `index.md`, `architecture.md`, `findings.md`, and function/type pages. `--output-dir` overrides the default `<repo>/.aposma/docs/` path.

## `analyze`

```bash
python -m codelens.cli analyze <path-or-github-source>
```

Prints the raw structured JSON emitted by the C++ analyzer.

## `history`

```bash
python -m codelens.cli history [--limit N]
```

Prints recent reviews stored in the SQLite database configured by `APOSMA_DB`.

## Settings

- `APOSMA_ANALYZER_BIN`: absolute path to the built `aposma-analyzer` executable.
- `APOSMA_OLLAMA_URL`: local Ollama API base URL, default `http://127.0.0.1:11434`.
- `APOSMA_OLLAMA_MODEL`: model name, default `qwen2.5-coder:3b`.
- `APOSMA_OLLAMA_TIMEOUT`: model request timeout in seconds.
- `APOSMA_DB`: SQLite path, default `.data/aposma.sqlite3`.
- `APOSMA_WORKSPACE_DIR`: persistent root directory for GitHub checkouts.
- `APOSMA_GITHUB_TOKEN`: optional token for private GitHub repositories.
