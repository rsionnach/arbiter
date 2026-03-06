"""Trend tracking — pure arithmetic over stored scores (ZFC: transport, not judgment)."""

from __future__ import annotations

from typing import Protocol

from arbiter.store.protocol import ScoreStore
from arbiter.types import TrendWindow


class TrendTracker(Protocol):
    """Computes aggregate trends over evaluation windows.

    Pure arithmetic — averages, rates, counts. Never interprets
    whether a trend is "good" or "bad" (that's the model's job).
    """

    async def compute_window(self, agent_name: str, window_days: int) -> TrendWindow: ...


class StoreTrendTracker:
    """TrendTracker backed by a ScoreStore."""

    def __init__(self, store: ScoreStore) -> None:
        self._store = store

    async def compute_window(self, agent_name: str, window_days: int) -> TrendWindow:
        raise NotImplementedError
