from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class GitError(RuntimeError):
    pass


def _run(args: list[str], cwd: Path, timeout: int = 30) -> str:
    proc = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise GitError(proc.stderr.strip() or "git command failed")
    return proc.stdout


def is_repo(path: Path) -> bool:
    return (path / ".git").exists()


def head(path: Path) -> str:
    return _run(["git", "rev-parse", "HEAD"], path).strip()


def diff(path: Path, base: str | None = None, max_chars: int = 30_000) -> str:
    if base:
        output = _run(["git", "diff", "--no-ext-diff", "--unified=40", base, "HEAD"], path)
    else:
        try:
            output = _run(["git", "diff", "--no-ext-diff", "--unified=40", "HEAD~1", "HEAD"], path)
        except GitError:
            output = _run(["git", "diff", "--no-ext-diff", "--unified=40"], path)
    return output[:max_chars]


def changed_files(path: Path, base: str | None = None) -> list[str]:
    if base:
        output = _run(["git", "diff", "--name-only", base, "HEAD"], path)
    else:
        try:
            output = _run(["git", "diff", "--name-only", "HEAD~1", "HEAD"], path)
        except GitError:
            output = _run(["git", "diff", "--name-only"], path)
    return [line.strip() for line in output.splitlines() if line.strip()]


def commit_message(path: Path, commit: str = "HEAD") -> str:
    try:
        return _run(["git", "log", "-1", "--pretty=%B", commit], path).strip()
    except GitError:
        return ""


def recent_log(path: Path, count: int = 10) -> list[str]:
    output = _run(["git", "log", f"-{count}", "--pretty=%h %s"], path)
    return [line.strip() for line in output.splitlines() if line.strip()]
