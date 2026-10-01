# Aposma Documentation, Guidelines, and Specification

This directory defines the technical direction, implementation rules, and system specification for **Aposma**, a local-first code intelligence tool.

Aposma is designed around one central principle:

> **Deterministic program analysis produces evidence; the language model explains that evidence.**

The language model is not the source of truth for program facts. Structural facts such as declarations, references, control-flow-related findings, source locations, symbols, and other analyzer outputs must come from deterministic tooling whenever practical. The local language model then uses that evidence to produce human-readable review comments and documentation.

## Documents

| Document | Purpose |
|---|---|
| [`system-specification.md`](system-specification.md) | Defines the problem, goals, scope, requirements, architecture, interfaces, and acceptance criteria. |
| [`architecture.md`](architecture.md) | Explains the internal architecture and data flow between the C++ analyzer, Python orchestration layer, evidence builder, model layer, and storage. |
| [`development-guidelines.md`](development-guidelines.md) | Rules for implementation, testing, Git workflow, error handling, determinism, and AI integration. |
| [`analysis-specification.md`](analysis-specification.md) | Defines the contract for static-analysis findings and evidence records. |
| [`model-specification.md`](model-specification.md) | Defines how the local SLM is used, what it may infer, grounding rules, and output constraints. |
| [`roadmap.md`](roadmap.md) | Defines the implementation phases and what belongs to MVP versus later work. |

## Status convention

This documentation uses three statuses:

- **Implemented** — behavior already present in the repository and validated by tests or direct execution.
- **In progress** — behavior currently being integrated or debugged.
- **Planned** — target behavior that is part of the design but is not yet complete.

Documentation must never describe planned behavior as already implemented.

## Core design principles

1. **Evidence before explanation.** The model should receive structured program evidence instead of an arbitrary source-code prompt whenever possible.
2. **Local-first.** The core workflow must be usable without sending source code to a remote AI service.
3. **Deterministic foundation.** Reproducible analysis is preferred over model-generated guesses for program facts.
4. **Explainability.** A user should be able to trace an AI-generated statement back to analyzer evidence.
5. **Small, composable components.** The analyzer, evidence layer, model adapter, review engine, documentation generator, and persistence layer should have clear boundaries.
6. **Fail safely.** If AI inference is unavailable, deterministic analysis should still be useful.
7. **Technology learning value.** The implementation should expose how the major systems work instead of hiding all behavior behind a framework.

## Intended repository relationship

This directory is documentation, not executable source code. Changes to architecture or requirements should be reflected here before implementation decisions become difficult to reverse.
