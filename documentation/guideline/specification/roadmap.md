# Aposma Roadmap

## Phase 1 — Deterministic foundation

**Goal:** make analyzer-driven evidence reliable.

- [x] Python package installation
- [x] CLI command structure
- [x] Initial deterministic unit tests
- [x] LLVM/Clang discovery through CMake
- [ ] Finish Clang/LLVM native linking on the target toolchain
- [ ] Build analyzer successfully
- [ ] Run analyzer against the example C++ repository
- [ ] Confirm stable JSON output

## Phase 2 — Evidence pipeline

- [ ] Normalize analyzer output
- [ ] Define versioned evidence schema
- [ ] Add evidence IDs
- [ ] Add source-location validation
- [ ] Improve deterministic ranking
- [ ] Add fixture-based analyzer tests

## Phase 3 — Local SLM

- [ ] Integrate local model runtime
- [ ] Add model adapter interface
- [ ] Add grounded review prompt
- [ ] Add structured model output
- [ ] Validate evidence references
- [ ] Add no-model fallback

## Phase 4 — Documentation generation

- [ ] Build documentation context selection
- [ ] Generate symbol/function/class summaries
- [ ] Generate repository-level documentation
- [ ] Validate generated documentation against evidence

## Phase 5 — History and Git

- [ ] Persist analysis metadata
- [ ] Store findings by repository revision
- [ ] Compare analyses across commits
- [ ] Focus review on changed code where appropriate

## Phase 6 — GitHub integration

- [ ] GitHub App configuration
- [ ] Webhook ingestion
- [ ] Revision checkout
- [ ] Aposma review execution
- [ ] Check Run publishing
- [ ] Line annotations

## Phase 7 — Evaluation

Build a repeatable evaluation corpus containing known bugs and review cases.

Measure separately:

```text
Analyzer precision / recall
Evidence quality
Ranking quality
Model grounding
Model usefulness
End-to-end review usefulness
```

## MVP boundary

The MVP should stop once the deterministic analyzer, evidence pipeline, local SLM integration, CLI, and tests form a coherent end-to-end path.

Features such as a polished web UI, large multi-language support, autonomous patch generation, and complex distributed execution should not delay the core research/engineering objective.

## Engineering principle

Every phase should produce a working intermediate system. Avoid building a large number of disconnected components before the end-to-end path works.
