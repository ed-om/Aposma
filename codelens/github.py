from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .config import Settings
from .review import review_repo


class GitHubError(RuntimeError):
    pass


def verify_webhook(payload: bytes, signature: str | None, secret: str) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def app_jwt(app_id: str, private_key_pem: str) -> str:
    try:
        import jwt
    except ImportError as exc:
        raise GitHubError("PyJWT is required for GitHub App authentication. Install with `pip install -e '.[server]'`.") from exc
    return str(jwt.encode({"iat": int(__import__("time").time()) - 30, "exp": int(__import__("time").time()) + 540, "iss": app_id}, private_key_pem, algorithm="RS256"))


def _request(url: str, token: str | None = None, data: dict[str, Any] | None = None, method: str = "GET") -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "aposma/0.1.0",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise GitHubError(f"GitHub API {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise GitHubError(str(exc)) from exc


def installation_token(app_id: str, private_key_pem: str, installation_id: int) -> str:
    token = app_jwt(app_id, private_key_pem)
    data = _request(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        token=token,
        method="POST",
        data={},
    )
    return str(data["token"])


def create_check_run(token: str, owner: str, repo: str, head_sha: str, summary: str, annotations: list[dict[str, Any]], conclusion: str) -> dict[str, Any]:
    payload = {
        "name": "Aposma",
        "head_sha": head_sha,
        "status": "completed",
        "conclusion": conclusion,
        "output": {
            "title": "Aposma Code Intelligence",
            "summary": summary[:65_000],
            "annotations": annotations[:50],
        },
    }
    return _request(
        f"https://api.github.com/repos/{owner}/{repo}/check-runs",
        token=token,
        data=payload,
        method="POST",
    )


def _clone_with_token(clone_url: str, token: str, destination: Path, ref: str) -> None:
    # GitHub's HTTPS clone accepts an installation token as x-access-token.
    safe_url = clone_url.replace("https://", f"https://x-access-token:{token}@", 1)
    subprocess.run(["git", "clone", "--filter=blob:none", safe_url, str(destination)], check=True, timeout=180, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    subprocess.run(["git", "-C", str(destination), "checkout", "--detach", ref], check=True, timeout=60, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    # Pass the short-lived token through Git's environment-based extra header,
    # not a clone URL that could leak through process listings or exception text.
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    credential = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "http.https://github.com/.extraheader"
    env["GIT_CONFIG_VALUE_0"] = f"AUTHORIZATION: basic {credential}"
    subprocess.run(
        ["git", "clone", "--filter=blob:none", clone_url, str(destination)],
        check=True,
        timeout=180,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    subprocess.run(
        ["git", "-C", str(destination), "checkout", "--detach", ref],
        check=True,
        timeout=60,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )


def handle_pull_request(payload: dict[str, Any], settings: Settings) -> dict[str, Any]:
    action = payload.get("action")
    if action not in {"opened", "synchronize", "reopened"}:
        return {"ignored": True, "reason": f"action={action}"}

    installation = payload.get("installation") or {}
    installation_id = installation.get("id")
    app_id = os.getenv("APOSMA_GITHUB_APP_ID")
    key_path = os.getenv("APOSMA_GITHUB_PRIVATE_KEY_PATH")
    if not installation_id or not app_id or not key_path:
        raise GitHubError("GitHub App ID, private key path, and installation id are required")
    private_key = Path(key_path).read_text(encoding="utf-8")
    token = installation_token(app_id, private_key, int(installation_id))

    repository = payload["repository"]
    full_name = repository["full_name"]
    owner, repo_name = full_name.split("/", 1)
    head_info = payload["pull_request"]["head"]
    base_info = payload["pull_request"]["base"]
    head_sha = head_info["sha"]
    base_sha = base_info["sha"]

    with tempfile.TemporaryDirectory(prefix="aposma-gh-") as tmp:
        repo_path = Path(tmp) / "repo"
        _clone_with_token(repository["clone_url"], token, repo_path, head_sha)
        result, _evidence = review_repo(repo_path, settings, base=base_sha, use_ai=True)

        annotations = []
        for finding in result.findings:
            if not finding.location or ":" not in finding.location:
                continue
            file_part, line_part = finding.location.rsplit(":", 1)
            try:
                line = int(line_part)
            except ValueError:
                line = 1
            annotations.append(
                {
                    "path": file_part,
                    "start_line": max(1, line),
                    "end_line": max(1, line),
                    "annotation_level": "failure" if finding.severity.upper() == "HIGH" else "warning",
                    "message": f"{finding.title}: {finding.finding}",
                }
            )

        conclusion = "failure" if any(f.severity.upper() == "HIGH" for f in result.findings) else "success"
        check = create_check_run(token, owner, repo_name, head_sha, result.summary, annotations, conclusion)
        return {"ignored": False, "check_run_id": check.get("id"), "conclusion": conclusion}
