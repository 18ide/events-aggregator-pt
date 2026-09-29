from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import sync as sync_module
from app.services.sync import SyncService


def _raw_event(idx: int, changed_at: str) -> dict:
    return {
        "id": f"00000000-0000-0000-0000-{idx:012d}",
        "name": f"Event {idx}",
        "place": {
            "id": f"11111111-1111-1111-1111-{idx:012d}",
            "name": f"Place {idx}",
            "city": "Москва",
            "address": "ул. Ленина, 1",
            "seats_pattern": "A1-100",
            "changed_at": "2025-01-01T03:00:00+03:00",
            "created_at": "2025-01-01T03:00:00+03:00",
        },
        "event_time": "2026-01-11T17:00:00+03:00",
        "registration_deadline": "2026-01-10T17:00:00+03:00",
        "status": "published",
        "number_of_visitors": 0,
        "changed_at": changed_at,
        "created_at": "2026-01-04T22:28:35+03:00",
        "status_changed_at": "2026-01-04T22:28:35+03:00",
    }


class _FakePaginator:
    def __init__(self, events):
        self._events = events

    def __aiter__(self):
        async def gen():
            for event in self._events:
                yield event

        return gen()


@pytest.fixture
def session() -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


async def test_sync_uses_initial_bookmark_on_first_run(
    session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = SyncService(client=AsyncMock(), session=session)
    service._meta = AsyncMock()
    service._meta.get.return_value = MagicMock(last_changed_at=None)
    service._places = AsyncMock()
    service._events = AsyncMock()

    events = [
        _raw_event(1, "2026-01-01T00:00:00+00:00"),
        _raw_event(2, "2026-01-02T00:00:00+00:00"),
        _raw_event(3, "2026-01-03T00:00:00+00:00"),
    ]

    monkeypatch.setattr(
        sync_module,
        "EventsPaginator",
        lambda client, changed_at: _FakePaginator(events),
    )

    processed = await service.run()

    assert processed == 3
    service._meta.mark_success.assert_awaited_once()
    bookmark = service._meta.mark_success.await_args.args[0]
    assert bookmark == "2026-01-03T00:00:00+00:00"
    session.commit.assert_awaited_once()
    assert service._events.upsert.await_count == 3
    assert service._places.upsert.await_count == 3


async def test_sync_truncates_existing_bookmark_to_date(
    session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = SyncService(client=AsyncMock(), session=session)
    service._meta = AsyncMock()
    service._meta.get.return_value = MagicMock(last_changed_at="2026-09-29T12:00:00.759462+03:00")
    service._places = AsyncMock()
    service._events = AsyncMock()

    captured_changed_at: list[str] = []

    def fake_paginator(client, changed_at):
        captured_changed_at.append(changed_at)
        return _FakePaginator([])

    monkeypatch.setattr(sync_module, "EventsPaginator", fake_paginator)

    processed = await service.run()

    assert processed == 0
    assert captured_changed_at == ["2026-09-29"]
    service._meta.mark_success.assert_awaited_once_with("2026-09-29")


async def test_sync_rolls_back_on_error(
    session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = SyncService(client=AsyncMock(), session=session)
    service._meta = AsyncMock()
    service._meta.get.return_value = MagicMock(last_changed_at=None)
    service._places = AsyncMock()
    service._places.upsert.side_effect = RuntimeError("db is down")
    service._events = AsyncMock()

    events = [_raw_event(1, "2026-01-01T00:00:00+00:00")]

    monkeypatch.setattr(
        sync_module,
        "EventsPaginator",
        lambda client, changed_at: _FakePaginator(events),
    )

    with pytest.raises(RuntimeError, match="db is down"):
        await service.run()

    session.rollback.assert_awaited_once()
    service._meta.mark_failure.assert_awaited_once()
