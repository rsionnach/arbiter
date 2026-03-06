"""Tests for ErrorBudgetGovernance — reduction + safety ratchet enforcement."""

import pytest
import pytest_asyncio

from arbiter.store.sqlite import SQLiteScoreStore
from arbiter.governance.engine import ErrorBudgetGovernance
from arbiter.trends.tracker import StoreTrendTracker
from arbiter.types import AutonomyLevel, QualityScore


@pytest_asyncio.fixture
async def store(tmp_path):
    s = SQLiteScoreStore(tmp_path / "test.db")
    yield s
    s.close()


@pytest_asyncio.fixture
async def governance(store):
    tracker = StoreTrendTracker(store)
    return ErrorBudgetGovernance(store=store, tracker=tracker, threshold=0.5)


def _make_score(eval_id: str, dims: dict[str, float]) -> QualityScore:
    return QualityScore(
        eval_id=eval_id,
        agent_name="agent-a",
        task_id="t1",
        dimensions=dims,
        confidence=0.8,
        evaluator_model="test",
    )


@pytest.mark.asyncio
async def test_no_scores_no_action(governance):
    action = await governance.check_agent("agent-a")
    assert action is None


@pytest.mark.asyncio
async def test_good_scores_no_action(store, governance):
    await store.save_score(_make_score("e1", {"correctness": 0.9}))
    action = await governance.check_agent("agent-a")
    assert action is None


@pytest.mark.asyncio
async def test_low_score_triggers_reduction(store, governance):
    await store.save_score(_make_score("e1", {"correctness": 0.3}))

    action = await governance.check_agent("agent-a")
    assert action is not None
    assert action.action_type == AutonomyLevel.SUPERVISED
    assert "correctness" in action.reason


@pytest.mark.asyncio
async def test_default_autonomy_is_full(governance):
    level = await governance.get_autonomy("unknown")
    assert level == AutonomyLevel.FULL


@pytest.mark.asyncio
async def test_safety_ratchet_requires_approver(governance):
    with pytest.raises(ValueError, match="approver"):
        await governance.restore_autonomy("agent-a", AutonomyLevel.FULL, "")


@pytest.mark.asyncio
async def test_restore_autonomy_with_approver(store, governance):
    await store.set_autonomy("agent-a", "supervised", "governance")
    await governance.restore_autonomy("agent-a", AutonomyLevel.FULL, "human-admin")
    level = await governance.get_autonomy("agent-a")
    assert level == AutonomyLevel.FULL


@pytest.mark.asyncio
async def test_reduction_ladder(governance):
    assert ErrorBudgetGovernance._reduce_level(AutonomyLevel.FULL) == AutonomyLevel.SUPERVISED
    assert ErrorBudgetGovernance._reduce_level(AutonomyLevel.SUPERVISED) == AutonomyLevel.ADVISORY_ONLY
    assert ErrorBudgetGovernance._reduce_level(AutonomyLevel.ADVISORY_ONLY) == AutonomyLevel.SUSPENDED
    assert ErrorBudgetGovernance._reduce_level(AutonomyLevel.SUSPENDED) == AutonomyLevel.SUSPENDED
