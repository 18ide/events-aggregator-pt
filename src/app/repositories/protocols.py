from __future__ import annotations

from datetime import date
from typing import Any, Protocol
from uuid import UUID

from app.db.models import Event, Place, SyncMetadata, Ticket


class PlaceRepository(Protocol):
    async def upsert(self, data: dict[str, Any]) -> Place: ...


class EventRepository(Protocol):
    async def upsert(self, data: dict[str, Any]) -> Event: ...

    async def get(self, event_id: UUID) -> Event | None: ...

    async def list_paginated(
        self,
        date_from: date | None,
        page: int,
        page_size: int,
    ) -> tuple[int, list[Event]]: ...


class TicketRepository(Protocol):
    async def create(
        self,
        event_id: UUID,
        ticket_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> Ticket: ...

    async def get_by_ticket_id(self, ticket_id: str) -> Ticket | None: ...

    async def mark_canceled(self, ticket: Ticket) -> None: ...


class SyncMetadataRepository(Protocol):
    async def get(self) -> SyncMetadata: ...

    async def mark_success(self, last_changed_at: str) -> None: ...

    async def mark_failure(self, error: str) -> None: ...
