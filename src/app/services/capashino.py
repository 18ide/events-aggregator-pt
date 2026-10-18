from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class CapashinoError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"Capashino error {status_code}: {message}")


class CapashinoClient:
    """Async client for the Capashino Notification API."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> CapashinoClient:
        await self.start()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def start(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={"X-API-Key": self._api_key},
                timeout=self._timeout,
                follow_redirects=True,
            )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("CapashinoClient is not started")
        return self._client

    async def send_notification(
        self,
        message: str,
        reference_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        response = await self.client.post(
            "/api/notifications",
            json={
                "message": message,
                "reference_id": reference_id,
                "idempotency_key": idempotency_key,
            },
        )

        # 200/201 — создано; 409 — уже существует (идемпотентный успех)
        if response.status_code in (200, 201, 409):
            if response.status_code == 409:
                logger.info(
                    "Capashino: notification already exists for idempotency_key=%s",
                    idempotency_key,
                )
            try:
                return response.json()
            except ValueError:
                return {}

        message_text: str
        try:
            data = response.json()
            message_text = str(data.get("detail") or data) if isinstance(data, dict) else str(data)
        except ValueError:
            message_text = response.text[:500] or response.reason_phrase

        logger.warning(
            "Capashino returned %s for %s: %s",
            response.status_code,
            response.request.url,
            message_text,
        )
        raise CapashinoError(response.status_code, message_text)
