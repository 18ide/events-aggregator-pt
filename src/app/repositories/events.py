from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Event


class SqlAlchemyEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, data: dict[str, Any]) -> Event:
        stmt = (
            insert(Event)
            .values(
                id=data["id"],
                name=data["name"],
                place_id=data["place"]["id"],
                event_time=data["event_time"],
                registration_deadline=data["registration_deadline"],
                status=data["status"],
                number_of_visitors=data.get("number_of_visitors", 0),
                changed_at=data["changed_at"],
                created_at=data["created_at"],
                status_changed_at=data["status_changed_at"],
            )
            .on_conflict_do_update(
                index_elements=[Event.id],
                set_={
                    "name": data["name"],
                    "place_id": data["place"]["id"],
                    "event_time": data["event_time"],
                    "registration_deadline": data["registration_deadline"],
                    "status": data["status"],
                    "number_of_visitors": data.get("number_of_visitors", 0),
                    "changed_at": data["changed_at"],
                    "status_changed_at": data["status_changed_at"],
                },
            )
            .returning(Event)
        )
        result = await self._session.execute(stmt)
        event = result.scalar_one()
        await self._session.flush()
        return event

    async def get(self, event_id: UUID) -> Event | None:
        return await self._session.get(Event, event_id)

    async def list_paginated(
        self,
        date_from: date | None,
        page: int,
        page_size: int,
    ) -> tuple[int, list[Event]]:
        base = select(Event)
        if date_from is not None:
            base = base.where(Event.event_time >= date_from)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = int((await self._session.execute(count_stmt)).scalar_one())

        stmt = base.order_by(Event.event_time.asc()).offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(stmt)
        events = list(result.scalars().unique().all())

        return total, events
