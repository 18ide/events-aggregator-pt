from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class EventsProviderError(Exception):
    """Raised when the Events Provider API returns an error response."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"Events Provider error {status_code}: {message}")


class EventsProviderClient:
    """Thin async wrapper around the Events Provider REST API.

    All URLs are used with a trailing slash as required by the provider;
    otherwise the server responds with 301 redirects.
    """

    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> EventsProviderClient:
        await self.start()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def start(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={"x-api-key": self._api_key},
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
            raise RuntimeError(
                "EventsProviderClient is not started. "
                "Use 'async with EventsProviderClient(...)' or call 'await client.start()'."
            )
        return self._client

    async def fetch_events_page(
        self,
        changed_at: str,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Fetch a single page of events.

        If `cursor` is None — fetches the first page for the given `changed_at`.
        Otherwise uses the cursor token to fetch the next page.
        """
        params: dict[str, str] = {"changed_at": changed_at}
        if cursor is not None:
            params["cursor"] = cursor

        response = await self.client.get("/api/events/", params=params)
        self._raise_for_status(response)
        return response.json()

    async def fetch_events_by_url(self, url: str) -> dict[str, Any]:
        """Fetch a page using a full URL (e.g. the `next` field from a response).

        The provider occasionally returns `http://` URLs in the `next` field even
        when the base URL is https. We normalize the scheme before requesting.
        """
        url = self._normalize_url(url)
        response = await self.client.get(url)
        self._raise_for_status(response)
        return response.json()

    def _normalize_url(self, url: str) -> str:
        """Force the scheme of a provider-returned URL to match our base URL."""
        if self._base_url.startswith("https://") and url.startswith("http://"):
            return "https://" + url[len("http://") :]
        return url

    async def fetch_seats(self, event_id: str) -> list[str]:
        response = await self.client.get(f"/api/events/{event_id}/seats/")
        self._raise_for_status(response)
        return list(response.json().get("seats", []))

    async def register(
        self,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> str:
        response = await self.client.post(
            f"/api/events/{event_id}/register/",
            json={
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "seat": seat,
            },
        )
        self._raise_for_status(response)
        return str(response.json()["ticket_id"])

    async def unregister(self, event_id: str, ticket_id: str) -> None:
        response = await self.client.request(
            "DELETE",
            f"/api/events/{event_id}/unregister/",
            json={"ticket_id": ticket_id},
        )
        self._raise_for_status(response)

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.is_success:
            return

        # Try to extract a meaningful message from JSON or plain text.
        message: str
        try:
            data = response.json()
            message = str(data.get("detail") or data) if isinstance(data, dict) else str(data)
        except ValueError:
            message = response.text[:500] or response.reason_phrase

        logger.warning(
            "Events Provider returned %s for %s: %s",
            response.status_code,
            response.request.url,
            message,
        )
        raise EventsProviderError(response.status_code, message)
