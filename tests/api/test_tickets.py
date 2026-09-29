from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.errors import (
    EventNotFoundError,
    EventNotPublishedError,
    RegistrationClosedError,
    SeatNotAvailableError,
)
from app.services.tickets import CreateTicketUseCase


@pytest.fixture
def session() -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def client() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def usecase(client: AsyncMock, session: MagicMock) -> CreateTicketUseCase:
    uc = CreateTicketUseCase(client=client, session=session)
    uc._events = AsyncMock()
    uc._tickets = AsyncMock()
    return uc


def _make_event(**overrides):
    event = MagicMock()
    event.id = uuid4()
    event.status = "published"
    event.registration_deadline = datetime.now(UTC) + timedelta(days=1)
    for key, value in overrides.items():
        setattr(event, key, value)
    return event


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
    usecase._session.commit.assert_awaited_once()
