from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .config import Settings


class OllamaError(RuntimeError):
    pass


SYSTEM_REVIEW = """You are Aposma, a grounded software-maintenance assistant.
You analyze C++ code changes using evidence produced by deterministic program analysis.
Never invent code facts that are not in the evidence. Treat static findings as hypotheses unless
there is sufficient evidence to support them. Prefer a small number of high-confidence findings.
Return JSON only with this shape:
{
  \"summary\": \"brief summary\",
  \"findings\": [
    {
      \"severity\": \"HIGH|MEDIUM|LOW|INFO\",
      \"category\": \"correctness|security|performance|maintainability|documentation|other\",
      \"location\": \"path:line\",
      \"title\": \"short title\",
      \"finding\": \"what the developer should know\",
      \"reason\": \"why, grounded in evidence\",
      \"evidence\": [\"specific evidence item\"],
      \"confidence\": 0.0
    }
  ]
}
"""

SYSTEM_DOCS = """You are Aposma, a grounded C++ documentation assistant.
Generate concise, factual documentation from the provided code-structure evidence.
Do not invent behavior, parameters, dependencies, or failure cases that are not supported.
Return JSON only with this shape:
{
  \"summary\": \"brief summary\",
  \"documents\": [
    {
      \"kind\": \"function|class|architecture\",
      \"name\": \"name\",
      \"markdown\": \"documentation in Markdown\"
    }
  ]
}
"""


def _post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise OllamaError(str(exc)) from exc
    if not isinstance(data, dict):
        raise OllamaError("Ollama returned a non-object JSON response")
    return data


def _get_json(url: str, timeout: int = 3) -> dict[str, Any]:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise OllamaError(str(exc)) from exc
    if not isinstance(data, dict):
        raise OllamaError("Ollama returned a non-object JSON response")
    return data


def generate(settings: Settings, system: str, prompt: str, json_mode: bool = True) -> str:
    payload: dict[str, Any] = {
        "model": settings.ollama_model,
        "system": system,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1},
    }
    if json_mode:
        payload["format"] = "json"
    response = _post_json(f"{settings.ollama_url.rstrip('/')}/api/generate", payload, settings.ollama_timeout)
    text = response.get("response")
    if not isinstance(text, str):
        raise OllamaError("Ollama response did not contain a string 'response' field")
    return text.strip()


def health(settings: Settings) -> dict[str, Any]:
    """Report API reachability and whether the configured model is installed."""
    try:
        data = _get_json(f"{settings.ollama_url.rstrip('/')}/api/tags")
    except OllamaError as exc:
        return {
            "reachable": False,
            "model": settings.ollama_model,
            "model_installed": False,
            "installed_models": [],
            "error": str(exc),
        }

    models_data = data.get("models", [])
    model_names = [
        str(item.get("name") or item.get("model"))
        for item in models_data
        if isinstance(item, dict) and (item.get("name") or item.get("model"))
    ] if isinstance(models_data, list) else []
    expected = settings.ollama_model.strip()
    installed = expected in model_names
    # Ollama may report an implicit latest tag for models configured without one.
    if ":" not in expected:
        installed = installed or f"{expected}:latest" in model_names

    return {
        "reachable": True,
        "model": expected,
        "model_installed": installed,
        "installed_models": model_names,
        "error": None if installed else f"Configured model '{expected}' is not installed in Ollama.",
    }


def is_available(settings: Settings) -> bool:
    state = health(settings)
    return bool(state["reachable"] and state["model_installed"])


def review(settings: Settings, evidence_json: str) -> str:
    prompt = (
        "Analyze the following evidence package for a C++ change. "
        "Focus on correctness, security, performance, maintainability, and the reliability of the evidence.\n\n"
        + evidence_json
    )
    return generate(settings, SYSTEM_REVIEW, prompt, json_mode=True)


def docs(settings: Settings, evidence_json: str) -> str:
    prompt = "Generate factual Markdown documentation from this code knowledge package:\n\n" + evidence_json
    return generate(settings, SYSTEM_DOCS, prompt, json_mode=True)
