from pathlib import Path

from codelens.docs import fallback_documentation, write_documents
from codelens.models import CodeAnalysis, Finding


def sample_analysis():
    return CodeAnalysis(
        functions=[{
            "name": "main",
            "qualified_name": "main",
            "return_type": "int",
            "file": "main.cpp",
            "line": 1,
            "end_line": 3,
            "parameter_count": 0,
            "control_count": 0,
            "calls": ["work"],
            "pointer_variables": [],
            "pointer_uses": [],
        }],
        records=[{"name": "User", "qualified_name": "User", "file": "main.cpp", "line": 5}],
        findings=[Finding("f1", "correctness", "HIGH", "Possible issue", "main.cpp", 2, 0.9, "pointer use")],
        edges=[{"caller": "main", "callee": "work"}],
        raw={},
    )


def test_fallback_documentation_includes_index_functions_types_architecture_and_findings(tmp_path: Path) -> None:
    docs = fallback_documentation(sample_analysis(), tmp_path)
    by_path = {doc["path"]: doc for doc in docs}

    assert "index.md" in by_path
    assert "architecture.md" in by_path
    assert "findings.md" in by_path
    assert "functions/main.md" in by_path
    assert "types/user.md" in by_path
    assert "[main](functions/main.md)" in by_path["index.md"]["markdown"]
    assert "Possible issue" in by_path["findings.md"]["markdown"]
    assert "work" in by_path["functions/main.md"]["markdown"]


def test_write_documents_creates_real_markdown_tree_and_removes_stale_pages(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    docs = fallback_documentation(sample_analysis(), repo)
    first_paths = write_documents(repo, docs)
    output = repo / ".aposma" / "docs"

    assert (output / "index.md").is_file()
    assert (output / "architecture.md").is_file()
    assert (output / "findings.md").is_file()
    assert (output / "functions" / "main.md").is_file()
    assert (output / "types" / "user.md").is_file()
    assert all(path.suffix == ".md" for path in first_paths)

    reduced = [doc for doc in docs if doc["path"] != "functions/main.md"]
    write_documents(repo, reduced)
    assert not (output / "functions" / "main.md").exists()
    assert (output / ".aposma-manifest.json").is_file()
