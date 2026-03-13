"""Tests for Arbiter / Verdict integration (Phase 1)."""

from __future__ import annotations

import asyncio
import textwrap
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from verdict import SQLiteVerdictStore, AccuracyFilter, VerdictFilter, create as verdict_create

from arbiter.config import ArbiterConfig, VerdictConfig, load_config
from arbiter.pipeline.router import DEFAULT_APPROVE_THRESHOLD, PipelineRouter
from arbiter.store.sqlite import SQLiteScoreStore
from arbiter.types import QualityScore


class TestVerdictConfig:
    """Tests for VerdictConfig dataclass and config loading."""

    def test_verdict_config_defaults(self):
        vc = VerdictConfig()
        assert vc.store_path == "verdicts.db"

    def test_verdict_config_custom_path(self):
        vc = VerdictConfig(store_path="/tmp/custom.db")
        assert vc.store_path == "/tmp/custom.db"

    def test_arbiter_config_verdict_none_by_default(self):
        config = ArbiterConfig()
        assert config.verdict is None

    def test_load_config_without_verdict_section(self, tmp_path):
        cfg_file = tmp_path / "arbiter.yaml"
        cfg_file.write_text(textwrap.dedent("""\
            evaluator:
              model: test-model
        """))
        config = load_config(cfg_file)
        assert config.verdict is None

    def test_load_config_with_verdict_section(self, tmp_path):
        cfg_file = tmp_path / "arbiter.yaml"
        cfg_file.write_text(textwrap.dedent("""\
            evaluator:
              model: test-model
            verdict:
              store:
                path: custom-verdicts.db
        """))
        config = load_config(cfg_file)
        assert config.verdict is not None
        assert config.verdict.store_path == "custom-verdicts.db"

    def test_load_config_with_verdict_section_defaults(self, tmp_path):
        cfg_file = tmp_path / "arbiter.yaml"
        cfg_file.write_text(textwrap.dedent("""\
            evaluator:
              model: test-model
            verdict:
              store: {}
        """))
        config = load_config(cfg_file)
        assert config.verdict is not None
        assert config.verdict.store_path == "verdicts.db"


def _make_score(eval_id: str = "e1", agent: str = "agent-a", task: str = "t1", **kwargs) -> QualityScore:
    return QualityScore(
        eval_id=eval_id,
        agent_name=agent,
        task_id=task,
        dimensions=kwargs.get("dimensions", {"correctness": 0.9, "style": 0.7}),
        reasoning=kwargs.get("reasoning", {"correctness": "Good", "style": "OK"}),
        confidence=kwargs.get("confidence", 0.85),
        evaluator_model=kwargs.get("evaluator_model", "test-model"),
        cost_usd=kwargs.get("cost_usd", 0.01),
    )


class TestSchemaMigration:
    """Tests for verdict_id column migration and set_verdict_id."""

    @pytest_asyncio.fixture
    async def store(self, tmp_path):
        s = SQLiteScoreStore(tmp_path / "test.db")
        yield s
        s.close()

    @pytest.mark.asyncio
    async def test_verdict_id_column_exists_after_init(self, store):
        """The evaluations table should have a verdict_id column after init."""
        with store._lock:
            row = store._conn.execute(
                "PRAGMA table_info(evaluations)"
            ).fetchall()
        col_names = [r["name"] for r in row]
        assert "verdict_id" in col_names

    @pytest.mark.asyncio
    async def test_verdict_id_null_by_default(self, store):
        """New evaluations should have verdict_id = NULL."""
        await store.save_score(_make_score())
        with store._lock:
            row = store._conn.execute(
                "SELECT verdict_id FROM evaluations WHERE eval_id = ?", ("e1",)
            ).fetchone()
        assert row["verdict_id"] is None

    @pytest.mark.asyncio
    async def test_set_verdict_id(self, store):
        """set_verdict_id should update the verdict_id for a given eval_id."""
        await store.save_score(_make_score())
        await store.set_verdict_id("e1", "vrd-2026-03-13-abcd1234-00001")
        with store._lock:
            row = store._conn.execute(
                "SELECT verdict_id FROM evaluations WHERE eval_id = ?", ("e1",)
            ).fetchone()
        assert row["verdict_id"] == "vrd-2026-03-13-abcd1234-00001"

    @pytest.mark.asyncio
    async def test_set_verdict_id_unknown_raises(self, store):
        """set_verdict_id on non-existent eval_id should raise ValueError."""
        with pytest.raises(ValueError, match="non-existent"):
            await store.set_verdict_id("no-such-id", "vrd-xxx")

    @pytest.mark.asyncio
    async def test_migration_idempotent(self, tmp_path):
        """Creating SQLiteScoreStore twice on the same DB should not crash."""
        db = tmp_path / "test.db"
        s1 = SQLiteScoreStore(db)
        s1.close()
        s2 = SQLiteScoreStore(db)
        s2.close()
        # No exception means migration is idempotent


