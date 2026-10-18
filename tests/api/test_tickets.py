from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.errors import (
    EventNotFoundError,
    EventNotPublishedError,
    IdempotencyConflictError,
    RegistrationClosedError,
    SeatNotAvailableError,
)
from app.services.tickets import CreateTicketUseCase


@pytest.fixture
def session() -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def client() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def usecase(client: AsyncMock, session: MagicMock) -> CreateTicketUseCase:
    uc = CreateTicketUseCase(client=client, session=session)
    uc._events = AsyncMock()
    uc._tickets = AsyncMock()
    uc._outbox = AsyncMock()
    uc._idempotency = AsyncMock()
    return uc


def _make_event(**overrides):
    event = MagicMock()
    event.id = uuid4()
    event.name = "Test Event"
    event.status = "published"
    event.registration_deadline = datetime.now(UTC) + timedelta(days=1)
    for key, value in overrides.items():
        setattr(event, key, value)
    return event


def _make_idempotency(event_id, seat, email, ticket_id="existing-ticket"):
    entry = MagicMock()
    entry.event_id = event_id
    entry.seat = seat
    entry.email = email
    entry.ticket_id = ticket_id
    return entry


async def test_create_ticket_event_not_found(usecase: CreateTicketUseCase) -> None:
    usecase._events.get.return_value = None
    with pytest.raises(EventNotFoundError):
        await usecase.do(uuid4(), "Ivan", "Ivanov", "i@example.com", "A1")


async def test_create_ticket_event_not_published(usecase: CreateTicketUseCase) -> None:
    usecase._events.get.return_value = _make_event(status="new")
    with pytest.raises(EventNotPublishedError):
        await usecase.do(uuid4(), "Ivan", "Ivanov", "i@example.com", "A1")


async def test_create_ticket_registration_closed(usecase: CreateTicketUseCase) -> None:
    usecase._events.get.return_value = _make_event(
        registration_deadline=datetime.now(UTC) - timedelta(hours=1)
    )
    with pytest.raises(RegistrationClosedError):
        await usecase.do(uuid4(), "Ivan", "Ivanov", "i@example.com", "A1")


async def test_create_ticket_seat_not_available(usecase: CreateTicketUseCase) -> None:
    usecase._events.get.return_value = _make_event()
    usecase._client.fetch_seats.return_value = ["A2", "A3"]
    with pytest.raises(SeatNotAvailableError):
        await usecase.do(uuid4(), "Ivan", "Ivanov", "i@example.com", "A1")


async def test_create_ticket_success(usecase: CreateTicketUseCase) -> None:
    event = _make_event()
    usecase._events.get.return_value = event
    usecase._client.fetch_seats.return_value = ["A1", "A2"]
    usecase._client.register.return_value = "ticket-xyz"

    ticket_id = await usecase.do(event.id, "Ivan", "Ivanov", "i@example.com", "A1")

    assert ticket_id == "ticket-xyz"
    usecase._tickets.create.assert_awaited_once()
    usecase._outbox.create.assert_awaited_once()
    usecase._idempotency.create.assert_not_awaited()
    usecase._session.commit.assert_awaited_once()


async def test_create_ticket_idempotent_replay(usecase: CreateTicketUseCase) -> None:
    event = _make_event()
    usecase._events.get.return_value = event

    existing = _make_idempotency(event.id, "A1", "i@example.com", ticket_id="old-ticket")
    usecase._idempotency.get.return_value = existing

    ticket_id = await usecase.do(
        event.id,
        "Ivan",
        "Ivanov",
        "i@example.com",
        "A1",
        idempotency_key="key-123",
    )

    assert ticket_id == "old-ticket"
    usecase._client.fetch_seats.assert_not_awaited()
    usecase._client.register.assert_not_awaited()
    usecase._tickets.create.assert_not_awaited()
    usecase._outbox.create.assert_not_awaited()
    usecase._session.commit.assert_not_awaited()


async def test_create_ticket_idempotent_conflict(usecase: CreateTicketUseCase) -> None:
    event = _make_event()
    usecase._events.get.return_value = event

    # Same key, but different seat
    existing = _make_idempotency(event.id, "A2", "i@example.com", ticket_id="old-ticket")
    usecase._idempotency.get.return_value = existing

    with pytest.raises(IdempotencyConflictError):
        await usecase.do(
            event.id,
            "Ivan",
            "Ivanov",
            "i@example.com",
            "A1",
            idempotency_key="key-123",
        )

    usecase._client.register.assert_not_awaited()
    usecase._tickets.create.assert_not_awaited()


async def test_create_ticket_idempotent_new_key(usecase: CreateTicketUseCase) -> None:
    event = _make_event()
    usecase._events.get.return_value = event
    usecase._client.fetch_seats.return_value = ["A1"]
    usecase._client.register.return_value = "new-ticket"
    usecase._idempotency.get.return_value = None

    ticket_id = await usecase.do(
        event.id,
        "Ivan",
        "Ivanov",
        "i@example.com",
        "A1",
        idempotency_key="new-key",
    )

    assert ticket_id == "new-ticket"
    usecase._idempotency.create.assert_awaited_once()
    call_kwargs = usecase._idempotency.create.await_args.kwargs
    assert call_kwargs["key"] == "new-key"
    assert call_kwargs["ticket_id"] == "new-ticket"
    assert call_kwargs["seat"] == "A1"
    assert call_kwargs["email"] == "i@example.com"
    usecase._session.commit.assert_awaited_once()
