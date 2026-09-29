from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.events import SqlAlchemyEventRepository
from app.repositories.places import SqlAlchemyPlaceRepository
from app.repositories.sync_metadata import SqlAlchemySyncMetadataRepository
from app.services.events_provider import EventsProviderClient
from app.services.paginator import EventsPaginator

logger = logging.getLogger(__name__)

INITIAL_CHANGED_AT = "2000-01-01"


def _parse_dt(value: str) -> datetime:
    """Parse ISO 8601 datetime string into timezone-aware datetime."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _as_date(value: str) -> str:
    """Truncate an ISO 8601 datetime string to date-only form.

    The provider's `changed_at` parameter accepts only `YYYY-MM-DD`,
    but we store the full timestamp for precision.
    """
    return value.split("T", 1)[0]


def _normalize_place(place: dict) -> dict:
    return {
        "id": place["id"],
        "name": place["name"],
        "city": place["city"],
        "address": place["address"],
        "seats_pattern": place["seats_pattern"],
        "changed_at": _parse_dt(place["changed_at"]),
        "created_at": _parse_dt(place["created_at"]),
    }


def _normalize_event(event: dict) -> dict:
    return {
        "id": event["id"],
        "name": event["name"],
        "place": _normalize_place(event["place"]),
        "event_time": _parse_dt(event["event_time"]),
        "registration_deadline": _parse_dt(event["registration_deadline"]),
        "status": event["status"],
        "number_of_visitors": event.get("number_of_visitors", 0),
        "changed_at": _parse_dt(event["changed_at"]),
        "created_at": _parse_dt(event["created_at"]),
        "status_changed_at": _parse_dt(event["status_changed_at"]),
    }


class SyncService:
    """Service responsible for incremental event synchronization.

    The service pulls events from the provider using a `changed_at` bookmark,
    upserts them (and their places) into the local DB, and updates the bookmark.
    """

    def __init__(
        self,
        client: EventsProviderClient,
        session: AsyncSession,
    ) -> None:
        self._client = client
        self._session = session
        self._places = SqlAlchemyPlaceRepository(session)
        self._events = SqlAlchemyEventRepository(session)
        self._meta = SqlAlchemySyncMetadataRepository(session)

    async def run(self) -> int:
        """Run one synchronization cycle.

        Returns the number of events processed. On error the bookmark is
        left untouched so the next run will retry the same range.
        """
        meta = await self._meta.get()
        changed_at = _as_date(meta.last_changed_at or INITIAL_CHANGED_AT)

        logger.info("Starting sync, changed_at=%s", changed_at)

        processed = 0
        max_changed_at: str | None = None

        try:
            async with self._client:
                paginator = EventsPaginator(self._client, changed_at=changed_at)
                async for raw_event in paginator:
                    event = _normalize_event(raw_event)
                    await self._places.upsert(event["place"])
                    await self._events.upsert(event)
                    processed += 1

                    event_changed_at = raw_event.get("changed_at")
                    if event_changed_at and (
                        max_changed_at is None or event_changed_at > max_changed_at
                    ):
                        max_changed_at = event_changed_at

            await self._meta.mark_success(max_changed_at or changed_at)
            await self._session.commit()
            logger.info(
                "Sync finished, processed=%s, bookmark=%s",
                processed,
                max_changed_at,
            )
            return processed

        except Exception as exc:
            await self._session.rollback()
            logger.exception("Sync failed: %s", exc)
            try:
                await self._meta.mark_failure(str(exc))
                await self._session.commit()
            except Exception:
                await self._session.rollback()
            raise
