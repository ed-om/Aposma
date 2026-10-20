from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import ReviewResult


class Database:
    def __init__(self, path: Path):
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repository TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    findings_json TEXT NOT NULL,
                    evidence_json TEXT NOT NULL
                )"""
            )

    def save_analysis(self, repo: Path, result: ReviewResult, evidence: dict[str, Any]) -> int:
        self.initialize()
        created = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.path) as db:
            cur = db.execute(
                "INSERT INTO analyses(repository, created_at, summary, findings_json, evidence_json) VALUES (?, ?, ?, ?, ?)",
                (
                    str(repo),
                    created,
                    result.summary,
                    json.dumps([f.__dict__ for f in result.findings], ensure_ascii=False),
                    json.dumps(evidence, ensure_ascii=False),
                ),
            )
            return int(cur.lastrowid)

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        self.initialize()
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT id, repository, created_at, summary FROM analyses ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]
