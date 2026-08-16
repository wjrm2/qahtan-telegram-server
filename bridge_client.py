"""Secure pull bridge between Az bot and the permanent control dashboard."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Awaitable, Callable

import requests

logger = logging.getLogger(__name__)

BridgeHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class AzControlBridge:
    def __init__(self, handler: BridgeHandler):
        self.base_url = os.environ.get("AZ_CONTROL_API_URL", "").rstrip("/")
        self.token = os.environ.get("AZ_CONTROL_BRIDGE_TOKEN", "").strip()
        self.interval = max(5, int(os.environ.get("AZ_CONTROL_POLL_SECONDS", "10")))
        self.handler = handler
        self._task: asyncio.Task | None = None
        self.enabled = bool(self.base_url and self.token)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    async def start(self) -> None:
        if not self.enabled:
            logger.info("[Bridge] disabled: AZ_CONTROL_API_URL or AZ_CONTROL_BRIDGE_TOKEN missing")
            return
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._run(), name="az-control-bridge")
        logger.info("[Bridge] enabled: polling %s", self.base_url)

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        await asyncio.gather(self._task, return_exceptions=True)
        self._task = None

    async def _run(self) -> None:
        await self.publish_states([])
        while True:
            try:
                actions = await asyncio.to_thread(self._get_actions)
                for action in actions:
                    await self._process(action)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("[Bridge] poll failed")
            await asyncio.sleep(self.interval)

    def _get_actions(self) -> list[dict[str, Any]]:
        response = requests.get(f"{self.base_url}/api/bridge/actions", headers=self._headers(), params={"limit": 10}, timeout=15)
        response.raise_for_status()
        return response.json().get("actions", [])

    async def _process(self, action: dict[str, Any]) -> None:
        queue_id = int(action["id"])
        try:
            result = await self.handler(action)
            await self._send_result(queue_id, "succeeded", str(result.get("detail", "completed")))
        except Exception as exc:
            logger.exception("[Bridge] action %s failed", queue_id)
            await self._send_result(queue_id, "failed", str(exc)[:1000])

    async def _send_result(self, queue_id: int, status: str, details: str) -> None:
        await asyncio.to_thread(
            requests.post,
            f"{self.base_url}/api/bridge/actions/{queue_id}/result",
            headers=self._headers(),
            json={"status": status, "details": details},
            timeout=15,
        )

    async def publish_states(self, states: list[dict[str, str]]) -> None:
        if not self.enabled:
            return
        await asyncio.to_thread(
            requests.post,
            f"{self.base_url}/api/bridge/states",
            headers=self._headers(),
            json={"states": states},
            timeout=15,
        )
