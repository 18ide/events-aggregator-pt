from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.sync import SyncService


@pytest.fixture
def session() -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


async def test_sync_uses_initial_bookmark_on_first_run(session: MagicMock) -> None:
    service = SyncService(client=AsyncMock(), session=session)
    service._meta = AsyncMock()
    service._meta.get.return_value = MagicMock(last_changed_at=None)
    service._places = AsyncMock()
    service._events = AsyncMock()

    # Пагинатор подменяем целиком: он сложен для мока через клиент.
    async def fake_aiter(self):
        for i in range(3):
            yield {
                "id": f"e{i}",
                "place": {"id": f"p{i}"},
                "changed_at": f"2026-01-0{i + 1}T00:00:00+00:00",
            }

    from app.services import sync as sync_module

    original = sync_module.EventsPaginator
    sync_module.EventsPaginator = lambda client, changed_at: _FakePaginator(fake_aiter)

    try:
        processed = await service.run()
    finally:
        sync_module.EventsPaginator = original

    assert processed == 3
    service._meta.mark_success.assert_awaited_once()
    bookmark = service._meta.mark_success.await_args.args[0]
    assert bookmark == "2026-01-03T00:00:00+00:00"


class _FakePaginator:
    def __init__(self, aiter_func):
        self._aiter = aiter_func

    def __aiter__(self):
        return self._aiter(self)
