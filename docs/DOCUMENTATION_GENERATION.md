# Markdown documentation generation

Aposma generates Markdown pages from the structured model emitted by its C++ analyzer. The implementation is in `codelens/docs.py`; the orchestration lives in `codelens/review.py`; CLI and HTTP entry points are in `codelens/cli.py` and `codelens/server.py`.

## Run it

```bash
python -m codelens.cli docs examples/sample_cpp --no-ai
```

For a remote repository:

```bash
python -m codelens.cli docs https://github.com/owner/repository --no-ai
```

The default output directory is `.aposma/docs/` at the repository root. `--output-dir` changes that destination for CLI runs.

## Files generated

| File | Contents |
| --- | --- |
| `index.md` | Navigable index of generated pages |
| `architecture.md` | Counts, call-graph edges, source locations, and analysis limitations |
| `findings.md` | Static findings, locations, evidence, severity, and confidence |
| `functions/<name>.md` | Return type, source, line span, parameter count, calls, and pointer observations |
| `types/<name>.md` | Record/class/struct declaration location and functions in the same source file |
| `ai-notes/<name>.md` | Extra AI notes that do not match an extracted function or class |

The generator writes only `.md` pages under the documentation output directory. It uses `.aposma-manifest.json` to remember which generated Markdown pages it created on the previous run, so stale generated pages can be removed without clearing unrelated files.

## AI-assisted documentation

If Ollama is available and the selected model is installed, Aposma asks the model for notes grounded in the evidence package. Notes for a known function or class are appended to that deterministic page under `AI-assisted notes`. Notes for unrecognized names are written to `ai-notes/`. If Ollama is unavailable or returns malformed output, the deterministic pages are still generated and the API returns a warning.

## Trust boundaries

Generated pages describe analyzer output and may include AI interpretation. The static report is not a proof of correctness, a complete call graph, a security audit, or a runtime trace. Check each page against source code before relying on it.
