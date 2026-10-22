from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5-coder:3b"
    db_path: Path = Path(".data/aposma.sqlite3")
    analyzer_bin: Path = Path("build/aposma-analyzer")
    max_source_chars: int = 50_000
    max_diff_chars: int = 30_000
    ollama_timeout: int = 180

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            ollama_url=os.getenv("APOSMA_OLLAMA_URL", cls.ollama_url),
            ollama_model=os.getenv("APOSMA_OLLAMA_MODEL", cls.ollama_model),
            db_path=Path(os.getenv("APOSMA_DB", str(cls.db_path))),
            analyzer_bin=Path(os.getenv("APOSMA_ANALYZER_BIN", str(cls.analyzer_bin))),
            max_source_chars=int(os.getenv("APOSMA_MAX_SOURCE_CHARS", cls.max_source_chars)),
            max_diff_chars=int(os.getenv("APOSMA_MAX_DIFF_CHARS", cls.max_diff_chars)),
            ollama_timeout=int(os.getenv("APOSMA_OLLAMA_TIMEOUT", cls.ollama_timeout)),
        )
