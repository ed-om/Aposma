from __future__ import annotations

import json
from pathlib import Path
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
