"""ScoreStore protocol — persistence boundary for evaluation results."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from arbiter.types import QualityScore


class ScoreStore(Protocol):
    """Persists and retrieves evaluation scores.

    The store is pure transport — it saves and loads data,
    never interprets or transforms scores.
    """

    async def save_score(self, score: QualityScore) -> None: ...

    async def get_scores(
        self, agent_name: str, since: datetime, limit: int = 100
    ) -> list[QualityScore]: ...

    async def save_override(
        self, eval_id: str, corrected_dimensions: dict[str, float], corrector: str
    ) -> None: ...
