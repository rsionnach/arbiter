"""Self-calibration loop — measures the Arbiter's own judgment accuracy.

Uses override data (human corrections) to compute how well the evaluator's
scores match ground truth. Pure arithmetic over stored data (ZFC).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from arbiter.store.protocol import ScoreStore


@dataclass(frozen=True)
class CalibrationReport:
    """Results of a calibration run."""

    total_overrides: int
    mean_absolute_error: float
    dimensions_analyzed: list[str]


class CalibrationLoop(Protocol):
    """Computes evaluator accuracy from override history."""

    async def calibrate(self, window_days: int = 30) -> CalibrationReport: ...


class OverrideCalibration:
    """Calibration based on comparing original scores to human overrides."""

    def __init__(self, store: ScoreStore) -> None:
        self._store = store

    async def calibrate(self, window_days: int = 30) -> CalibrationReport:
        raise NotImplementedError
