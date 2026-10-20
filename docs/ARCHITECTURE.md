# Aposma Architecture

## Core rule

The local SLM does not establish program facts. The analyzer establishes facts; the SLM interprets them.

```text
C++
 ↓
Clang AST
 ↓
Code Knowledge Model
 ↓
Static Analysis + Git
 ↓
Evidence Package
 ↓
Qwen2.5-Coder-3B-Instruct via Ollama
 ↓
Review / Documentation
```

## Boundaries

- `analyzer/` is deterministic C++ analysis.
- `codelens/` is orchestration and persistence.
- Ollama is a replaceable model runtime.
- GitHub integration is optional until the local workflow is stable.

## Zero-budget design

No paid API is required. The project is usable locally.
