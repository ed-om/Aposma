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
    documents = fallback_documentation(analysis, repo)
    summary = "Generated indexed Markdown documentation from the repository's C++ code structure."
    ai_used = False
    warning = None

    if use_ai and is_available(settings):
        try:
            from .ollama_client import docs as ollama_docs

            raw = ollama_docs(settings, compact_json(evidence))
            parsed = parse_documentation_response(raw)
            ai_documents = parsed.get("documents", [])
            if not isinstance(ai_documents, list):
                raise ValueError("Documentation response field 'documents' must be a list")
            if not any(
                isinstance(item, dict) and str(item.get("name") or "").strip() and str(item.get("markdown") or "").strip()
                for item in ai_documents
            ):
                raise ValueError("Documentation response contained no usable Markdown pages")
            documents = _merge_ai_documentation(documents, ai_documents)
            summary = str(parsed.get("summary") or summary)
            ai_used = True
        except Exception as exc:  # noqa: BLE001
            warning = f"AI documentation was unavailable; deterministic Markdown was generated instead ({exc})."
    elif use_ai:
        warning = "Ollama model is unavailable; deterministic Markdown was generated instead."

    # Refresh the index after AI notes have been incorporated.
    from .docs import _index_markdown
    for document in documents:
        if document.get("path") == "index.md":
            document["markdown"] = _index_markdown(repo.name, documents)
            break

    return {
        "summary": summary,
        "documents": documents,
        "evidence": evidence,
        "ai_used": ai_used,
        "warning": warning,
    }


def _merge_ai_documentation(
    deterministic: list[dict[str, str]], ai_documents: list[Any]
) -> list[dict[str, str]]:
    """Attach model-written notes to matched deterministic pages, keeping facts and links."""
    result = [dict(item) for item in deterministic]
    by_identity: dict[tuple[str, str], dict[str, str]] = {}
    for item in result:
        identity = (item.get("kind", "").lower(), item.get("name", "").strip().casefold())
        by_identity[identity] = item

    for index, item in enumerate(ai_documents):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        markdown = str(item.get("markdown") or "").strip()
        if not name or not markdown:
            continue
        kind = str(item.get("kind") or "notes").strip().lower()
        if kind in {"type", "record", "struct"}:
            kind = "class"
        if kind not in {"function", "class"}:
            kind = "ai-notes"
        target = by_identity.get((kind, name.casefold()))
        if target is not None:
            target["markdown"] = target["markdown"].rstrip() + "\n\n## AI-assisted notes\n\n" + markdown + "\n"
            continue
        # Unexpected names from the model are kept separately instead of being
        # silently dropped or allowed to choose an arbitrary filesystem path.
        from .docs import _slug
        import hashlib

        suffix = hashlib.sha1(f"{name}:{index}".encode()).hexdigest()[:8]
        safe_name = _slug(name)
        path = f"ai-notes/{safe_name}-{suffix}.md"
        result.append({
            "kind": "ai-notes",
            "name": name,
            "path": path,
            "markdown": f"# {name}\n\n{markdown}\n",
        })
        by_identity[("ai-notes", name.casefold())] = result[-1]

    return result


def persist_review(settings: Settings, repo: Path, result: ReviewResult, evidence: dict[str, Any]) -> int:
    db = Database(settings.db_path)
    db.initialize()
    return db.save_analysis(repo, result, evidence)
