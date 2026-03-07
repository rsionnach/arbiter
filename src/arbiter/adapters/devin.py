"""Devin adapter — polls Devin REST API for completed sessions.

Pure transport: translates Devin session format into AgentOutput (ZFC).
Uses httpx (transitive dep via anthropic SDK) with lazy import.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import AsyncIterator

from arbiter.types import AgentOutput


class DevinAdapter:
    """Polls Devin API for completed sessions and yields AgentOutput."""

    def __init__(
        self,
        api_key: str | None = None,
        api_key_env: str = "DEVIN_API_KEY",
        poll_interval: float = 30.0,
        base_url: str = "https://api.devin.ai",
    ) -> None:
        self._api_key = api_key or os.environ.get(api_key_env, "")
        self._poll_interval = poll_interval
        self._base_url = base_url.rstrip("/")
        self._seen: set[str] = set()

    def name(self) -> str:
        return "devin"

    async def receive(self) -> AsyncIterator[AgentOutput]:
        """Poll Devin API for completed sessions."""
        while True:
            sessions = await self._list_sessions()
            for session in sessions:
                sid = session.get("session_id", "")
                if sid and sid not in self._seen and self._is_complete(session):
                    self._seen.add(sid)
                    detail = await self._get_session(sid)
                    yield self._to_agent_output(detail)
            await asyncio.sleep(self._poll_interval)

    async def _list_sessions(self) -> list[dict]:
        """GET /v1/sessions."""
        import httpx

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self._base_url}/v1/sessions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("sessions", data if isinstance(data, list) else [])
            except (httpx.HTTPError, Exception):
                return []

    async def _get_session(self, session_id: str) -> dict:
        """GET /v1/sessions/{id}."""
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/v1/sessions/{session_id}",
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def _is_complete(session: dict) -> bool:
        return session.get("status") in ("completed", "stopped", "failed")

    @staticmethod
    def _to_agent_output(session: dict) -> AgentOutput:
        """Convert Devin session to AgentOutput. Pure transport."""
        structured = session.get("structured_output")
        content = (
            json.dumps(structured) if structured else session.get("title", "")
        )
        return AgentOutput(
            agent_name=f"devin:{session.get('session_id', '')}",
            task_id=session.get("session_id", ""),
            output_content=content,
            output_type="devin-session",
            metadata={
                "status": session.get("status", ""),
                "created_at": session.get("created_at", ""),
            },
        )