class TestVerdictEmission:
    """Tests for verdict creation in PipelineRouter."""

    @pytest_asyncio.fixture
    async def verdict_store(self, tmp_path):
        vs = SQLiteVerdictStore(str(tmp_path / "verdicts.db"))
        yield vs
        vs.close()

    @pytest_asyncio.fixture
    async def score_store(self, tmp_path):
        s = SQLiteScoreStore(tmp_path / "score.db")
        yield s
        s.close()

    def _make_pipeline(self, score_store, verdict_store=None, threshold=None):
        """Build a PipelineRouter with mock adapter/evaluator for testing."""
        adapter = AsyncMock()
        evaluator_mock = AsyncMock()
        tracker = AsyncMock()
        tracker.compute_window = AsyncMock()

        return PipelineRouter(
            adapter=adapter,
            evaluator=evaluator_mock,
            store=score_store,
            tracker=tracker,
            dimensions=["correctness", "style"],
            verdict_store=verdict_store,
            approve_threshold=threshold,
        )

    async def _run_single(self, router, score):
        """Configure adapter to yield one output, evaluator to return score, run pipeline."""
        output = MagicMock()
        output.agent_name = score.agent_name

        async def _receive():
            yield output

        router._adapter.receive = _receive
        router._evaluator.evaluate = AsyncMock(return_value=score)
        await router.run()

    @pytest.mark.asyncio
    async def test_verdict_created_after_scoring(self, score_store, verdict_store):
        router = self._make_pipeline(score_store, verdict_store)
        score = _make_score(dimensions={"correctness": 0.8, "style": 0.6})
        await self._run_single(router, score)

        # Verdict should be in verdict store
        verdicts = verdict_store.query(VerdictFilter(producer_system="arbiter", limit=10))
        assert len(verdicts) == 1
        v = verdicts[0]
        assert v.subject.type == "agent_output"
        assert v.subject.ref == "t1"
        assert v.subject.agent == "agent-a"
        assert v.judgment.action == "approve"  # avg 0.7 >= 0.5
        assert v.judgment.confidence == pytest.approx(0.85)
        assert v.judgment.score == pytest.approx(0.7)
        assert v.judgment.dimensions == {"correctness": 0.8, "style": 0.6}
        assert v.subject.summary == "Evaluation of agent-a: t1"
        assert v.producer.system == "arbiter"
        assert v.producer.model == "test-model"
        assert v.metadata.cost_currency == pytest.approx(0.01)

    @pytest.mark.asyncio
    async def test_verdict_id_written_to_evaluations(self, score_store, verdict_store):
        router = self._make_pipeline(score_store, verdict_store)
        score = _make_score()
        await self._run_single(router, score)

        # verdict_id should be set on the evaluations row
        with score_store._lock:
            row = score_store._conn.execute(
                "SELECT verdict_id FROM evaluations WHERE eval_id = ?", ("e1",)
            ).fetchone()
        assert row["verdict_id"] is not None
        assert row["verdict_id"].startswith("vrd-")

    @pytest.mark.asyncio
    async def test_approve_threshold_boundary_approve(self, score_store, verdict_store):
        """Score exactly at threshold -> approve."""
        router = self._make_pipeline(score_store, verdict_store)
        score = _make_score(dimensions={"d1": 0.5})
        await self._run_single(router, score)

        verdicts = verdict_store.query(VerdictFilter(producer_system="arbiter", limit=10))
        assert verdicts[0].judgment.action == "approve"

    @pytest.mark.asyncio
    async def test_approve_threshold_boundary_reject(self, score_store, verdict_store):
        """Score just below threshold -> reject."""
        router = self._make_pipeline(score_store, verdict_store)
        score = _make_score(dimensions={"d1": 0.49})
        await self._run_single(router, score)

        verdicts = verdict_store.query(VerdictFilter(producer_system="arbiter", limit=10))
        assert verdicts[0].judgment.action == "reject"

    @pytest.mark.asyncio
    async def test_custom_threshold(self, score_store, verdict_store):
        """Custom approve_threshold should be respected."""
        router = self._make_pipeline(score_store, verdict_store, threshold=0.8)
        score = _make_score(dimensions={"d1": 0.75})
        await self._run_single(router, score)

        verdicts = verdict_store.query(VerdictFilter(producer_system="arbiter", limit=10))
        assert verdicts[0].judgment.action == "reject"  # 0.75 < 0.8

    @pytest.mark.asyncio
    async def test_no_verdict_when_store_is_none(self, score_store):
        """When verdict_store is None, pipeline works without creating verdicts."""
        router = self._make_pipeline(score_store, verdict_store=None)
        score = _make_score()
        await self._run_single(router, score)

        # Score still saved
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        results = await score_store.get_scores("agent-a", since)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_verdict_reasoning_formatted(self, score_store, verdict_store):
        """Reasoning dict should be formatted as semicolon-separated string."""
        router = self._make_pipeline(score_store, verdict_store)
        score = _make_score(
            reasoning={"correctness": "Looks good", "style": "Needs work"}
        )
        await self._run_single(router, score)

        verdicts = verdict_store.query(VerdictFilter(producer_system="arbiter", limit=10))
        reasoning = verdicts[0].judgment.reasoning
        assert "correctness: Looks good" in reasoning
        assert "style: Needs work" in reasoning

    @pytest.mark.asyncio
    async def test_default_approve_threshold_value(self):
        assert DEFAULT_APPROVE_THRESHOLD == 0.5


