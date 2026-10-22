# Aposma Architecture

## Core rule

The local SLM does not establish program facts. The native analyzer establishes structural facts and deterministic findings; the SLM interprets the structured evidence when enabled.

```text
Local folder / GitHub repository URL
                ↓
        Local repository workspace
                ↓
            Clang AST
                ↓
       Code Knowledge Model
                ↓
       Static findings + Git context
                ↓
          Evidence package
            ↙          ↘
   Deterministic pages  optional Ollama notes
            ↘          ↙
       Review / Markdown documentation
                ↓
       SQLite history / .aposma/docs/
```

## Boundaries

- `analyzer/` is deterministic C++ analysis implemented with Clang LibTooling.
- `codelens/analyzer.py` finds the native executable and supplies detected compiler built-in include paths.
- `codelens/repositories.py` resolves local source paths or clones GitHub repositories into persistent local workspaces.
- `codelens/evidence.py` builds compact evidence from the code model and optional Git diff context.
- `codelens/review.py` coordinates review, documentation, and deterministic fallback behavior.
- `codelens/docs.py` creates the Markdown file tree and safely cleans up stale pages recorded in its manifest.
- `codelens/server.py` exposes the local FastAPI API used by React.
- `codelens/github.py` contains the optional GitHub App pull-request/check-run integration.
- `frontend/` is the React/Vite dashboard.

## Privacy and limitations

Repository clone, analysis, and Markdown writes occur locally. If enabled, the code evidence is submitted to the locally configured Ollama endpoint. Keep the FastAPI server bound to loopback. The current native analysis is C++-focused and does not provide a complete program proof.
