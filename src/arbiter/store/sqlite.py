"""SQLite implementation of the ScoreStore protocol."""

from __future__ import annotations

import asyncio
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from arbiter.types import QualityScore

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class SQLiteScoreStore:
    """Persists evaluation scores to a local SQLite database."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._apply_schema()

    def _apply_schema(self) -> None:
        schema = _SCHEMA_PATH.read_text()
        self._conn.executescript(schema)

    def _save_score_sync(self, score: QualityScore) -> None:
        self._conn.execute(
            "INSERT INTO evaluations (eval_id, agent_name, task_id, evaluator_model, confidence, cost_usd, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                score.eval_id,
                score.agent_name,
                score.task_id,
                score.evaluator_model,
                score.confidence,
                score.cost_usd,
                score.timestamp.isoformat(),
            ),
        )
        for dim_name, dim_score in score.dimensions.items():
            reasoning = score.reasoning.get(dim_name, "")
            self._conn.execute(
                "INSERT INTO dimension_scores (eval_id, dimension, score, reasoning) VALUES (?, ?, ?, ?)",
                (score.eval_id, dim_name, dim_score, reasoning),
            )
        self._conn.commit()

    async def save_score(self, score: QualityScore) -> None:
        await asyncio.to_thread(self._save_score_sync, score)

    def _get_scores_sync(
        self, agent_name: str, since: datetime, limit: int
    ) -> list[QualityScore]:
        rows = self._conn.execute(
            "SELECT eval_id, agent_name, task_id, evaluator_model, confidence, cost_usd, created_at "
            "FROM evaluations WHERE agent_name = ? AND created_at >= ? "
            "ORDER BY created_at DESC LIMIT ?",
            (agent_name, since.isoformat(), limit),
        ).fetchall()

        results = []
        for row in rows:
            dim_rows = self._conn.execute(
                "SELECT dimension, score, reasoning FROM dimension_scores WHERE eval_id = ?",
                (row["eval_id"],),
            ).fetchall()
            dimensions = {r["dimension"]: r["score"] for r in dim_rows}
            reasoning = {
                r["dimension"]: r["reasoning"]
                for r in dim_rows
                if r["reasoning"]
            }
            results.append(
                QualityScore(
                    eval_id=row["eval_id"],
                    agent_name=row["agent_name"],
                    task_id=row["task_id"],
                    dimensions=dimensions,
                    reasoning=reasoning,
                    confidence=row["confidence"],
                    evaluator_model=row["evaluator_model"],
                    cost_usd=row["cost_usd"],
                    timestamp=datetime.fromisoformat(row["created_at"]),
                )
            )
        return results

    async def get_scores(
        self, agent_name: str, since: datetime, limit: int = 100
    ) -> list[QualityScore]:
        return await asyncio.to_thread(self._get_scores_sync, agent_name, since, limit)

    def _save_override_sync(
        self, eval_id: str, corrected_dimensions: dict[str, float], corrector: str
    ) -> None:
        for dim_name, corrected_score in corrected_dimensions.items():
            row = self._conn.execute(
                "SELECT score FROM dimension_scores WHERE eval_id = ? AND dimension = ?",
                (eval_id, dim_name),
            ).fetchone()
            original_score = row["score"] if row else 0.0
            self._conn.execute(
                "INSERT INTO overrides (override_id, eval_id, dimension, original_score, corrected_score, corrector) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), eval_id, dim_name, original_score, corrected_score, corrector),
            )
        self._conn.commit()

    async def save_override(
        self, eval_id: str, corrected_dimensions: dict[str, float], corrector: str
    ) -> None:
        await asyncio.to_thread(self._save_override_sync, eval_id, corrected_dimensions, corrector)

    def _get_overrides_sync(self, since: datetime, limit: int) -> list[dict]:
        rows = self._conn.execute(
            "SELECT override_id, eval_id, dimension, original_score, corrected_score, corrector, created_at "
            "FROM overrides WHERE created_at >= ? ORDER BY created_at DESC LIMIT ?",
            (since.isoformat(), limit),
        ).fetchall()
        return [dict(r) for r in rows]

    async def get_overrides(self, since: datetime, limit: int = 100) -> list[dict]:
        return await asyncio.to_thread(self._get_overrides_sync, since, limit)

    def _get_autonomy_sync(self, agent_name: str) -> str | None:
        row = self._conn.execute(
            "SELECT level FROM agent_autonomy WHERE agent_name = ?",
            (agent_name,),
        ).fetchone()
        return row["level"] if row else None

    async def get_autonomy(self, agent_name: str) -> str | None:
        return await asyncio.to_thread(self._get_autonomy_sync, agent_name)

    def _set_autonomy_sync(self, agent_name: str, level: str, updated_by: str) -> None:
        current = self._get_autonomy_sync(agent_name)
        from_level = current or "full"

        self._conn.execute(
            "INSERT INTO agent_autonomy (agent_name, level, updated_by) VALUES (?, ?, ?) "
            "ON CONFLICT(agent_name) DO UPDATE SET level = excluded.level, "
            "updated_by = excluded.updated_by, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')",
            (agent_name, level, updated_by),
        )
        self._conn.execute(
            "INSERT INTO governance_log (agent_name, from_level, to_level, reason, triggered_by) "
            "VALUES (?, ?, ?, ?, ?)",
            (agent_name, from_level, level, f"Autonomy changed to {level}", updated_by),
        )
        self._conn.commit()

    async def set_autonomy(self, agent_name: str, level: str, updated_by: str) -> None:
        await asyncio.to_thread(self._set_autonomy_sync, agent_name, level, updated_by)

    def close(self) -> None:
        self._conn.close()
