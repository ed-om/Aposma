from __future__ import annotations

import base64
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse


class RepositorySourceError(RuntimeError):
    """A local repository path or GitHub URL could not be resolved."""

    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


def _git_url(owner: str, repository: str) -> str:
    repo_name = repository[:-4] if repository.lower().endswith(".git") else repository
    valid = re.compile(r"^[A-Za-z0-9_.-]+$")
    if not owner or not repo_name or owner in {".", ".."} or repo_name in {".", ".."}:
        raise RepositorySourceError("Provide a GitHub repository URL such as https://github.com/owner/repository.")
    if not valid.fullmatch(owner) or not valid.fullmatch(repo_name):
        raise RepositorySourceError("The GitHub repository owner or name contains unsupported characters.")
    return f"https://github.com/{owner}/{repo_name}.git"


def parse_github_source(source: str) -> tuple[str, str, str] | None:
    """Return (owner, repo, canonical HTTPS URL) for supported GitHub inputs."""
    value = source.strip()
    if not value:
        return None

    if "//" in value:
        parsed = urlparse(value)
        if parsed.scheme not in {"https", "http", "ssh"} or (parsed.hostname or "").lower() != "github.com":
            raise RepositorySourceError("Only GitHub repository URLs are supported. Local paths are also accepted.")
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            raise RepositorySourceError("GitHub URL must include both an owner and repository name.")
        owner, repository = parts[0], parts[1]
        if repository.lower().endswith(".git"):
            repository = repository[:-4]
        return owner, repository, _git_url(owner, repository)

    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?", value):
        owner, repository = value.split("/", 1)
        repository = repository[:-4] if repository.lower().endswith(".git") else repository
        return owner, repository, _git_url(owner, repository)
    return None


def _origin_url(repo: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "remote", "get-url", "origin"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip().removesuffix(".git").rstrip("/").lower()


def _git_environment() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    token = env.get("APOSMA_GITHUB_TOKEN", "").strip()
    if token:
        # Feed authentication to Git through environment-based config, not a URL
        # containing a credential that could appear in process listings or logs.
        credential = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        env["GIT_CONFIG_COUNT"] = "1"
        env["GIT_CONFIG_KEY_0"] = "http.https://github.com/.extraheader"
        env["GIT_CONFIG_VALUE_0"] = f"AUTHORIZATION: basic {credential}"
    return env


def _clone(owner: str, repository: str, url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix=".aposma-clone-", dir=destination.parent) as temp_dir:
            clone_path = Path(temp_dir) / "checkout"
            result = subprocess.run(
                ["git", "clone", "--filter=blob:none", url, str(clone_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300,
                check=False,
                env=_git_environment(),
            )
            if result.returncode != 0:
                detail = result.stderr.strip()[-1800:] or "git clone failed without an error message"
                if "Authentication failed" in detail or "Repository not found" in detail or "could not read Username" in detail:
                    raise RepositorySourceError(
                        f"Could not access GitHub repository {owner}/{repository}. For a private repository, set APOSMA_GITHUB_TOKEN with a token that can read it. Details: {detail}",
                        status_code=502,
                    )
                raise RepositorySourceError(f"Could not clone GitHub repository {owner}/{repository}: {detail}", status_code=502)
            os.replace(clone_path, destination)
    except subprocess.TimeoutExpired as exc:
        raise RepositorySourceError(f"Cloning {owner}/{repository} timed out after 300 seconds.", status_code=504) from exc
    except OSError as exc:
        raise RepositorySourceError(f"Could not create a local workspace for {owner}/{repository}: {exc}", status_code=500) from exc


def resolve_repository_source(source: str) -> tuple[Path, dict[str, str]]:
    """Resolve a local folder or GitHub URL into an on-disk repository.

    GitHub checkouts are stored persistently under APOSMA_WORKSPACE_DIR (or
    ~/.local/share/aposma/workspaces), so generated Markdown stays available.
    Existing clones are reused without resetting uncommitted local changes.
    """
    raw = source.strip()
    if not raw:
        raise RepositorySourceError("Enter a local repository path or a GitHub repository URL.")

    local_path = Path(raw).expanduser()
    if local_path.exists():
        resolved = local_path.resolve()
        if not resolved.is_dir():
            raise RepositorySourceError("Repository path must point to a directory.")
        return resolved, {"type": "local", "source": raw, "label": resolved.name or str(resolved)}

    parsed = parse_github_source(raw)
    if not parsed:
        raise RepositorySourceError(
            f"Local repository path does not exist: {local_path.resolve()}. Enter an existing directory or a GitHub URL."
        )

    owner, repository, url = parsed
    workspace_root = Path(os.getenv("APOSMA_WORKSPACE_DIR", str(Path.home() / ".local" / "share" / "aposma" / "workspaces"))).expanduser().resolve()
    destination = workspace_root / owner / repository
    if destination.exists():
        if not destination.is_dir() or not (destination / ".git").is_dir():
            raise RepositorySourceError(
                f"Workspace path exists but is not a Git checkout: {destination}. Move it aside or set APOSMA_WORKSPACE_DIR."
            )
        origin = _origin_url(destination)
        expected = url.removesuffix(".git").rstrip("/").lower()
        if origin is None or origin != expected:
            raise RepositorySourceError(f"Workspace origin does not match {owner}/{repository}: {destination}")
    else:
        _clone(owner, repository, url, destination)

    return destination.resolve(), {
        "type": "github",
        "source": raw,
        "label": f"{owner}/{repository}",
        "workspace": str(destination.resolve()),
    }
