from pathlib import Path

import pytest

from codelens.repositories import RepositorySourceError, parse_github_source, resolve_repository_source


def test_parse_github_repository_url():
    parsed = parse_github_source("https://github.com/example/project")
    assert parsed == ("example", "project", "https://github.com/example/project.git")


def test_parse_github_repo_subpage_uses_repository_root():
    parsed = parse_github_source("https://github.com/example/project/tree/main")
    assert parsed == ("example", "project", "https://github.com/example/project.git")


def test_parse_github_shorthand():
    parsed = parse_github_source("example/project.git")
    assert parsed == ("example", "project", "https://github.com/example/project.git")


def test_resolve_existing_local_directory(tmp_path: Path):
    repo = tmp_path / "local-repo"
    repo.mkdir()
    resolved, source = resolve_repository_source(str(repo))
    assert resolved == repo.resolve()
    assert source["type"] == "local"
    assert source["label"] == "local-repo"


def test_rejects_unrecognized_remote_and_missing_path():
    with pytest.raises(RepositorySourceError, match="does not exist"):
        resolve_repository_source("/this/path/does/not/exist")
    with pytest.raises(RepositorySourceError, match="Only GitHub"):
        resolve_repository_source("https://gitlab.com/example/project")
