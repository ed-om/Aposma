from codelens.docs import fallback_documentation


def test_fallback_documentation() -> None:
    class Analysis:
        functions = [{"name": "main", "qualified_name": "main", "return_type": "int", "file": "main.cpp", "line": 1, "parameter_count": 0, "calls": []}]
        records = []

    docs = fallback_documentation(Analysis())
    assert docs[0]["kind"] == "function"
    assert "main" in docs[0]["markdown"]
