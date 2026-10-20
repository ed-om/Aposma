from __future__ import annotations

import json
import os

from .config import Settings
from .github import GitHubError, handle_pull_request, verify_webhook

try:
    from fastapi import FastAPI, Header, HTTPException, Request
except ImportError:  # pragma: no cover
    FastAPI = None

if FastAPI is not None:
    app = FastAPI(title="Aposma GitHub Webhook Server", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

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
