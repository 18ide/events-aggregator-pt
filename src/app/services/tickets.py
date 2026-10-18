from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import (
    EventNotFoundError,
    EventNotPublishedError,
    IdempotencyConflictError,
    ProviderUnavailableError,
    RegistrationClosedError,
    SeatNotAvailableError,
    TicketNotFoundError,
)
from app.repositories.events import SqlAlchemyEventRepository
from app.repositories.idempotency import SqlAlchemyIdempotencyRepository
from app.repositories.outbox import SqlAlchemyOutboxRepository
from app.repositories.tickets import SqlAlchemyTicketRepository
from app.services.events_provider import EventsProviderClient, EventsProviderError

logger = logging.getLogger(__name__)


class CreateTicketUseCase:
    def __init__(
        self,
        client: EventsProviderClient,
        session: AsyncSession,
    ) -> None:
        self._client = client
        self._session = session
        self._events = SqlAlchemyEventRepository(session)
        self._tickets = SqlAlchemyTicketRepository(session)
        self._outbox = SqlAlchemyOutboxRepository(session)
        self._idempotency = SqlAlchemyIdempotencyRepository(session)

    async def do(
        self,
        event_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
        idempotency_key: str | None = None,
    ) -> str:
        # 1. Idempotency fast-path: return cached result or raise conflict
        if idempotency_key is not None:
            existing = await self._idempotency.get(idempotency_key)
            if existing is not None:
                self._ensure_same_request(existing, event_id, seat, email)
                logger.info(
                    "Idempotent replay for key=%s ticket_id=%s",
                    idempotency_key,
                    existing.ticket_id,
                )
                return existing.ticket_id

        # 2. Normal flow: business validation
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

        # 3. Provider calls
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
                raise SeatNotAvailableError(str(exc)) from exc

        # 4. Persist atomically: ticket + outbox + idempotency
        try:
            await self._tickets.create(
                event_id=event_id,
                ticket_id=ticket_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                seat=seat,
            )
            await self._outbox.create(
                event_type="ticket_purchased",
                payload={
                    "ticket_id": ticket_id,
                    "event_id": str(event_id),
                    "event_name": event.name,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "seat": seat,
                },
            )
            if idempotency_key is not None:
                await self._idempotency.create(
                    key=idempotency_key,
                    event_id=event_id,
                    seat=seat,
                    email=email,
                    ticket_id=ticket_id,
                )
            await self._session.commit()
        except IntegrityError:
            # Race: another request committed the same key between our
            # get() and create(). Roll back and return the winner's result.
            await self._session.rollback()
            if idempotency_key is None:
                raise
            existing = await self._idempotency.get(idempotency_key)
            if existing is None:
                raise
            self._ensure_same_request(existing, event_id, seat, email)
            logger.warning(
                "Idempotency race for key=%s, returning existing ticket_id=%s",
                idempotency_key,
                existing.ticket_id,
            )
            return existing.ticket_id

        logger.info(
            "Ticket %s created for event %s seat %s (idem=%s)",
            ticket_id,
            event_id,
            seat,
            idempotency_key,
        )
        return ticket_id

    def _ensure_same_request(
        self,
        existing,
        event_id: UUID,
        seat: str,
        email: str,
    ) -> None:
        if existing.event_id != event_id or existing.seat != seat or existing.email != email:
            raise IdempotencyConflictError(
                "Idempotency key was already used with different request data"
            )


class CancelTicketUseCase:
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
