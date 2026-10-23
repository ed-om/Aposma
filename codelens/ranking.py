from __future__ import annotations

from collections.abc import Iterable

from .models import Finding, ReviewFinding

_SEVERITY = {"HIGH": 4, "MEDIUM": 3, "LOW": 2, "INFO": 1}


def score(finding: Finding) -> float:
    severity = _SEVERITY.get(finding.severity.upper(), 1)
    return severity * 10 + finding.confidence * 5


def rank(findings: Iterable[Finding]) -> list[Finding]:
    return sorted(findings, key=score, reverse=True)


def rank_ai(findings: Iterable[ReviewFinding]) -> list[ReviewFinding]:
    return sorted(
        findings,
        key=lambda f: _SEVERITY.get(f.severity.upper(), 1) * 10 + float(f.confidence),
        reverse=True,
    )
