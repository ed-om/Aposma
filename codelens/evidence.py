from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import Settings
from .git import changed_files, diff, head, is_repo
from .models import CodeAnalysis


def _read_changed_sources(repo: Path, files: list[str], limit: int) -> dict[str, str]:
    sources: dict[str, str] = {}
    remaining = limit
    for rel in files:
        if remaining <= 0:
            break
        path = repo / rel
        if not path.is_file() or path.suffix not in {".cpp", ".cc", ".cxx", ".h", ".hpp", ".hh"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        snippet = text[:remaining]
        sources[rel] = snippet
        remaining -= len(snippet)
    return sources


def build_evidence(repo: Path, analysis: CodeAnalysis, settings: Settings, base: str | None = None) -> dict[str, Any]:
    git_meta: dict[str, Any] = {"is_repository": is_repo(repo)}
    diff_text = ""
    changed: list[str] = []
    if git_meta["is_repository"]:
        try:
            git_meta["head"] = head(repo)
            changed = changed_files(repo, base)
            diff_text = diff(repo, base, settings.max_diff_chars)
        except Exception as exc:  # noqa: BLE001
            git_meta["error"] = str(exc)

    sources = _read_changed_sources(repo, changed, settings.max_source_chars)

    return {
        "project": repo.name,
        "language": "C++",
        "git": git_meta,
        "changed_files": changed,
        "diff": diff_text,
        "sources": sources,
        "program": {
            "functions": analysis.functions,
            "records": analysis.records,
            "edges": analysis.edges,
        },
        "static_findings": [
            {
                "id": f.id,
                "category": f.category,
                "severity": f.severity,
                "message": f.message,
                "file": f.file,
                "line": f.line,
                "confidence": f.confidence,
                "evidence": f.evidence,
            }
            for f in analysis.findings
        ],
    }


def compact_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
