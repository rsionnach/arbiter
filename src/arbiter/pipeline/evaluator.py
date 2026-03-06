"""Evaluator protocol and skeleton — the boundary between transport and judgment."""

from __future__ import annotations

from typing import Protocol

from arbiter.types import AgentOutput, QualityScore


class Evaluator(Protocol):
    """Evaluates agent output across quality dimensions.

    The evaluator is the boundary where transport hands off to judgment.
    It constructs the prompt, calls the model, and parses the response.
    It never interprets quality itself — that's the model's job (ZFC).
    """

    async def evaluate(self, output: AgentOutput, dimensions: list[str]) -> QualityScore: ...


class ModelEvaluator:
    """Evaluator that delegates quality judgment to a language model.

    Constructs evaluation prompts, sends to model, parses structured
    responses back into QualityScore. All judgment lives in the prompt,
    not in this code.
    """

    def __init__(self, model: str, max_tokens: int = 4096) -> None:
        self._model = model
        self._max_tokens = max_tokens

    async def evaluate(self, output: AgentOutput, dimensions: list[str]) -> QualityScore:
        raise NotImplementedError("Model evaluator not yet implemented")
