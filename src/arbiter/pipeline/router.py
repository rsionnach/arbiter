"""Pipeline router — connects adapters to evaluators to stores."""

from __future__ import annotations

from arbiter.adapters.protocol import Adapter
from arbiter.governance.engine import GovernanceEngine
from arbiter.pipeline.evaluator import Evaluator
from arbiter.store.protocol import ScoreStore
from arbiter.trends.tracker import TrendTracker


class PipelineRouter:
    """Routes agent output through the evaluation pipeline.

    Flow: adapter.receive() -> evaluator.evaluate() -> store.save_score()
          -> governance.check_agent() -> (optional autonomy change)
    """

    def __init__(
        self,
        adapter: Adapter,
        evaluator: Evaluator,
        store: ScoreStore,
        tracker: TrendTracker,
        dimensions: list[str],
        governance: GovernanceEngine | None = None,
    ) -> None:
        self._adapter = adapter
        self._evaluator = evaluator
        self._store = store
        self._tracker = tracker
        self._dimensions = dimensions
        self._governance = governance

    async def run(self) -> None:
        """Process agent outputs through the full pipeline."""
        async for output in self._adapter.receive():
            score = await self._evaluator.evaluate(output, self._dimensions)
            await self._store.save_score(score)

            if self._governance is not None:
                action = await self._governance.check_agent(output.agent_name)
                if action is not None:
                    await self._store.set_autonomy(
                        output.agent_name,
                        action.action_type.value,
                        "governance:pipeline",
                    )
