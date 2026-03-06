"""Governance engine — watches error budgets, manages agent autonomy.

Key constraint: can REDUCE autonomy, never increase without human approval
(one-way safety ratchet). Acts on model decisions, never makes its own
quality judgments (ZFC).
"""

from __future__ import annotations

from typing import Protocol

from arbiter.store.protocol import ScoreStore
from arbiter.trends.tracker import TrendTracker
from arbiter.types import AutonomyLevel, GovernanceAction


class GovernanceEngine(Protocol):
    """Manages agent autonomy levels based on evaluation trends."""

    async def check_agent(self, agent_name: str) -> GovernanceAction | None: ...

    async def get_autonomy(self, agent_name: str) -> AutonomyLevel: ...

    async def restore_autonomy(self, agent_name: str, level: AutonomyLevel, approver: str) -> None:
        """Restore autonomy — requires human approver (safety ratchet)."""
        ...


class ErrorBudgetGovernance:
    """Governance based on error budget consumption over a rolling window."""

    def __init__(
        self,
        store: ScoreStore,
        tracker: TrendTracker,
        window_days: int = 7,
        threshold: float = 0.5,
    ) -> None:
        self._store = store
        self._tracker = tracker
        self._window_days = window_days
        self._threshold = threshold

    async def check_agent(self, agent_name: str) -> GovernanceAction | None:
        trend = await self._tracker.compute_window(self._agent_name_str(agent_name), self._window_days)

        if trend.evaluation_count == 0:
            return None

        for dim_name, avg in trend.dimension_averages.items():
            if avg < self._threshold:
                current = await self.get_autonomy(agent_name)
                reduced = self._reduce_level(current)
                if reduced != current:
                    await self._store.set_autonomy(
                        agent_name, reduced.value, "governance:error_budget"
                    )
                    return GovernanceAction(
                        agent_name=agent_name,
                        action_type=reduced,
                        reason=f"Dimension '{dim_name}' average {avg:.2f} below threshold {self._threshold:.2f}",
                    )

        return None

    async def get_autonomy(self, agent_name: str) -> AutonomyLevel:
        level_str = await self._store.get_autonomy(agent_name)
        if level_str is None:
            return AutonomyLevel.FULL
        return AutonomyLevel(level_str)

    async def restore_autonomy(
        self, agent_name: str, level: AutonomyLevel, approver: str
    ) -> None:
        if not approver:
            raise ValueError("Safety ratchet: approver is required to restore autonomy")
        await self._store.set_autonomy(agent_name, level.value, approver)

    @staticmethod
    def _reduce_level(current: AutonomyLevel) -> AutonomyLevel:
        """One step down the autonomy ladder."""
        reduction = {
            AutonomyLevel.FULL: AutonomyLevel.SUPERVISED,
            AutonomyLevel.SUPERVISED: AutonomyLevel.ADVISORY_ONLY,
            AutonomyLevel.ADVISORY_ONLY: AutonomyLevel.SUSPENDED,
            AutonomyLevel.SUSPENDED: AutonomyLevel.SUSPENDED,
        }
        return reduction[current]

    @staticmethod
    def _agent_name_str(agent_name: str) -> str:
        return agent_name
