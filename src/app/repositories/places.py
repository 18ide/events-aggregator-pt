from __future__ import annotations

from typing import Any

from sqlalchemy.dialects.postgresql import insert

from app.db.models import Place
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyPlaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, data: dict[str, Any]) -> Place:
        stmt = (
            insert(Place)
            .values(
                id=data["id"],
                name=data["name"],
                city=data["city"],
                address=data["address"],
                seats_pattern=data["seats_pattern"],
                changed_at=data["changed_at"],
                created_at=data["created_at"],
            )
            .on_conflict_do_update(
                index_elements=[Place.id],
                set_={
                    "name": data["name"],
                    "city": data["city"],
                    "address": data["address"],
                    "seats_pattern": data["seats_pattern"],
                    "changed_at": data["changed_at"],
                },
            )
            .returning(Place)
        )
        result = await self._session.execute(stmt)
        place = result.scalar_one()
        await self._session.flush()
        return place
