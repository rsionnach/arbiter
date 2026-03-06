"""Tests for Arbiter data types."""

import pytest
from arbiter.types import (
    AgentOutput,
    AutonomyLevel,
    DimensionScore,
    GovernanceAction,
    QualityScore,
    TrendWindow,
)


def test_quality_score_construction():
    score = QualityScore(
        eval_id="e1",
        agent_name="agent-a",
        task_id="t1",
        dimensions={"correctness": 0.9, "style": 0.7},
        reasoning={"correctness": "Mostly correct", "style": "Needs work"},
        confidence=0.85,
        evaluator_model="test-model",
    )
    assert score.dimensions["correctness"] == 0.9
    assert score.reasoning["style"] == "Needs work"
    assert score.confidence == 0.85


def test_quality_score_reasoning_defaults_empty():
    score = QualityScore(
        eval_id="e2",
        agent_name="agent-a",
        task_id="t2",
        dimensions={"correctness": 0.5},
    )
    assert score.reasoning == {}
    assert score.confidence == 0.0
    assert score.evaluator_model == ""


def test_quality_score_frozen():
    score = QualityScore(
        eval_id="e3",
        agent_name="agent-a",
        task_id="t3",
        dimensions={"x": 1.0},
    )
    with pytest.raises(AttributeError):
        score.eval_id = "changed"  # type: ignore[misc]


def test_agent_output_construction():
    output = AgentOutput(
        agent_name="bot",
        task_id="t1",
        output_content="hello",
        output_type="text",
    )
    assert output.agent_name == "bot"
    assert output.metadata == {}


def test_autonomy_level_values():
    assert AutonomyLevel.FULL.value == "full"
    assert AutonomyLevel.SUSPENDED.value == "suspended"


def test_trend_window_construction():
    tw = TrendWindow(
        agent_name="a",
        window_days=7,
        dimension_averages={"x": 0.5},
        evaluation_count=10,
        confidence_mean=0.8,
    )
    assert tw.evaluation_count == 10


def test_dimension_score_construction():
    ds = DimensionScore(name="correctness", score=0.95, reasoning="Looks good")
    assert ds.score == 0.95


def test_governance_action_construction():
    ga = GovernanceAction(
        agent_name="bot",
        action_type=AutonomyLevel.SUPERVISED,
        reason="Score dropped",
    )
    assert ga.action_type == AutonomyLevel.SUPERVISED
