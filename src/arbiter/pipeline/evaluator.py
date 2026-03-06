"""Evaluator protocol and implementation — the boundary between transport and judgment."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
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

    def build_prompt(self, output: AgentOutput, dimensions: list[str]) -> str:
        """Construct the evaluation prompt. This IS the deliverable — prompt engineering."""
        dimensions_block = "\n".join(f"- {d}" for d in dimensions)
        return f"""You are an evaluation judge. Score the following agent output on each dimension.

## Agent Output
- Agent: {output.agent_name}
- Task: {output.task_id}
- Type: {output.output_type}

### Content
{output.output_content}

## Dimensions to Score
{dimensions_block}

## Instructions
For each dimension, provide:
1. A score from 0.0 to 1.0
2. Brief reasoning for your score

Also provide an overall confidence score (0.0 to 1.0) representing how confident you are in your evaluation.

## Response Format
Respond with valid JSON only:
{{
  "dimensions": {{
    "<dimension_name>": {{"score": <float>, "reasoning": "<string>"}},
    ...
  }},
  "confidence": <float>
}}"""

    def parse_response(self, raw: str, output: AgentOutput) -> QualityScore:
        """Parse model response JSON into a QualityScore. Pure transport."""
        # Strip markdown code fences if present
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last fence lines
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        data = json.loads(text)
        dimensions: dict[str, float] = {}
        reasoning: dict[str, str] = {}

        for dim_name, dim_data in data["dimensions"].items():
            dimensions[dim_name] = float(dim_data["score"])
            if "reasoning" in dim_data:
                reasoning[dim_name] = dim_data["reasoning"]

        return QualityScore(
            eval_id=str(uuid.uuid4()),
            agent_name=output.agent_name,
            task_id=output.task_id,
            dimensions=dimensions,
            reasoning=reasoning,
            confidence=float(data["confidence"]),
            evaluator_model=self._model,
        )

    async def _call_model(self, prompt: str) -> str:
        """Call the language model. Not implemented — no SDK dependency yet."""
        raise NotImplementedError(
            "Model calling requires an SDK dependency (e.g. anthropic). "
            "Inject a callable or subclass this method."
        )

    async def evaluate(self, output: AgentOutput, dimensions: list[str]) -> QualityScore:
        prompt = self.build_prompt(output, dimensions)
        raw_response = await self._call_model(prompt)
        return self.parse_response(raw_response, output)
