from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.common import PaginatedResponse
from app.api.schemas.events import EventDetail, EventShort, SeatsResponse
from app.cache import TTLCache
from app.core.config import settings
from app.db.session import get_session
from app.errors import EventNotFoundError, ProviderUnavailableError
from app.repositories.events import SqlAlchemyEventRepository
from app.services.events_provider import EventsProviderClient, EventsProviderError

router = APIRouter(tags=["events"])

_seats_cache: TTLCache[list[str]] = TTLCache(ttl_seconds=30)


def get_seats_cache() -> TTLCache[list[str]]:
    return _seats_cache


@router.get("/events", response_model=PaginatedResponse[EventShort])
async def list_events(
    request: Request,
    date_from: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[EventShort]:
    repo = SqlAlchemyEventRepository(session)
    total, items = await repo.list_paginated(date_from, page, page_size)

    base = str(request.url_for("list_events"))
    next_url = f"{base}?page={page + 1}&page_size={page_size}" if page * page_size < total else None
    prev_url = f"{base}?page={page - 1}&page_size={page_size}" if page > 1 else None

    return PaginatedResponse[EventShort](
        count=total,
        next=next_url,
        previous=prev_url,
        results=[EventShort.model_validate(item) for item in items],
    )


@router.get("/events/{event_id}", response_model=EventDetail)
async def get_event(
    event_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> EventDetail:
    repo = SqlAlchemyEventRepository(session)
    event = await repo.get(event_id)
    if event is None:
        raise EventNotFoundError(f"Event {event_id} not found")
    return EventDetail.model_validate(event)


@router.get("/events/{event_id}/seats", response_model=SeatsResponse)
async def get_event_seats(
    event_id: UUID,
    session: AsyncSession = Depends(get_session),
    cache: TTLCache[list[str]] = Depends(get_seats_cache),
) -> SeatsResponse:
    repo = SqlAlchemyEventRepository(session)
    event = await repo.get(event_id)
    if event is None:
        raise EventNotFoundError(f"Event {event_id} not found")

    if event.status != "published":
        # Избегаем 500 от внешнего API — валидируем на своей стороне.
        raise HTTPException(
            status_code=400,
            detail=f"Event {event_id} is not published",
        )

    cache_key = str(event_id)
    seats = cache.get(cache_key)
    if seats is None:
        client = EventsProviderClient(
            base_url=settings.events_provider_url,
            api_key=settings.events_provider_api_key,
        )
        async with client:
            try:
                seats = await client.fetch_seats(str(event_id))
            except EventsProviderError as exc:
                raise ProviderUnavailableError(str(exc)) from exc
        cache.set(cache_key, seats)

    return SeatsResponse(event_id=event_id, available_seats=seats)
