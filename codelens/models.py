from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Finding:
    id: str
    category: str
    severity: str
    message: str
    file: str
    line: int
    confidence: float
    evidence: str
    source: str = "static"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Finding":
        return cls(
            id=str(data.get("id", "unknown")),
            category=str(data.get("category", "unknown")),
            severity=str(data.get("severity", "LOW")).upper(),
            message=str(data.get("message", "")),
            file=str(data.get("file", "")),
            line=int(data.get("line", 1) or 1),
            confidence=float(data.get("confidence", 0.0) or 0.0),
            evidence=str(data.get("evidence", "")),
            source=str(data.get("source", "static")),
        )


@dataclass
class ReviewFinding:
    severity: str
    category: str
    location: str
    title: str
    finding: str
    reason: str
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class ReviewResult:
    summary: str
    findings: list[ReviewFinding]
    raw_model_output: str = ""


@dataclass
class CodeAnalysis:
    functions: list[dict[str, Any]]
    records: list[dict[str, Any]]
    findings: list[Finding]
    edges: list[dict[str, Any]]
    raw: dict[str, Any]
