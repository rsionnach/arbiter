"""Configuration loading for Arbiter."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class EvaluatorConfig:
    """Configuration for the evaluation model."""

    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    temperature: float = 0.0


@dataclass
class StoreConfig:
    """Configuration for the score store."""

    backend: str = "sqlite"
    path: str = "arbiter.db"


@dataclass
class GovernanceConfig:
    """Configuration for the governance engine."""

    error_budget_window_days: int = 7
    error_budget_threshold: float = 0.1


@dataclass
class ArbiterConfig:
    """Top-level Arbiter configuration matching arbiter.yaml shape."""

    evaluator: EvaluatorConfig = field(default_factory=EvaluatorConfig)
    store: StoreConfig = field(default_factory=StoreConfig)
    governance: GovernanceConfig = field(default_factory=GovernanceConfig)
    dimensions: list[str] = field(default_factory=lambda: ["correctness", "completeness", "style"])


def load_config(path: Path) -> ArbiterConfig:
    """Load ArbiterConfig from a YAML file.

    Requires PyYAML — will be added as a dependency when config loading
    is implemented beyond the scaffold.
    """
    raise NotImplementedError("YAML config loading not yet implemented")
