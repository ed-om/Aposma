from __future__ import annotations

import json
from pathlib import Path
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


def parse_documentation_response(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


def fallback_documentation(analysis: Any) -> list[dict[str, str]]:
    documents: list[dict[str, str]] = []
    for fn in analysis.functions:
        deps = "\n".join(f"- `{x}`" for x in fn.get("calls", [])) or "- None detected"
        markdown = (
            f"## `{fn.get('qualified_name', fn.get('name', 'unknown'))}`\n\n"
            f"**Return type:** `{fn.get('return_type', 'unknown')}`\n\n"
            f"**Source:** `{fn.get('file', '')}:{fn.get('line', '')}`\n\n"
            f"**Parameters:** {fn.get('parameter_count', 0)}\n\n"
            f"### Direct calls\n{deps}\n"
        )
        documents.append({"kind": "function", "name": fn.get("qualified_name", fn.get("name", "unknown")), "markdown": markdown})

    for record in analysis.records:
        markdown = (
            f"## `{record.get('qualified_name', record.get('name', 'unknown'))}`\n\n"
            f"C++ record declared in `{record.get('file', '')}:{record.get('line', '')}`.\n"
        )
        documents.append({"kind": "class", "name": record.get("qualified_name", record.get("name", "unknown")), "markdown": markdown})
    return documents


def write_documents(repo: Path, documents: list[dict[str, str]], output_dir: Path | None = None) -> list[Path]:
    out = output_dir or (repo / ".aposma" / "docs")
    out.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index, document in enumerate(documents):
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in document.get("name", f"doc-{index}"))
        path = out / f"{index:03d}-{safe}.md"
        path.write_text(document.get("markdown", ""), encoding="utf-8")
        paths.append(path)
    return paths
        text = re.sub(r"^```(?:json)?\s*", "", text, count=1, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text, count=1)
    result = json.loads(text)
    if not isinstance(result, dict):
        raise ValueError("Documentation model response must be a JSON object")
    return result


def _slug(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    if not normalized:
        normalized = "item"
    if len(normalized) > 70:
        digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]
        normalized = f"{normalized[:60].rstrip('-')}-{digest}"
    return normalized


def _source_path(repo: Path | None, raw: Any) -> str:
    value = str(raw or "unknown")
    if repo is None:
        return value
    try:
        candidate = Path(value)
        if candidate.is_absolute():
            return candidate.resolve().relative_to(repo.resolve()).as_posix()
    except (OSError, ValueError):
        pass
    return value.replace("\\", "/")


def _document(kind: str, name: str, path: str, markdown: str) -> dict[str, str]:
    return {"kind": kind, "name": name, "path": path, "markdown": markdown.rstrip() + "\n"}


