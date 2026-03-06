"""Governance engine — watches error budgets, manages agent autonomy.

Key constraint: can REDUCE autonomy, never increase without human approval
(one-way safety ratchet). Acts on model decisions, never makes its own
quality judgments (ZFC).
"""

from __future__ import annotations

from typing import Protocol

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

    def __init__(self, window_days: int = 7, threshold: float = 0.1) -> None:
        self._window_days = window_days
        self._threshold = threshold

    async def check_agent(self, agent_name: str) -> GovernanceAction | None:
        raise NotImplementedError

    async def get_autonomy(self, agent_name: str) -> AutonomyLevel:
        raise NotImplementedError

    async def restore_autonomy(self, agent_name: str, level: AutonomyLevel, approver: str) -> None:
        raise NotImplementedError
