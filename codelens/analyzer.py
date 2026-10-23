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


def _compiler_builtin_include_dirs() -> list[Path]:
    """Find compiler-provided headers Clang may not discover on its own.

    This matters on rolling-release Linux systems where Clang's linked
    LibTooling version and the installed GCC version can change independently.
    Only paths containing stddef.h are returned.
    """
    candidates: list[Path] = []
    queries = (
        ("clang++", "-print-resource-dir", "resource"),
        ("clang", "-print-resource-dir", "resource"),
        ("gcc", "-print-file-name=include", "include"),
        ("g++", "-print-file-name=include", "include"),
    )
    for compiler, flag, kind in queries:
        try:
            result = subprocess.run(
                [compiler, flag],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=3,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode != 0:
            continue
        value = result.stdout.strip()
        if not value:
            continue
        path = Path(value)
        if kind == "resource":
            path = path / "include"
        try:
            path = path.resolve()
        except OSError:
            continue
        if (path / "stddef.h").is_file() and path not in candidates:
            candidates.append(path)
    return candidates


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
    builtin_include_dirs = _compiler_builtin_include_dirs()
    if compile_commands.exists():
        # Supply compiler built-in headers explicitly. Clang LibTooling does not
        # always discover the active GCC installation correctly on Arch Linux.
        for include_dir in builtin_include_dirs:
            cmd.extend([
                f"--extra-arg-before=-isystem",
                f"--extra-arg-before={include_dir}",
            ])
        cmd += ["-p", str(repo)]
    else:
        cmd += cpp_files
        cmd += ["--", "-std=c++20", f"-I{repo}"]
        for include_dir in builtin_include_dirs:
            cmd += ["-isystem", str(include_dir)]

    if compile_commands.exists():
        # When a compilation database exists, passing all files explicitly lets
        # CommonOptionsParser choose their compile commands.
        cmd += cpp_files

    try:
        proc = subprocess.run(
            cmd,
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AnalyzerError(f"Analyzer timed out after 180 seconds while scanning {repo}.") from exc
    except OSError as exc:
        raise AnalyzerError(f"Could not start analyzer at {binary}: {exc}") from exc
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
