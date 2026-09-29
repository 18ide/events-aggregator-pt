from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import (
    EventNotFoundError,
    EventNotPublishedError,
    ProviderUnavailableError,
    RegistrationClosedError,
    SeatNotAvailableError,
    TicketNotFoundError,
)
from app.repositories.events import SqlAlchemyEventRepository
from app.repositories.tickets import SqlAlchemyTicketRepository
from app.services.events_provider import EventsProviderClient, EventsProviderError

logger = logging.getLogger(__name__)


class CreateTicketUseCase:
    """Business logic for registering a user on an event."""

    def __init__(
        self,
        client: EventsProviderClient,
        session: AsyncSession,
    ) -> None:
        self._client = client
        self._session = session
        self._events = SqlAlchemyEventRepository(session)
        self._tickets = SqlAlchemyTicketRepository(session)

    async def do(
        self,
        event_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> str:
        event = await self._events.get(event_id)
        if event is None:
            raise EventNotFoundError(f"Event {event_id} not found")

        if event.status != "published":
            raise EventNotPublishedError(
                f"Event {event_id} is not published (status={event.status})"
            )

        now = datetime.now(UTC)
        if event.registration_deadline < now:
            raise RegistrationClosedError(
                f"Registration for event {event_id} closed at "
                f"{event.registration_deadline.isoformat()}"
            )

        async with self._client:
            try:
                available = await self._client.fetch_seats(str(event_id))
            except EventsProviderError as exc:
                raise ProviderUnavailableError(str(exc)) from exc

            if seat not in available:
                raise SeatNotAvailableError(f"Seat {seat} is not available")

            try:
                ticket_id = await self._client.register(
                    event_id=str(event_id),
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    seat=seat,
                )
            except EventsProviderError as exc:
                # Provider может вернуть 400 "seat already sold" при гонке.
                raise SeatNotAvailableError(str(exc)) from exc

        await self._tickets.create(
            event_id=event_id,
            ticket_id=ticket_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
        )
        await self._session.commit()
        logger.info("Ticket %s created for event %s seat %s", ticket_id, event_id, seat)
        return ticket_id


class CancelTicketUseCase:
    """Business logic for cancelling a registration by ticket id."""

    def __init__(
        self,
        client: EventsProviderClient,
        session: AsyncSession,
    ) -> None:
        self._client = client
        self._session = session
        self._tickets = SqlAlchemyTicketRepository(session)

    async def do(self, ticket_id: str) -> None:
        ticket = await self._tickets.get_by_ticket_id(ticket_id)
        if ticket is None:
            raise TicketNotFoundError(f"Ticket {ticket_id} not found")

        async with self._client:
            try:
                await self._client.unregister(
                    event_id=str(ticket.event_id),
                    ticket_id=ticket_id,
                )
            except EventsProviderError as exc:
                raise ProviderUnavailableError(str(exc)) from exc

        await self._tickets.mark_canceled(ticket)
        await self._session.commit()
        logger.info("Ticket %s cancelled", ticket_id)
