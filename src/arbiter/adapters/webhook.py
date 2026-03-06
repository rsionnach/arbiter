"""Webhook adapter — accepts HTTP POSTs and yields AgentOutput."""

from __future__ import annotations

from collections.abc import AsyncIterator

from arbiter.types import AgentOutput


class WebhookAdapter:
    """Receives agent output via HTTP webhook POST requests."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        self._host = host
        self._port = port

    def name(self) -> str:
        return "webhook"

    async def receive(self) -> AsyncIterator[AgentOutput]:
        raise NotImplementedError("Webhook adapter not yet implemented")
        yield  # noqa: RET503 — makes this a proper async generator
