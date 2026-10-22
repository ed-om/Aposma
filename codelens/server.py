from __future__ import annotations

import json
import logging
import os
import sqlite3
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .config import Settings
from .github import GitHubError, handle_pull_request, verify_webhook
from .repositories import RepositorySourceError, resolve_repository_source

try:
    from fastapi import FastAPI, Header, HTTPException, Query, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover
    FastAPI = None

if FastAPI is not None:
    logger = logging.getLogger("aposma.api")

    from .analyzer import AnalyzerError, find_analyzer
    from .docs import write_documents
    from .ollama_client import health as ollama_health
    from .review import docs_repo, persist_review, review_repo
    from .storage import Database

    class RepositoryRequest(BaseModel):
        # Accept either a local directory or a GitHub repository URL in repo_path.
        repo_path: str = Field(min_length=1, max_length=4096)

    class ReviewRequest(RepositoryRequest):
        base: str | None = Field(default=None, max_length=256)
        use_ai: bool = True

    class DocsRequest(RepositoryRequest):
        use_ai: bool = True

    app = FastAPI(title="Aposma Local API", version="0.2.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # Keep the browser response useful while retaining the full traceback in
        # the terminal running Uvicorn. The API is intended for local use.
        logger.error("Unhandled error for %s %s", request.method, request.url.path, exc_info=(type(exc), exc, exc.__traceback__))
        return JSONResponse(
            status_code=500,
            content={
                "detail": (
                    f"Unexpected server error ({type(exc).__name__})."
                )
            },
        )

    def _repository(raw_source: str) -> tuple[Path, dict[str, str]]:
        try:
            return resolve_repository_source(raw_source)
        except RepositorySourceError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    def _finding_dict(finding: Any) -> dict[str, Any]:
        return asdict(finding)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/status")
    def api_status() -> dict[str, Any]:
        settings = Settings.from_env()
        try:
            analyzer_path = str(find_analyzer(settings))
            analyzer_available = True
            analyzer_error = None
        except AnalyzerError as exc:
            analyzer_path = None
            analyzer_available = False
            analyzer_error = str(exc)
        model_state = ollama_health(settings)
        return {
            "status": "ok",
            "analyzer": {"available": analyzer_available, "path": analyzer_path, "error": analyzer_error},
            "ollama": model_state,
            "storage": {"database_path": str(settings.db_path.resolve())},
        }

    @app.post("/api/review")
    def api_review(payload: ReviewRequest) -> dict[str, Any]:
        repo, source_info = _repository(payload.repo_path)
        settings = Settings.from_env()
        try:
            result, evidence = review_repo(repo, settings, payload.base, payload.use_ai)
            analysis_id = persist_review(settings, repo, result, evidence)
        except AnalyzerError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(status_code=504, detail="The analyzer timed out. Check the repository size and analyzer process.") from exc
        except sqlite3.Error as exc:
            logger.exception("Could not persist review for %s", repo)
            raise HTTPException(status_code=500, detail=f"Review finished but could not be saved to SQLite: {exc}") from exc
        except (OSError, ValueError) as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {
            "analysis_id": analysis_id,
            "repo_path": str(repo),
            "repository_source": source_info.get("source", payload.repo_path),
            "source_type": source_info.get("type", "local"),
            "source_label": source_info.get("label", repo.name),
            "workspace_path": source_info.get("workspace", str(repo)),
            "summary": result.summary,
            "ai_used": bool(result.raw_model_output),
            "findings": [_finding_dict(finding) for finding in result.findings],
        }

    @app.post("/api/docs")
    def api_docs(payload: DocsRequest) -> dict[str, Any]:
        repo, source_info = _repository(payload.repo_path)
        settings = Settings.from_env()
        try:
            result = docs_repo(repo, settings, use_ai=payload.use_ai)
            paths = write_documents(repo, result["documents"])
        except AnalyzerError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"Could not write documentation: {exc}") from exc
        return {
            "repo_path": str(repo),
            "repository_source": source_info.get("source", payload.repo_path),
            "source_type": source_info.get("type", "local"),
            "source_label": source_info.get("label", repo.name),
            "workspace_path": source_info.get("workspace", str(repo)),
            "summary": result.get("summary", ""),
            "ai_used": bool(result.get("ai_used", False)),
            "warning": result.get("warning"),
            "documents": [
                {**document, "saved_path": str(paths[index])}
                for index, document in enumerate(result.get("documents", []))
                if index < len(paths)
            ],
            "saved_to": [str(path) for path in paths],
            "docs_directory": str((repo / ".aposma" / "docs").resolve()),
        }

    @app.get("/api/history")
    def api_history(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
        settings = Settings.from_env()
        database = Database(settings.db_path)
        return {"analyses": database.recent(limit)}

    @app.post("/webhooks/github")
    async def github_webhook(request: Request, x_hub_signature_256: str | None = Header(default=None)) -> dict[str, object]:
        body = await request.body()
        secret = os.getenv("APOSMA_GITHUB_WEBHOOK_SECRET")
        if not secret:
            raise HTTPException(status_code=500, detail="APOSMA_GITHUB_WEBHOOK_SECRET is not configured")
        if not verify_webhook(body, x_hub_signature_256, secret):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

        event = request.headers.get("X-GitHub-Event", "")
        payload = json.loads(body.decode("utf-8"))
        if event != "pull_request":
            return {"ok": True, "ignored": True, "reason": f"event={event}"}
        try:
            result = handle_pull_request(payload, Settings.from_env())
            return {"ok": True, **result}
        except GitHubError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
else:
    app = None
