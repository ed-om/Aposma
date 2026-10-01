# Aposma Development Guidelines

## 1. General rule

Implement the smallest technically sound change that preserves the architecture.

Do not introduce a framework or dependency simply because it makes a short piece of code easier.

## 2. Source-of-truth rule

When a program fact can be determined by the compiler, AST, parser, or deterministic analysis, do not use the SLM as the primary source of that fact.

Bad pattern:

```text
source code -> SLM -> "I think this variable is local"
```

Preferred pattern:

```text
source code -> Clang AST -> local variable evidence -> SLM explanation
```

## 3. C++ analyzer guidelines

- Prefer Clang AST matchers and compiler APIs over brittle text matching.
- Preserve source locations whenever possible.
- Keep analyzer rules independently understandable.
- Avoid embedding prose-generation logic in the analyzer.
- Keep output serialization deterministic.
- Treat the analyzer as a library/tool boundary, not as a general application layer.
- Document Clang/LLVM version assumptions.

## 4. Python guidelines

- Keep orchestration separate from business logic.
- Use typed data structures for boundaries between subsystems.
- Validate external input.
- Avoid global mutable state.
- Make failures explicit.
- Keep CLI rendering separate from core analysis functions.

## 5. AI/SLM guidelines

### 5.1 Grounding

Every concrete review claim should have corresponding evidence where practical.

### 5.2 No fabricated locations

The model must not invent line numbers, files, symbols, or function names.

### 5.3 Uncertainty

When evidence is incomplete, output must say so instead of manufacturing certainty.

### 5.4 Structured output

Prefer a schema that can be validated before presentation.

### 5.5 Prompt design

Prompts should define:

- role
- trusted evidence
- relevant source context
- prohibited behavior
- required output schema

### 5.6 Model independence

The model adapter should be replaceable. Do not hardcode Qwen-specific behavior throughout the application.

## 6. Testing guidelines

At minimum, test:

- evidence normalization
- ranking
- documentation formatting
- malformed input handling
- model-output parsing
- CLI command behavior
- analyzer fixtures

Tests that require a local SLM should be separate from deterministic unit tests.

## 7. Example-driven analysis

Keep small C++ fixtures for known cases:

```text
examples/
  sample_cpp/
    ...
```

Each fixture should have an intended analysis outcome so changes to the analyzer can be detected.

## 8. Error handling

Errors should communicate:

1. what failed
2. which subsystem failed
3. whether the failure is recoverable
4. what output, if any, remains valid

Avoid broad exception swallowing.

## 9. Logging

Logs should help answer:

- which repository was analyzed?
- which analyzer configuration was used?
- how many findings were generated?
- whether model inference was attempted?
- whether model output passed validation?

Do not log source secrets or credentials.

## 10. Git guidelines

Use focused commits.

Recommended commit categories:

```text
feat: new capability
fix: bug correction
refactor: structural change without intended behavior change
test: test-only change
docs: documentation change
build: build/toolchain change
```

A commit should not mix unrelated architecture, formatting, and feature changes unless there is a strong reason.

## 11. Pull request/change checklist

Before merging a meaningful change:

- [ ] Tests pass.
- [ ] New behavior has a test or fixture where practical.
- [ ] Documentation matches actual behavior.
- [ ] No unsupported AI claims were introduced.
- [ ] Error paths were considered.
- [ ] No secrets were committed.
- [ ] Build/toolchain assumptions are documented.

## 12. Documentation rule

Documentation must distinguish:

- implemented behavior
- experimental behavior
- planned behavior

Never describe an architecture diagram as evidence that an implementation already exists.
