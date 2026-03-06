"""Pipeline router — connects adapters to evaluators to stores."""

from __future__ import annotations

from arbiter.adapters.protocol import Adapter
from arbiter.pipeline.evaluator import Evaluator
from arbiter.store.protocol import ScoreStore
from arbiter.trends.tracker import TrendTracker


class PipelineRouter:
    """Routes agent output through the evaluation pipeline.

    Flow: adapter.receive() -> evaluator.evaluate() -> store.save_score() -> tracker
    """

    def __init__(
        self,
        adapter: Adapter,
        evaluator: Evaluator,
        store: ScoreStore,
        tracker: TrendTracker,
        dimensions: list[str],
    ) -> None:
        self._adapter = adapter
        self._evaluator = evaluator
        self._store = store
        self._tracker = tracker
        self._dimensions = dimensions

    async def run(self) -> None:
        """Process agent outputs through the full pipeline."""
        async for output in self._adapter.receive():
            score = await self._evaluator.evaluate(output, self._dimensions)
            await self._store.save_score(score)
