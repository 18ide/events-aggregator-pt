from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from app.services.events_provider import EventsProviderClient

logger = logging.getLogger(__name__)


class EventsPaginator:
    """Async iterator over all events from the Events Provider API.

    Handles cursor-based pagination transparently: callers just iterate
    and receive one event dict at a time.

    Example:
        client = EventsProviderClient(base_url, api_key)
        async with client:
            async for event in EventsPaginator(client, changed_at="2000-01-01"):
                ...
    """

    def __init__(
        self,
        client: EventsProviderClient,
        changed_at: str = "2000-01-01",
        max_pages: int | None = None,
    ) -> None:
        self._client = client
        self._changed_at = changed_at
        self._max_pages = max_pages

    async def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        page = await self._client.fetch_events_page(self._changed_at)
        pages_fetched = 0

        while True:
            pages_fetched += 1
            for event in page.get("results", []):
                yield event

            next_url = page.get("next")
            if not next_url:
                return

            if self._max_pages is not None and pages_fetched >= self._max_pages:
                logger.warning(
                    "EventsPaginator reached max_pages=%s, stopping early",
                    self._max_pages,
                )
                return

            page = await self._client.fetch_events_by_url(next_url)
