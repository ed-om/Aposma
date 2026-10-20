from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from .config import Settings
from .models import CodeAnalysis, Finding


class AnalyzerError(RuntimeError):
    pass


def _candidate_binaries(settings: Settings) -> list[Path]:
    candidates = [settings.analyzer_bin]
    root = Path(__file__).resolve().parents[1]
    candidates.extend([
        root / "build" / "aposma-analyzer",
        root / "build" / "bin" / "aposma-analyzer",
    ])
    env = os.getenv("APOSMA_ANALYZER_BIN")
    if env:
        candidates.insert(0, Path(env))
    return list(dict.fromkeys(candidates))


def find_analyzer(settings: Settings) -> Path:
    for candidate in _candidate_binaries(settings):
        if candidate.exists() and os.access(candidate, os.X_OK):
            return candidate
    raise AnalyzerError(
        "Aposma analyzer binary was not found. Build it with `cmake -S . -B build && cmake --build build` "
        "or set APOSMA_ANALYZER_BIN."
    )


def run_analyzer(repo: Path, settings: Settings) -> CodeAnalysis:
    binary = find_analyzer(settings)
    cpp_files = []
    for path in repo.rglob("*.cpp"):
        rel = path.relative_to(repo)
        if any(part in {"build", ".git", "node_modules", "third_party", "vendor"} for part in rel.parts):
            continue
        cpp_files.append(str(path))
    if not cpp_files:
        raise AnalyzerError(f"No .cpp files found under {repo}")

    compile_commands = repo / "compile_commands.json"
    cmd = [str(binary)]
    if compile_commands.exists():
        cmd += ["-p", str(repo)]
    else:
        cmd += cpp_files
        cmd += ["--", "-std=c++20", f"-I{repo}"]

    if compile_commands.exists():
        # When a compilation database exists, passing all files explicitly lets
        # CommonOptionsParser choose their compile commands.
        cmd += cpp_files

    proc = subprocess.run(
        cmd,
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=180,
        check=False,
    )
    if proc.returncode != 0:
        raise AnalyzerError(f"Analyzer failed ({proc.returncode}):\n{proc.stderr[-5000:]}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AnalyzerError(f"Analyzer returned invalid JSON: {exc}\n{proc.stdout[-2000:]}") from exc

    return CodeAnalysis(
        functions=data.get("functions", []),
        records=data.get("records", []),
        findings=[Finding.from_dict(x) for x in data.get("findings", [])],
        edges=data.get("edges", []),
        raw=data,
    )
