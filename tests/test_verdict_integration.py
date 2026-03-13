"""Tests for Arbiter / Verdict integration (Phase 1)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from arbiter.config import ArbiterConfig, VerdictConfig, load_config


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
