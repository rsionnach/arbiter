"""Configuration loading for Arbiter."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AgentConfig:
    """Configuration for a monitored agent."""

    name: str
    adapter: str = "webhook"
    dimensions: list[str] | None = None


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
    error_budget_threshold: float = 0.5


@dataclass
class ArbiterConfig:
    """Top-level Arbiter configuration matching arbiter.yaml shape."""

    evaluator: EvaluatorConfig = field(default_factory=EvaluatorConfig)
    store: StoreConfig = field(default_factory=StoreConfig)
    governance: GovernanceConfig = field(default_factory=GovernanceConfig)
    dimensions: list[str] = field(default_factory=lambda: ["correctness", "completeness", "style"])
    agents: list[AgentConfig] = field(default_factory=list)


def load_config(path: Path) -> ArbiterConfig:
    """Load ArbiterConfig from a YAML file."""
    raw = yaml.safe_load(path.read_text())
    if raw is None:
        return ArbiterConfig()

    evaluator = EvaluatorConfig(**raw["evaluator"]) if "evaluator" in raw else EvaluatorConfig()
    store = StoreConfig(**raw["store"]) if "store" in raw else StoreConfig()
    governance = GovernanceConfig(**raw["governance"]) if "governance" in raw else GovernanceConfig()
    dimensions = raw.get("dimensions", ["correctness", "completeness", "style"])

    agents = []
    for agent_data in raw.get("agents", []):
        agents.append(AgentConfig(**agent_data))

    return ArbiterConfig(
        evaluator=evaluator,
        store=store,
        governance=governance,
        dimensions=dimensions,
        agents=agents,
    )
