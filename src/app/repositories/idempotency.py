from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import IdempotencyKey


class SqlAlchemyIdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, key: str) -> IdempotencyKey | None:
        return await self._session.get(IdempotencyKey, key)

    async def create(
        self,
        key: str,
        event_id: UUID,
        seat: str,
        email: str,
        ticket_id: str,
    ) -> IdempotencyKey:
        entry = IdempotencyKey(
            key=key,
            event_id=event_id,
            seat=seat,
            email=email,
            ticket_id=ticket_id,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry
