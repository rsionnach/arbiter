"""Tests for StoreTrendTracker — window computation with known data."""

import pytest
import pytest_asyncio
from datetime import timedelta, timezone, datetime

from arbiter.store.sqlite import SQLiteScoreStore
from arbiter.trends.tracker import StoreTrendTracker
from arbiter.types import QualityScore


@pytest_asyncio.fixture
async def store(tmp_path):
    s = SQLiteScoreStore(tmp_path / "test.db")
    yield s
    s.close()


@pytest_asyncio.fixture
async def tracker(store):
    return StoreTrendTracker(store)


def _make_score(eval_id: str, dims: dict[str, float], confidence: float = 0.8) -> QualityScore:
    return QualityScore(
        eval_id=eval_id,
        agent_name="agent-a",
        task_id="t1",
        dimensions=dims,
        confidence=confidence,
        evaluator_model="test",
    )


@pytest.mark.asyncio
async def test_empty_window(tracker):
    window = await tracker.compute_window("agent-a", 7)
    assert window.evaluation_count == 0
    assert window.dimension_averages == {}
    assert window.confidence_mean == 0.0


@pytest.mark.asyncio
async def test_single_score_window(store, tracker):
    await store.save_score(_make_score("e1", {"correctness": 0.8, "style": 0.6}, 0.9))

    window = await tracker.compute_window("agent-a", 7)
    assert window.evaluation_count == 1
    assert window.dimension_averages["correctness"] == pytest.approx(0.8)
    assert window.dimension_averages["style"] == pytest.approx(0.6)
    assert window.confidence_mean == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_multiple_scores_averaged(store, tracker):
    await store.save_score(_make_score("e1", {"correctness": 0.8}, 0.9))
    await store.save_score(_make_score("e2", {"correctness": 0.6}, 0.7))

    window = await tracker.compute_window("agent-a", 7)
    assert window.evaluation_count == 2
    assert window.dimension_averages["correctness"] == pytest.approx(0.7)
    assert window.confidence_mean == pytest.approx(0.8)
