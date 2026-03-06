"""CLI entry point for Arbiter."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from arbiter.adapters.webhook import WebhookAdapter
from arbiter.config import load_config
from arbiter.governance.engine import ErrorBudgetGovernance
from arbiter.pipeline.evaluator import ModelEvaluator
from arbiter.pipeline.router import PipelineRouter
from arbiter.store.sqlite import SQLiteScoreStore
from arbiter.trends.tracker import StoreTrendTracker


def build_pipeline(config_path: Path) -> PipelineRouter:
    """Wire all components from config into a pipeline."""
    config = load_config(config_path)

    store = SQLiteScoreStore(config.store.path)
    tracker = StoreTrendTracker(store)
    evaluator = ModelEvaluator(
        model=config.evaluator.model,
        max_tokens=config.evaluator.max_tokens,
    )
    governance = ErrorBudgetGovernance(
        store=store,
        tracker=tracker,
        window_days=config.governance.error_budget_window_days,
        threshold=config.governance.error_budget_threshold,
    )
    adapter = WebhookAdapter()

    return PipelineRouter(
        adapter=adapter,
        evaluator=evaluator,
        store=store,
        tracker=tracker,
        dimensions=config.dimensions,
        governance=governance,
    )


def main() -> None:
    """Entry point: load config, wire components, run pipeline."""
    parser = argparse.ArgumentParser(description="Arbiter — AI agent quality measurement")
    parser.add_argument(
        "-c", "--config",
        type=Path,
        default=Path("arbiter.yaml"),
        help="Path to arbiter.yaml config file",
    )
    args = parser.parse_args()

    if not args.config.exists():
        print(f"Config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    router = build_pipeline(args.config)
    asyncio.run(router.run())


if __name__ == "__main__":
    main()