def fallback_documentation(analysis: Any, repo: Path | None = None) -> list[dict[str, str]]:
    """Build a useful deterministic Markdown reference without requiring Ollama."""
    functions = list(getattr(analysis, "functions", []) or [])
    records = list(getattr(analysis, "records", []) or [])
    findings = list(getattr(analysis, "findings", []) or [])
    edges = list(getattr(analysis, "edges", []) or [])
    project_name = repo.name if repo else "Codebase"
    docs: list[dict[str, str]] = []
    function_docs: list[tuple[str, str]] = []
    type_docs: list[tuple[str, str]] = []

    seen_paths: set[str] = set()
    for fn in functions:
        name = str(fn.get("qualified_name") or fn.get("name") or "unknown")
        file_path = _source_path(repo, fn.get("file", "unknown"))
        line = fn.get("line", "?")
        end_line = fn.get("end_line")
        source_label = f"`{file_path}:{line}`" + (f"–`{end_line}`" if end_line else "")
        calls = [str(item) for item in (fn.get("calls") or [])]
        pointers = [str(item) for item in (fn.get("pointer_variables") or [])]
        pointer_uses = [str(item) for item in (fn.get("pointer_uses") or [])]
        path = f"functions/{_slug(name)}.md"
        if path in seen_paths:
            suffix = hashlib.sha1(f"{name}:{file_path}:{line}".encode()).hexdigest()[:8]
            path = f"functions/{_slug(name)}-{suffix}.md"
        seen_paths.add(path)
        markdown = (
            f"# `{name}`\n\n"
            f"**Source:** {source_label}  \n"
            f"**Return type:** `{fn.get('return_type', 'unknown')}`  \n"
            f"**Parameters detected:** {fn.get('parameter_count', 0)}  \n"
            f"**Control-flow constructs detected:** {fn.get('control_count', 0)}\n\n"
            "## Direct calls\n\n"
            + ("\n".join(f"- `{call}`" for call in calls) if calls else "- No direct calls were recorded by the analyzer.")
            + "\n\n## Pointer-related observations\n\n"
            + ("**Pointer variables:** " + ", ".join(f"`{item}`" for item in pointers) + "\n\n" if pointers else "No pointer variables were recorded for this function.\n\n")
            + ("**Pointer uses:**\n\n" + "\n".join(f"- {item}" for item in pointer_uses) if pointer_uses else "No pointer-use observations were recorded.")
            + "\n\n> Generated from the analyzer's structural output. Parameter names and runtime behavior are not inferred when they are unavailable.\n"
        )
        docs.append(_document("function", name, path, markdown))
        function_docs.append((name, path))

    for record in records:
        name = str(record.get("qualified_name") or record.get("name") or "unknown")
        file_path = _source_path(repo, record.get("file", "unknown"))
        line = record.get("line", "?")
        path = f"types/{_slug(name)}.md"
        if path in seen_paths:
            suffix = hashlib.sha1(f"{name}:{file_path}:{line}".encode()).hexdigest()[:8]
            path = f"types/{_slug(name)}-{suffix}.md"
        seen_paths.add(path)
        related_functions = [
            (str(fn.get("qualified_name") or fn.get("name") or "unknown"), _source_path(repo, fn.get("file", "unknown")))
            for fn in functions
            if _source_path(repo, fn.get("file", "unknown")) == file_path
        ]
        related = "\n".join(f"- `{fn_name}`" for fn_name, _ in related_functions) or "- No functions from the same source file were associated by the analyzer."
        markdown = (
            f"# `{name}`\n\n"
            f"**Kind:** C++ record / class / struct  \n"
            f"**Source:** `{file_path}:{line}`\n\n"
            "## Related functions in the same source file\n\n"
            f"{related}\n\n"
            "> The analyzer records the declaration location; member layout and inheritance details are not currently extracted.\n"
        )
        docs.append(_document("class", name, path, markdown))
        type_docs.append((name, path))

    architecture_lines = [
        f"# Architecture and code structure — {project_name}",
        "",
        "This report is generated from the deterministic C++ analyzer output. It documents observed structure, not a complete proof of program behavior.",
        "",
        "## Overview",
        "",
        f"- Functions discovered: **{len(functions)}**",
        f"- C++ records discovered: **{len(records)}**",
        f"- Call-graph edges: **{len(edges)}**",
        f"- Static findings: **{len(findings)}**",
        "",
        "## Call graph edges",
        "",
    ]
    if edges:
        for edge in edges[:500]:
            caller = edge.get("caller") or edge.get("from") or edge.get("source") or "unknown"
            callee = edge.get("callee") or edge.get("to") or edge.get("target") or "unknown"
            architecture_lines.append(f"- `{caller}` → `{callee}`")
        if len(edges) > 500:
            architecture_lines.extend(["", f"> Only the first 500 of {len(edges)} edges are listed."])
    else:
        architecture_lines.append("No call-graph edges were emitted by the analyzer.")
    architecture_lines.extend([
        "",
        "## Source locations",
        "",
    ])
    locations = sorted({
        _source_path(repo, item.get("file", "unknown"))
        for item in [*functions, *records]
        if item.get("file")
    })
    architecture_lines.extend([f"- `{location}`" for location in locations] or ["No source locations were recorded."])
    architecture_lines.extend([
        "",
        "## Limitations",
        "",
        "- This documentation is based on the analyzer's current C++ AST extraction and static rules.",
        "- It does not run the program or establish runtime behavior.",
        "- AI-assisted notes, when present, are appended separately and should be checked against the source.",
    ])
    docs.append(_document("architecture", "Architecture", "architecture.md", "\n".join(architecture_lines)))

    findings_lines = [f"# Static analysis findings — {project_name}", ""]
    if not findings:
        findings_lines.extend([
            "The analyzer did not emit any static findings for this run.",
            "",
            "> This is not a guarantee that the code is free of defects; it reflects only the rules currently implemented by Aposma.",
        ])
    else:
        findings_lines.extend([
            f"Aposma emitted **{len(findings)}** static finding(s). Review each finding in its source context.",
            "",
        ])
        for index, finding in enumerate(findings, 1):
            item = finding if isinstance(finding, dict) else {
                "severity": getattr(finding, "severity", "LOW"),
                "category": getattr(finding, "category", "unknown"),
                "message": getattr(finding, "message", ""),
                "file": getattr(finding, "file", "unknown"),
                "line": getattr(finding, "line", "?"),
                "evidence": getattr(finding, "evidence", ""),
                "confidence": getattr(finding, "confidence", 0),
            }
            severity = str(item.get("severity", "LOW")).upper()
            file_path = _source_path(repo, item.get("file", "unknown"))
            findings_lines.extend([
                f"## {index}. [{severity}] {item.get('category', 'unknown')}",
                "",
                str(item.get("message", "No message was provided.")),
                "",
                f"**Location:** `{file_path}:{item.get('line', '?')}`  ",
                f"**Confidence:** {item.get('confidence', 0)}",
                "",
                f"**Evidence:** {item.get('evidence', 'No evidence text was recorded.')}",
                "",
            ])
    docs.append(_document("findings", "Static findings", "findings.md", "\n".join(findings_lines)))

    # Index is inserted first after optional AI notes have been merged.
    docs.insert(0, _document("index", "Documentation index", "index.md", _index_markdown(project_name, docs)))
    return docs


