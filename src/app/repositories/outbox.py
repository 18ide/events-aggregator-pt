from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OutboxEntry

PENDING = "pending"
SENT = "sent"
FAILED = "failed"


class SqlAlchemyOutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, event_type: str, payload: dict[str, Any]) -> OutboxEntry:
        entry = OutboxEntry(
            event_type=event_type,
            payload=payload,
            status=PENDING,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def get_pending(
        self,
        limit: int,
        max_attempts: int = 10,
    ) -> list[OutboxEntry]:
        stmt = (
            select(OutboxEntry)
            .where(OutboxEntry.status == PENDING)
            .where(OutboxEntry.attempts < max_attempts)
            .order_by(OutboxEntry.created_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_sent(self, entry: OutboxEntry) -> None:
        entry.status = SENT
        entry.sent_at = datetime.now(UTC)
        await self._session.flush()

    async def mark_failed(self, entry: OutboxEntry, error: str) -> None:
        entry.attempts += 1
        entry.last_error = error[:500]
        await self._session.flush()
