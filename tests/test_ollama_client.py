from codelens.config import Settings
from codelens.ollama_client import health, is_available


def test_ollama_health_reports_reachable_but_missing_model(monkeypatch):
    monkeypatch.setattr(
        "codelens.ollama_client._get_json",
        lambda url, timeout=3: {"models": [{"name": "llama3.2:3b"}]},
    )
    state = health(Settings(ollama_model="qwen2.5-coder:3b"))
    assert state["reachable"] is True
    assert state["model_installed"] is False
    assert is_available(Settings(ollama_model="qwen2.5-coder:3b")) is False


def test_ollama_health_confirms_installed_model(monkeypatch):
    monkeypatch.setattr(
        "codelens.ollama_client._get_json",
        lambda url, timeout=3: {"models": [{"name": "qwen2.5-coder:3b"}]},
    )
    settings = Settings(ollama_model="qwen2.5-coder:3b")
    assert health(settings)["model_installed"] is True
    assert is_available(settings) is True


def test_ollama_health_handles_offline_service(monkeypatch):
    from codelens.ollama_client import OllamaError

    def fail(url, timeout=3):
        raise OllamaError("connection refused")

    monkeypatch.setattr("codelens.ollama_client._get_json", fail)
    state = health(Settings())
    assert state["reachable"] is False
    assert state["model_installed"] is False
    assert "connection refused" in state["error"]
