from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .analyzer import run_analyzer
from .config import Settings
from .docs import fallback_documentation, parse_documentation_response
from .evidence import build_evidence, compact_json
from .models import ReviewFinding, ReviewResult
from .ollama_client import OllamaError, is_available, review as ollama_review
from .ranking import rank
from .storage import Database


def _parse_json_output(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model did not return valid JSON: {exc}") from exc


def review_repo(repo: Path, settings: Settings, base: str | None = None, use_ai: bool = True) -> tuple[ReviewResult, dict[str, Any]]:
    analysis = run_analyzer(repo, settings)
    evidence = build_evidence(repo, analysis, settings, base)
    ranked_static = rank(analysis.findings)

    deterministic = [
        ReviewFinding(
            severity=f.severity,
            category=f.category,
            location=f"{f.file}:{f.line}",
            title=f.message.split(".")[0][:100],
            finding=f.message,
            reason=f.evidence,
            evidence=[f.evidence],
            confidence=f.confidence,
        )
        for f in ranked_static
    ]

    if not use_ai or not is_available(settings):
        return ReviewResult(
            summary=f"Aposma found {len(deterministic)} deterministic finding(s). Local SLM was not used.",
            findings=deterministic,
        ), evidence

    try:
        raw = ollama_review(settings, compact_json(evidence))
        payload = _parse_json_output(raw)
        findings = [ReviewFinding(**item) for item in payload.get("findings", [])]
        findings.sort(key=lambda x: {"HIGH": 4, "MEDIUM": 3, "LOW": 2, "INFO": 1}.get(x.severity.upper(), 1), reverse=True)
        return ReviewResult(
            summary=str(payload.get("summary", "")),
            findings=findings,
            raw_model_output=raw,
        ), evidence
    except (OllamaError, ValueError, TypeError) as exc:
        return ReviewResult(
            summary=f"Local SLM unavailable or invalid. Showing deterministic findings. Reason: {exc}",
            findings=deterministic,
        ), evidence


def docs_repo(repo: Path, settings: Settings, use_ai: bool = True) -> dict[str, Any]:
    analysis = run_analyzer(repo, settings)
    evidence = build_evidence(repo, analysis, settings)
    if use_ai and is_available(settings):
        try:
            from .ollama_client import docs as ollama_docs
            raw = ollama_docs(settings, compact_json(evidence))
            parsed = parse_documentation_response(raw)
            return {"summary": parsed.get("summary", ""), "documents": parsed.get("documents", []), "evidence": evidence}
        except Exception as exc:  # noqa: BLE001
            return {"summary": f"AI documentation failed: {exc}", "documents": fallback_documentation(analysis), "evidence": evidence}
    return {"summary": "Deterministic documentation generated from the code model.", "documents": fallback_documentation(analysis), "evidence": evidence}


def persist_review(settings: Settings, repo: Path, result: ReviewResult, evidence: dict[str, Any]) -> int:
    db = Database(settings.db_path)
    db.initialize()
    return db.save_analysis(repo, result, evidence)
