from codelens.models import Finding
from codelens.ranking import rank


def test_high_confidence_high_severity_comes_first() -> None:
    findings = [
        Finding("1", "maintainability", "LOW", "low", "a.cpp", 1, 1.0, "e"),
        Finding("2", "correctness", "HIGH", "high", "a.cpp", 2, 0.7, "e"),
    ]
    ordered = rank(findings)
    assert ordered[0].severity == "HIGH"