class TestOverrideResolution:
    """Tests for override to verdict resolution in SQLiteScoreStore."""

    @pytest_asyncio.fixture
    async def verdict_store(self, tmp_path):
        vs = SQLiteVerdictStore(str(tmp_path / "verdicts.db"))
        yield vs
        vs.close()

    @pytest_asyncio.fixture
    async def score_store(self, tmp_path, verdict_store):
        s = SQLiteScoreStore(tmp_path / "score.db", verdict_store=verdict_store)
        yield s
        s.close()

    @pytest.mark.asyncio
    async def test_override_resolves_verdict(self, score_store, verdict_store):
        """Override should resolve the linked verdict as overridden."""
        # Save score
        await score_store.save_score(_make_score())

        # Create and store verdict, link it
        verdict = await asyncio.to_thread(
            verdict_create,
            subject={"type": "agent_output", "ref": "t1", "agent": "agent-a",
                     "summary": "Test evaluation"},
            judgment={"action": "approve", "confidence": 0.85, "score": 0.8},
            producer={"system": "arbiter", "model": "test-model"},
        )
        await asyncio.to_thread(verdict_store.put, verdict)
        await score_store.set_verdict_id("e1", verdict.id)

        # Override
        await score_store.save_override("e1", {"correctness": 0.3}, "human-reviewer")

        # Verdict should be resolved
        resolved = verdict_store.get(verdict.id)
        assert resolved.outcome.status == "overridden"
        assert resolved.outcome.override.by == "human-reviewer"

    @pytest.mark.asyncio
    async def test_override_without_verdict_id_still_works(self, score_store):
        """Override on pre-integration data (no verdict_id) should work normally."""
        await score_store.save_score(_make_score())
        # No verdict_id set — simulates pre-integration data
        await score_store.save_override("e1", {"correctness": 0.3}, "reviewer")

        since = datetime.now(timezone.utc) - timedelta(hours=1)
        overrides = await score_store.get_overrides(since)
        assert len(overrides) == 1

    @pytest.mark.asyncio
    async def test_score_store_without_verdict_store(self, tmp_path):
        """SQLiteScoreStore without verdict_store should work identically to before."""
        s = SQLiteScoreStore(tmp_path / "test.db")
        try:
            await s.save_score(_make_score())
            await s.save_override("e1", {"correctness": 0.3}, "reviewer")
            since = datetime.now(timezone.utc) - timedelta(hours=1)
            overrides = await s.get_overrides(since)
            assert len(overrides) == 1
        finally:
            s.close()
