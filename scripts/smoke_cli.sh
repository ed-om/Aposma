#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SOURCE="${1:-examples/sample_cpp}"
if [[ ! -x "${APOSMA_ANALYZER_BIN:-$ROOT/build/aposma-analyzer}" ]]; then
  echo "Aposma analyzer binary was not found. Set APOSMA_ANALYZER_BIN or build ./build/aposma-analyzer." >&2
  exit 2
fi

export APOSMA_ANALYZER_BIN="${APOSMA_ANALYZER_BIN:-$ROOT/build/aposma-analyzer}"
python -m codelens.cli review "$SOURCE" --no-ai
python -m codelens.cli docs "$SOURCE" --no-ai

if [[ "$SOURCE" = /* || -d "$SOURCE" ]]; then
  REPO_PATH="$(python -c 'import sys; from pathlib import Path; print(Path(sys.argv[1]).expanduser().resolve())' "$SOURCE")"
else
  echo "Review and docs commands completed for source: $SOURCE"
  echo "For remote-source output, use the workspace path printed by the commands above."
  exit 0
fi

DOC_DIR="$REPO_PATH/.aposma/docs"
if [[ ! -f "$DOC_DIR/index.md" ]]; then
  echo "Expected Markdown index was not generated: $DOC_DIR/index.md" >&2
  exit 1
fi
if ! find "$DOC_DIR" -type f -name '*.md' -print -quit | grep -q .; then
  echo "No Markdown files were generated under $DOC_DIR" >&2
  exit 1
fi
printf '\nCLI smoke test passed. Markdown output: %s\n' "$DOC_DIR"
