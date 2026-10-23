import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from codelens.config import Settings
from codelens.models import ReviewFinding, ReviewResult
from codelens.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_review_endpoint_persists_and_returns_findings(client, tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    settings = Settings(db_path=tmp_path / "analyses.sqlite3")
    monkeypatch.setattr("codelens.server.Settings.from_env", lambda: settings)
    monkeypatch.setattr(
        "codelens.server.review_repo",
        lambda repo_path, _settings, base, use_ai: (
            ReviewResult("Found a potential issue.", [ReviewFinding(
                severity="HIGH", category="correctness", location="main.cpp:4",
                title="Possible null dereference", finding="Pointer may be null.",
                reason="The pointer is dereferenced without a visible guard.",
                evidence=["pointer access"], confidence=0.91,
            )], raw_model_output="{\"summary\":\"Found a potential issue.\"}"),
            {"static_findings": []},
        ),
    )
    monkeypatch.setattr("codelens.server.persist_review", lambda *_args: 17)
    response = client.post("/api/review", json={"repo_path": str(repo), "base": None, "use_ai": True})
    assert response.status_code == 200
    data = response.json()
    assert data["analysis_id"] == 17
    assert data["ai_used"] is True
    assert data["findings"][0]["severity"] == "HIGH"


def test_review_rejects_nonexistent_repository(client, tmp_path):
    response = client.post("/api/review", json={"repo_path": str(tmp_path / "missing")})
    assert response.status_code == 422


def test_history_endpoint(client, tmp_path, monkeypatch):
    settings = Settings(db_path=tmp_path / "analyses.sqlite3")
    monkeypatch.setattr("codelens.server.Settings.from_env", lambda: settings)
    response = client.get("/api/history?limit=10")
    assert response.status_code == 200
    assert response.json() == {"analyses": []}


def test_status_endpoint_exposes_analyzer_and_model_state(client, monkeypatch):
    from pathlib import Path
    from codelens.ollama_client import health as ollama_health

    monkeypatch.setattr("codelens.server.Settings.from_env", lambda: Settings(db_path=Path("/tmp/aposma-test-status.sqlite3")))
    monkeypatch.setattr("codelens.server.find_analyzer", lambda _settings: Path("/tmp/aposma-analyzer"))
    monkeypatch.setattr("codelens.server.ollama_health", lambda _settings: {
        "reachable": True, "model": "qwen2.5-coder:3b", "model_installed": True,
        "installed_models": ["qwen2.5-coder:3b"], "error": None,
    })
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["analyzer"]["available"] is True
    assert data["ollama"]["model_installed"] is True


def test_docs_endpoint_returns_written_documentation(client, tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    doc_path = repo / ".aposma" / "docs" / "000-main.md"
    monkeypatch.setattr("codelens.server.Settings.from_env", lambda: Settings(db_path=tmp_path / "db.sqlite3"))
    monkeypatch.setattr("codelens.server.docs_repo", lambda *_args, **_kwargs: {
        "summary": "Deterministic documentation generated from the code model.",
        "documents": [{"kind": "function", "name": "main", "markdown": "## main\n"}],
        "ai_used": False,
    })

    def fake_write(_repo, _documents):
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text("## main\n", encoding="utf-8")
        return [doc_path]

    monkeypatch.setattr("codelens.server.write_documents", fake_write)
    response = client.post("/api/docs", json={"repo_path": str(repo)})
    assert response.status_code == 200
    assert response.json()["ai_used"] is False
    assert response.json()["documents"][0]["name"] == "main"
    assert doc_path.exists()


def test_review_endpoint_accepts_github_source_and_reports_workspace(client, tmp_path, monkeypatch):
    repo = tmp_path / "github-checkout"
    repo.mkdir()
    settings = Settings(db_path=tmp_path / "github.sqlite3")
    monkeypatch.setattr("codelens.server.Settings.from_env", lambda: settings)
    monkeypatch.setattr(
        "codelens.server.resolve_repository_source",
        lambda source: (repo, {
            "type": "github", "source": source, "label": "example/project", "workspace": str(repo),
        }),
    )
    monkeypatch.setattr(
        "codelens.server.review_repo",
        lambda *_args: (ReviewResult("Review complete.", []), {"static_findings": []}),
    )
    monkeypatch.setattr("codelens.server.persist_review", lambda *_args: 23)

    response = client.post(
        "/api/review",
        json={"repo_path": "https://github.com/example/project", "use_ai": False},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source_type"] == "github"
    assert body["source_label"] == "example/project"
    assert body["analysis_id"] == 23
