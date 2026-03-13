"""Tests for Arbiter / Verdict integration (Phase 1)."""

from __future__ import annotations

import textwrap
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from arbiter.config import ArbiterConfig, VerdictConfig, load_config
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
