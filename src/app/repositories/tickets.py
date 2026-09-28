from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Ticket


class SqlAlchemyTicketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        event_id: UUID,
        ticket_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> Ticket:
        ticket = Ticket(
            event_id=event_id,
            ticket_id=ticket_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
            status="active",
        )
        self._session.add(ticket)
        await self._session.flush()
        return ticket

    async def get_by_ticket_id(self, ticket_id: str) -> Ticket | None:
        stmt = (
            select(Ticket)
            .where(Ticket.ticket_id == ticket_id, Ticket.status == "active")
            .order_by(Ticket.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_canceled(self, ticket: Ticket) -> None:
        ticket.status = "canceled"
        ticket.canceled_at = datetime.now(UTC)
        await self._session.flush()
