# Aposma Analysis Specification

## 1. Purpose

This document defines the conceptual contract for deterministic findings produced by Aposma's source analyzer.

## 2. Finding model

A finding represents an observation produced by a deterministic analyzer rule.

Conceptual fields:

```text
id
rule
category
severity
confidence
message
file
line
column
symbol
related_symbols
evidence
```

Fields may be optional when the underlying compiler data is unavailable.

## 3. Rule identity

Every analysis rule should have a stable identifier.

Example format:

```text
APOSMA001
APOSMA002
APOSMA003
```

The numeric identifier should not be reused for an unrelated rule.

## 4. Severity

Severity is a classification, not an absolute guarantee of impact.

Suggested levels:

```text
info
warning
error
critical
```

Rules should document why a particular level is appropriate.

## 5. Confidence

Confidence describes how strongly the analyzer can justify the finding.

It is distinct from severity.

A high-severity finding with weak evidence should not be silently converted into a high-confidence claim.

## 6. Source location

Source locations should use compiler-provided locations where possible.

A location record should conceptually contain:

```json
{
  "file": "src/example.cpp",
  "line": 42,
  "column": 7
}
```

## 7. Evidence references

Evidence should make the reasoning chain inspectable.

Conceptually:

```text
Finding F12
   |
   +--> Evidence E21: declaration
   +--> Evidence E22: reference
   +--> Evidence E23: rule trigger
```

## 8. Determinism

Given the same source revision, toolchain, and analyzer configuration, the analyzer should aim to produce equivalent findings.

If toolchain-dependent behavior exists, the analysis metadata should record the relevant version information.

## 9. Evidence quality

Evidence should be:

- relevant
- concise
- source-located
- sufficient to justify the finding
- free from unnecessary repository content

## 10. False positives

False positives are expected in static analysis. The system should make them inspectable rather than hide them.

A future evaluation dataset should track:

```text
true positive
false positive
false negative
true negative
```

This supports measurable analyzer improvement.

## 11. Analyzer output versus AI explanation

Analyzer:

```text
There is a finding at src/foo.cpp:42.
Rule APOSMA001 triggered because condition X was observed.
```

AI explanation:

```text
This may lead to ... because ...
```

The second statement is interpretation and should remain subordinate to the first.
