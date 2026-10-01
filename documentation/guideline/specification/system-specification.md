# Aposma System Specification

**Project:** Aposma
**Category:** Local-first code intelligence and automated code review
**Primary language:** C++ for source analysis, Python for orchestration and application services
**Target AI runtime:** Local small language model (SLM), currently designed around Qwen2.5-Coder 3B through Ollama
**Primary interface:** CLI
**Secondary integration:** Git/GitHub-oriented workflows

## 1. Problem statement

Code review requires understanding syntax, structure, data flow, dependencies, conventions, and intent. Traditional static-analysis tools are strong at deterministic checks, but their output can be fragmented or difficult to interpret. Large language models can explain code well, but a model-only reviewer can hallucinate facts, miss structural relationships, or produce claims that cannot be traced to evidence.

Aposma combines the two approaches.

The analyzer discovers structured evidence about a codebase. The evidence layer organizes and ranks that information. A local SLM then converts the evidence into explanations, review findings, and documentation.

The target experience is:

```text
Repository
   |
   v
Deterministic analysis
   |
   v
Structured evidence
   |
   v
Context construction
   |
   v
Local SLM
   |
   +----> Code review
   |
   +----> Documentation
   |
   +----> Explanations
```

## 2. Goals

### 2.1 Primary goals

- Analyze C++ source repositories using Clang/LLVM-based tooling.
- Produce structured, machine-readable findings.
- Preserve source locations and relevant context.
- Rank findings so important issues appear before low-value observations.
- Feed grounded evidence into a local SLM.
- Generate human-readable code-review explanations.
- Generate documentation from repository evidence.
- Store historical analyses so changes can be compared over time.
- Provide a usable CLI without requiring paid cloud AI APIs.

### 2.2 Secondary goals

- Support Git-aware analysis.
- Prepare a clean integration boundary for GitHub Checks.
- Make failures observable and debuggable.
- Keep the system modular enough to replace the model or analyzer independently.

## 3. Non-goals for the MVP

The following are explicitly outside the MVP unless they become necessary for a demonstrated use case:

- Building a full IDE.
- Building a general-purpose autonomous software engineer.
- Replacing a compiler or production static-analysis suite.
- Running expensive remote foundation models by default.
- Supporting every programming language.
- Fully automatic code modification without human review.
- Building a CRUD-heavy web dashboard as the primary product.

## 4. Functional requirements

### FR-01: Repository analysis

The system shall accept a local source repository and analyze supported source files.

### FR-02: Deterministic findings

The analyzer shall produce structured findings containing, where available:

- finding identifier
- category
- severity
- message
- source file
- source line and column
- symbol or declaration information
- related entities
- evidence metadata

### FR-03: Evidence construction

The system shall transform raw analyzer output into a normalized evidence representation suitable for downstream reasoning.

### FR-04: Finding ranking

The system shall rank findings according to explicit deterministic criteria before model generation.

### FR-05: AI-assisted review

The system shall optionally send evidence and controlled source context to a local SLM and produce review text.

### FR-06: AI-assisted documentation

The system shall optionally use the same grounded evidence pipeline to generate documentation for relevant code structures.

### FR-07: No-model operation

The system shall remain capable of producing deterministic analysis output when the local model is unavailable.

### FR-08: Persistence

The system shall store analyses and relevant metadata in local persistence so previous runs can be inspected.

### FR-09: CLI interface

The CLI shall expose separate commands for review, documentation, raw analysis, and history.

Current command groups:

```text
aposma review
aposma docs
aposma analyze
aposma history
```

### FR-10: Git-aware context

The system should be able to use repository history and diffs to focus analysis on changed or affected code where appropriate.

## 5. Non-functional requirements

### NFR-01: Local-first privacy

Source code should remain local by default. No remote model provider should be required for core functionality.

### NFR-02: Reproducibility

Deterministic analyzer output should be stable for the same repository state and analyzer configuration, subject to compiler/toolchain behavior.

### NFR-03: Traceability

AI-generated review statements should be traceable to evidence records whenever they assert a concrete program fact.

### NFR-04: Modularity

The model provider must be replaceable without rewriting the static-analysis subsystem.

### NFR-05: Testability

Core ranking, evidence construction, documentation generation, and model formatting should be testable without requiring an actual LLM.

