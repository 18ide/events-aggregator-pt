from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services import outbox as outbox_module
from app.services.capashino import CapashinoError
from app.services.outbox import _process_batch


def _make_entry(**overrides):
    entry = MagicMock()
    entry.id = uuid4()
    entry.event_type = "ticket_purchased"
    entry.attempts = 0
    entry.payload = {
        "ticket_id": "ticket-1",
        "seat": "A1",
        "first_name": "Ivan",
        "event_name": "Test Event",
    }
    for key, value in overrides.items():
        setattr(entry, key, value)
    return entry


@pytest.fixture
def session() -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def client() -> AsyncMock:
    c = AsyncMock()
    c.send_notification = AsyncMock(return_value={})
    return c


@pytest.fixture
def fake_repo(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    repo = MagicMock()
    repo.get_pending = AsyncMock(return_value=[])
    repo.mark_sent = AsyncMock()
    repo.mark_failed = AsyncMock()
    monkeypatch.setattr(
        outbox_module,
        "SqlAlchemyOutboxRepository",
        lambda session: repo,
    )
    return repo


async def test_process_batch_marks_sent(
    session: MagicMock,
    client: AsyncMock,
    fake_repo: MagicMock,
) -> None:
    entry = _make_entry()
    fake_repo.get_pending.return_value = [entry]

    processed = await _process_batch(session, client)

    assert processed == 1
    client.send_notification.assert_awaited_once()
    call_kwargs = client.send_notification.await_args.kwargs
    assert call_kwargs["reference_id"] == "ticket-1"
    assert call_kwargs["idempotency_key"] == "ticket-1"
    assert "Test Event" in call_kwargs["message"]
    fake_repo.mark_sent.assert_awaited_once()
    session.commit.assert_awaited_once()


async def test_process_batch_marks_failed_on_capashino_error(
    session: MagicMock,
    client: AsyncMock,
    fake_repo: MagicMock,
) -> None:
    entry = _make_entry()
    fake_repo.get_pending.return_value = [entry]
    client.send_notification.side_effect = CapashinoError(401, "unauthorized")

    processed = await _process_batch(session, client)

    assert processed == 0
    fake_repo.mark_failed.assert_awaited_once()
    session.commit.assert_awaited_once()


async def test_process_batch_marks_failed_on_generic_error(
    session: MagicMock,
    client: AsyncMock,
    fake_repo: MagicMock,
) -> None:
    entry = _make_entry()
    fake_repo.get_pending.return_value = [entry]
    client.send_notification.side_effect = RuntimeError("boom")

    processed = await _process_batch(session, client)

    assert processed == 0
    fake_repo.mark_failed.assert_awaited_once()
    session.commit.assert_awaited_once()


async def test_process_batch_skips_unknown_event_type(
    session: MagicMock,
    client: AsyncMock,
    fake_repo: MagicMock,
) -> None:
    entry = _make_entry(event_type="unknown")
    fake_repo.get_pending.return_value = [entry]

    processed = await _process_batch(session, client)

    assert processed == 1
    client.send_notification.assert_not_awaited()
    fake_repo.mark_sent.assert_awaited_once()


async def test_process_batch_handles_empty_batch(
    session: MagicMock,
    client: AsyncMock,
    fake_repo: MagicMock,
) -> None:
    fake_repo.get_pending.return_value = []

    processed = await _process_batch(session, client)

    assert processed == 0
    client.send_notification.assert_not_awaited()
