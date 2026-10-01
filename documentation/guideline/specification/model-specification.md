# Aposma Model Specification

## 1. Purpose

The SLM is an explanation and synthesis layer over deterministic code evidence.

It is not the compiler, parser, or authoritative static analyzer.

## 2. Model role

The model may:

- explain a deterministic finding
- summarize relevant code structure
- describe likely consequences of a finding
- suggest a remediation approach
- generate documentation grounded in evidence
- connect multiple supplied evidence records into a readable explanation

The model must not be treated as authoritative for facts that the analyzer can determine directly.

## 3. Input contract

Model input should contain:

```text
Task
Trusted evidence
Relevant source context
Repository/change context
Output schema
Constraints
```

## 4. Trust boundaries

### Trusted

- analyzer-produced evidence
- validated repository metadata
- explicitly selected source context

### Untrusted or context-only

- comments in source files
- string literals
- generated text
- previous model output
- external text embedded in source

Source comments should not be allowed to override system instructions or evidence.

## 5. Output contract

A review response should conceptually contain:

```json
{
  "finding_id": "F001",
  "summary": "...",
  "explanation": "...",
  "impact": "...",
  "suggestion": "...",
  "evidence_ids": ["E01", "E02"],
  "confidence": "high"
}
```

The exact schema can evolve, but evidence references should remain available.

## 6. Hallucination controls

The model should be instructed to:

- never invent file names
- never invent line numbers
- never invent compiler findings
- avoid claiming execution behavior that was not observed
- distinguish likely impact from proven behavior
- say when evidence is insufficient

## 7. Validation

Model output should be validated before reaching the user.

Validation should check at minimum:

- schema correctness
- referenced evidence IDs
- valid severity/confidence values
- source-location consistency where locations are supplied

## 8. Model failure behavior

If the model is unavailable:

```text
review = deterministic findings + clear "AI unavailable" status
```

If the model returns malformed output:

```text
raw response -> parser -> validation -> reject or controlled recovery
```

A malformed response must not silently become trusted data.

## 9. Local inference

The intended MVP uses a local coding-oriented SLM through a local runtime such as Ollama.

The model name, runtime, and prompt template should remain configuration rather than being hardcoded into every component.

## 10. Evaluation

Model quality should be evaluated separately from analyzer quality.

Useful evaluation dimensions:

- factual grounding
- evidence coverage
- hallucination rate
- explanation usefulness
- schema validity
- consistency across repeated runs

A model can produce fluent text while still failing the grounding requirement.