### NFR-06: Failure isolation

An unavailable model must not erase or invalidate deterministic findings.

## 6. High-level architecture

```text
                 +----------------------+
                 |      Aposma CLI      |
                 +----------+-----------+
                            |
                +-----------+-----------+
                |                       |
                v                       v
       +----------------+      +----------------+
       | C++ Analyzer   |      | Git / Repo     |
       | Clang/LLVM     |      | Context        |
       +-------+--------+      +-------+--------+
               |                       |
               +----------+------------+
                          v
                 +------------------+
                 | Evidence Builder  |
                 +---------+--------+
                           |
                  +--------+--------+
                  |                 |
                  v                 v
          +---------------+  +-------------+
          | Ranking       |  | Persistence |
          +-------+-------+  +-------------+
                  |
                  v
           +-------------+
           | Model Adapter|
           | Local SLM    |
           +------+------+ 
                  |
          +-------+--------+
          |                |
          v                v
   Code Review         Documentation
```

## 7. Component responsibilities

### 7.1 C++ analyzer

Responsible for structural program inspection using Clang/LLVM.

It should focus on facts that benefit from compiler-grade understanding of the language:

- declarations
- references
- functions
- variables
- classes and types
- source locations
- AST relationships
- selected static-analysis patterns

The analyzer should not generate prose.

### 7.2 Python orchestration layer

Responsible for:

- CLI behavior
- repository discovery
- process orchestration
- evidence assembly
- ranking
- model invocation
- output formatting
- persistence

### 7.3 Evidence builder

Responsible for converting low-level findings into normalized records with enough context for reasoning.

### 7.4 Model adapter

Responsible for local SLM communication. It must not silently become the source of truth for deterministic findings.

### 7.5 Review engine

Responsible for turning evidence into structured review output.

### 7.6 Documentation engine

Responsible for turning evidence and selected source context into documentation while avoiding unsupported claims.

### 7.7 Persistence layer

Stores analysis history, metadata, and results needed for comparison or later inspection.

## 8. CLI specification

### `aposma analyze <repository>`

Produces raw deterministic analysis output, primarily for debugging and machine consumption.

### `aposma review <repository>`

Runs the review pipeline and produces ranked findings and explanations.

Expected high-level pipeline:

```text
repository -> analyze -> evidence -> rank -> optional model -> report
```

### `aposma docs <repository>`

Generates repository documentation from analyzed structures and grounded model output.

### `aposma history`

Displays previously stored analyses and metadata.

## 9. Output principles

Review findings should be structured before they are rendered as prose.

A finding should conceptually contain:

```json
{
  "id": "F001",
  "severity": "warning",
  "category": "resource-management",
  "message": "...",
  "file": "src/example.cpp",
  "line": 42,
  "column": 7,
  "evidence": ["E12", "E19"],
  "explanation": "..."
}
```

The exact schema may evolve, but the principle remains: **facts and explanations are separate fields**.

## 10. Acceptance criteria for MVP

The MVP is considered technically functional when all of the following are true:

1. The Python package installs in an isolated environment.
2. The test suite passes without a running model.
3. The Clang/LLVM analyzer builds against the supported local toolchain.
4. A known C++ example can be analyzed deterministically.
5. Raw findings can be emitted as JSON.
6. Evidence can be built from those findings.
7. Findings can be ranked deterministically.
8. The local model can be invoked optionally.
9. Model output is constrained by evidence and validated before presentation.
10. An analysis can be persisted and retrieved through the CLI.

## 11. Security and privacy requirements

- Local source code should not leave the machine by default.
- Secrets must not be placed into prompts or persisted analysis records.
- GitHub credentials, webhook secrets, and signing keys must be loaded from environment variables or secure configuration.
- Generated reports should avoid copying entire repositories unnecessarily.
- Model prompts must clearly distinguish trusted analyzer evidence from untrusted source comments or strings.

## 12. Open engineering questions

The following are intentionally unresolved until implementation evidence is available:

- The exact supported Clang/LLVM version range.
- The minimum hardware configuration for practical local inference.
- The final finding taxonomy.
- The amount of source context that should be passed to the SLM.
- The optimal persistence schema for long-term history.
- The exact GitHub Checks annotation strategy.

These should be decided from tests and measurements rather than assumptions.
