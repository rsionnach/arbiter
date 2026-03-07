"""Judgment SLO metrics — extends calibration with false accept rate, precision, recall.

All metrics are arithmetic over stored scores and overrides (ZFC: transport).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from arbiter.manifest import JudgmentSLO
from arbiter.store.protocol import ScoreStore


@dataclass(frozen=True)
class JudgmentSLOReport:
    """Full judgment SLO compliance report for one agent."""

    agent_name: str
    window_days: int
    reversal_rate: float
    reversal_rate_target: float | None
    reversal_rate_compliant: bool | None
    false_accept_rate: float
    precision: float
    recall: float
    mae: float
    total_evaluations: int
    total_overrides: int


class JudgmentSLOChecker:
    """Computes judgment SLO compliance from store data."""

    def __init__(self, store: ScoreStore, slo: JudgmentSLO | None = None) -> None:
        self._store = store
        self._slo = slo

    async def check(
        self,
        agent_name: str,
        window_days: int = 30,
        score_threshold: float = 0.5,
    ) -> JudgmentSLOReport:
        since = datetime.now(timezone.utc) - timedelta(days=window_days)

        scores = await self._store.get_scores(agent_name, since=since, limit=100000)
        overrides = await self._store.get_overrides(
            since=since, limit=100000, agent_name=agent_name
        )

        total_evals = len(scores)
        total_overrides = len(overrides)

        # Build lookup: eval_id -> QualityScore
        score_by_id: dict[str, dict[str, float]] = {}
        for s in scores:
            score_by_id[s.eval_id] = s.dimensions

        # Build override groups: eval_id -> list of override dicts
        overrides_by_eval: dict[str, list[dict]] = {}
        for ov in overrides:
            eid = ov["eval_id"]
            overrides_by_eval.setdefault(eid, []).append(ov)

        # Reversal rate: fraction of evals that have any override
        eval_ids_with_overrides = set(overrides_by_eval.keys())
        reversal_rate = (
            len(eval_ids_with_overrides) / total_evals if total_evals > 0 else 0.0
        )

        # False accept rate: of downward overrides, how many had original avg >= threshold?
        downward_eval_ids: set[str] = set()
        for eid, ovs in overrides_by_eval.items():
            for ov in ovs:
                if ov["corrected_score"] < ov["original_score"]:
                    downward_eval_ids.add(eid)
                    break

        false_accepts = 0
        for eid in downward_eval_ids:
            dims = score_by_id.get(eid, {})
            if dims:
                avg = sum(dims.values()) / len(dims)
                if avg >= score_threshold:
                    false_accepts += 1

        false_accept_rate = (
            false_accepts / len(downward_eval_ids)
            if downward_eval_ids
            else 0.0
        )

        # Precision: of evals evaluator scored low (avg < threshold),
        # what fraction had no upward override (human agrees it's low)?
        scored_low_ids: list[str] = []
        for s in scores:
            if s.dimensions:
                avg = sum(s.dimensions.values()) / len(s.dimensions)
                if avg < score_threshold:
                    scored_low_ids.append(s.eval_id)

        if scored_low_ids:
            agreed_low = 0
            for eid in scored_low_ids:
                has_upward = False
                for ov in overrides_by_eval.get(eid, []):
                    if ov["corrected_score"] > ov["original_score"]:
                        has_upward = True
                        break
                if not has_upward:
                    agreed_low += 1
            precision = agreed_low / len(scored_low_ids)
        else:
            precision = 1.0

        # Recall: of evals humans flagged as problematic (downward override),
        # what fraction did evaluator also score < threshold?
        if downward_eval_ids:
            caught = 0
            for eid in downward_eval_ids:
                dims = score_by_id.get(eid, {})
                if dims:
                    avg = sum(dims.values()) / len(dims)
                    if avg < score_threshold:
                        caught += 1
            recall = caught / len(downward_eval_ids)
        else:
            recall = 1.0

        # MAE from overrides
        if overrides:
            mae = sum(
                abs(ov["original_score"] - ov["corrected_score"]) for ov in overrides
            ) / len(overrides)
        else:
            mae = 0.0

        # Windowed compliance
        target = self._slo.reversal_rate_target if self._slo else None
        compliant = reversal_rate <= target if target is not None else None

        return JudgmentSLOReport(
            agent_name=agent_name,
            window_days=window_days,
            reversal_rate=reversal_rate,
            reversal_rate_target=target,
            reversal_rate_compliant=compliant,
            false_accept_rate=false_accept_rate,
            precision=precision,
            recall=recall,
            mae=mae,
            total_evaluations=total_evals,
            total_overrides=total_overrides,
        )
