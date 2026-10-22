from argparse import Namespace
from pathlib import Path

from codelens.config import Settings
from codelens.models import ReviewResult
from codelens.cli import cmd_docs, cmd_review


def test_cli_docs_writes_markdown_files_for_local_path(tmp_path, monkeypatch, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    settings = Settings(db_path=tmp_path / "db.sqlite3")
    monkeypatch.setattr("codelens.cli._settings", lambda: settings)
    monkeypatch.setattr("codelens.cli.docs_repo", lambda *_args, **_kwargs: {
        "summary": "Generated test docs.",
        "documents": [
            {"kind": "index", "name": "Index", "path": "index.md", "markdown": "# Index\n"},
            {"kind": "function", "name": "main", "path": "functions/main.md", "markdown": "# main\n"},
        ],
        "ai_used": False,
    })

    result = cmd_docs(Namespace(path=str(repo), no_ai=True, output_dir=None))
    assert result == 0
    assert (repo / ".aposma" / "docs" / "index.md").is_file()
    assert (repo / ".aposma" / "docs" / "functions" / "main.md").is_file()
    output = capsys.readouterr().out
    assert "Generated 2 Markdown document(s)" in output


def test_cli_review_uses_repository_source_and_persists_result(tmp_path, monkeypatch, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    settings = Settings(db_path=tmp_path / "db.sqlite3")
    monkeypatch.setattr("codelens.cli._settings", lambda: settings)
    monkeypatch.setattr(
        "codelens.cli.review_repo",
        lambda *_args, **_kwargs: (ReviewResult("No findings.", []), {"static_findings": []}),
    )
    monkeypatch.setattr("codelens.cli.persist_review", lambda *_args: 42)

    result = cmd_review(Namespace(path=str(repo), base=None, no_ai=True))
    assert result == 0
    output = capsys.readouterr().out
    assert "Aposma Review — repo" in output
    assert "Stored analysis: #42" in output
    assert "No findings." in output
