"""SQLite implementation of the ScoreStore protocol."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from arbiter.types import QualityScore

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class SQLiteScoreStore:
    """Persists evaluation scores to a local SQLite database."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._conn = sqlite3.connect(str(self._db_path))
        self._apply_schema()

    def _apply_schema(self) -> None:
        schema = _SCHEMA_PATH.read_text()
        self._conn.executescript(schema)

    async def save_score(self, score: QualityScore) -> None:
        raise NotImplementedError

    async def get_scores(
        self, agent_name: str, since: datetime, limit: int = 100
    ) -> list[QualityScore]:
        raise NotImplementedError

    async def save_override(
        self, eval_id: str, corrected_dimensions: dict[str, float], corrector: str
    ) -> None:
        raise NotImplementedError

    def close(self) -> None:
        self._conn.close()
