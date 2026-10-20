from pathlib import Path

from codelens.config import Settings
from codelens.evidence import build_evidence
from codelens.models import CodeAnalysis, Finding


def test_build_evidence_without_git(tmp_path: Path) -> None:
    (tmp_path / "main.cpp").write_text("int main(){return 0;}\n", encoding="utf-8")
    analysis = CodeAnalysis(
        functions=[{"name": "main", "file": str(tmp_path / "main.cpp")}],
        records=[],
        findings=[Finding("f", "correctness", "HIGH", "bad", "main.cpp", 1, 0.9, "e")],
        edges=[],
        raw={},
    )
    evidence = build_evidence(tmp_path, analysis, Settings())
    assert evidence["language"] == "C++"
    assert evidence["static_findings"][0]["severity"] == "HIGH"