def _index_markdown(project_name: str, documents: list[dict[str, str]]) -> str:
    ordered = [doc for doc in documents if doc.get("path") != "index.md"]
    lines = [
        f"# Aposma documentation — {project_name}",
        "",
        "Generated Markdown reference for this repository. Start with the architecture overview, then browse function and type pages.",
        "",
        "## Core documents",
        "",
    ]
    core = [doc for doc in ordered if doc.get("kind") in {"architecture", "findings"}]
    for doc in core:
        lines.append(f"- [{doc['name']}]({doc['path']}) — {doc.get('kind', 'document').capitalize()}")
    lines.extend(["", "## Functions", ""])
    function_docs = [doc for doc in ordered if doc.get("kind") == "function"]
    for doc in function_docs:
        lines.append(f"- [{doc['name']}]({doc['path']})")
    if not function_docs:
        lines.append("No functions were reported by the analyzer.")
    lines.extend(["", "## Types and records", ""])
    type_docs = [doc for doc in ordered if doc.get("kind") in {"class", "type", "record"}]
    for doc in type_docs:
        lines.append(f"- [{doc['name']}]({doc['path']})")
    if not type_docs:
        lines.append("No C++ records were reported by the analyzer.")
    other_docs = [doc for doc in ordered if doc.get("kind") not in {"architecture", "findings", "function", "class", "type", "record"}]
    if other_docs:
        lines.extend(["", "## Additional notes", ""])
        for doc in other_docs:
            lines.append(f"- [{doc['name']}]({doc['path']})")
    lines.extend(["", "---", "Generated by Aposma. Review these pages against the source before treating them as authoritative."])
    return "\n".join(lines)


def _safe_relative_path(value: str) -> Path:
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or not candidate.parts or any(part in {"", ".", ".."} for part in candidate.parts):
        raise ValueError(f"Invalid generated documentation path: {value!r}")
    if candidate.suffix.lower() != ".md":
        raise ValueError(f"Generated documentation must use .md files: {value!r}")
    return Path(*candidate.parts)


def write_documents(repo: Path, documents: list[dict[str, str]], output_dir: Path | None = None) -> list[Path]:
    """Write an indexed .md documentation tree and remove stale Aposma pages."""
    out = (output_dir or (repo / ".aposma" / "docs")).resolve()
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / ".aposma-manifest.json"
    try:
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        previous_paths = previous.get("files", []) if isinstance(previous, dict) else []
    except (OSError, json.JSONDecodeError):
        previous_paths = []

    sanitized: list[dict[str, str]] = []
    used: set[str] = set()
    for index, document in enumerate(documents):
        name = str(document.get("name") or f"document-{index + 1}")
        kind = str(document.get("kind") or "document").lower()
        markdown = str(document.get("markdown") or "").strip()
        if not markdown:
            markdown = f"# {name}\n\nNo documentation content was returned for this item."
        raw_path = str(document.get("path") or f"{index:03d}-{_slug(name)}.md")
        relative = _safe_relative_path(raw_path)
        path_key = relative.as_posix()
        if path_key in used:
            suffix = hashlib.sha1(f"{name}:{index}".encode()).hexdigest()[:8]
            relative = relative.with_name(f"{relative.stem}-{suffix}.md")
            path_key = relative.as_posix()
        used.add(path_key)
        sanitized.append({"kind": kind, "name": name, "path": path_key, "markdown": markdown + "\n"})

    # Regenerate the index using the final, safe paths and actual output list.
    index_document = next((item for item in sanitized if item["path"] == "index.md"), None)
    if index_document is not None:
        index_document["markdown"] = _index_markdown(repo.name, sanitized) + "\n"

    written: list[Path] = []
    for document in sanitized:
        destination = (out / _safe_relative_path(document["path"])).resolve()
        if out not in destination.parents:
            raise ValueError(f"Generated documentation path escapes output directory: {document['path']}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(document["markdown"], encoding="utf-8")
        written.append(destination)

    current = {item["path"] for item in sanitized}
    for raw_previous in previous_paths:
        try:
            old_relative = _safe_relative_path(str(raw_previous))
        except ValueError:
            continue
        if old_relative.as_posix() in current:
            continue
        old_path = (out / old_relative).resolve()
        if out in old_path.parents and old_path.is_file():
            old_path.unlink()
    manifest_path.write_text(json.dumps({"files": sorted(current)}, indent=2) + "\n", encoding="utf-8")
    return written
