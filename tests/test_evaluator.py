"""Tests for ModelEvaluator — prompt construction + response parsing."""

import json

import pytest

from arbiter.pipeline.evaluator import ModelEvaluator
from arbiter.types import AgentOutput


@pytest.fixture
def evaluator():
    return ModelEvaluator(model="test-model", max_tokens=2048)


@pytest.fixture
def sample_output():
    return AgentOutput(
        agent_name="agent-a",
        task_id="task-1",
        output_content="def hello(): return 'world'",
        output_type="code",
    )


def test_build_prompt_contains_dimensions(evaluator, sample_output):
    prompt = evaluator.build_prompt(sample_output, ["correctness", "style"])
    assert "correctness" in prompt
    assert "style" in prompt
    assert "agent-a" in prompt
    assert "task-1" in prompt
    assert "def hello()" in prompt


def test_build_prompt_contains_response_format(evaluator, sample_output):
    prompt = evaluator.build_prompt(sample_output, ["correctness"])
    assert '"dimensions"' in prompt
    assert '"confidence"' in prompt
    assert "JSON" in prompt


def test_parse_response_valid_json(evaluator, sample_output):
    response = json.dumps({
        "dimensions": {
            "correctness": {"score": 0.9, "reasoning": "Mostly correct"},
            "style": {"score": 0.7, "reasoning": "Could improve"},
        },
        "confidence": 0.85,
    })

    score = evaluator.parse_response(response, sample_output)
    assert score.agent_name == "agent-a"
    assert score.task_id == "task-1"
    assert score.dimensions["correctness"] == pytest.approx(0.9)
    assert score.dimensions["style"] == pytest.approx(0.7)
    assert score.reasoning["correctness"] == "Mostly correct"
    assert score.confidence == pytest.approx(0.85)
    assert score.evaluator_model == "test-model"


def test_parse_response_strips_code_fences(evaluator, sample_output):
    response = "```json\n" + json.dumps({
        "dimensions": {"x": {"score": 0.5, "reasoning": "r"}},
        "confidence": 0.6,
    }) + "\n```"

    score = evaluator.parse_response(response, sample_output)
    assert score.dimensions["x"] == pytest.approx(0.5)


def test_parse_response_invalid_json(evaluator, sample_output):
    with pytest.raises(json.JSONDecodeError):
        evaluator.parse_response("not json", sample_output)


@pytest.mark.asyncio
async def test_call_model_raises(evaluator, sample_output):
    with pytest.raises(NotImplementedError):
        await evaluator.evaluate(sample_output, ["correctness"])
