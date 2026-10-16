from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.services.outbox import _process_batch


async def test_process_batch_marks_sent() -> None:
    session = MagicMock()
    session.commit = AsyncMock()

    # подменяем репозиторий
    from app.services import outbox as outbox_module

    original = outbox_module.SqlAlchemyOutboxRepository

    fake_repo = MagicMock()
    fake_repo.get_pending = AsyncMock(
        return_value=[
            MagicMock(id=uuid4(), event_type="ticket_purchased", attempts=0),
        ]
    )
    fake_repo.mark_sent = AsyncMock()
    fake_repo.mark_failed = AsyncMock()

    outbox_module.SqlAlchemyOutboxRepository = lambda session: fake_repo
    try:
        processed = await _process_batch(session)
    finally:
        outbox_module.SqlAlchemyOutboxRepository = original

    assert processed == 1
    fake_repo.mark_sent.assert_awaited_once()
    session.commit.assert_awaited_once()


async def test_process_batch_marks_failed_on_exception() -> None:
    session = MagicMock()
    session.commit = AsyncMock()

    from app.services import outbox as outbox_module

    original = outbox_module.SqlAlchemyOutboxRepository
    original_process = outbox_module._process_entry

    entry = MagicMock(id=uuid4(), event_type="ticket_purchased", attempts=0)
    fake_repo = MagicMock()
    fake_repo.get_pending = AsyncMock(return_value=[entry])
    fake_repo.mark_sent = AsyncMock()
    fake_repo.mark_failed = AsyncMock()

    async def failing_process(repo, e):
        raise RuntimeError("boom")

    outbox_module.SqlAlchemyOutboxRepository = lambda session: fake_repo
    outbox_module._process_entry = failing_process
    try:
        processed = await _process_batch(session)
    finally:
        outbox_module.SqlAlchemyOutboxRepository = original
        outbox_module._process_entry = original_process

    assert processed == 0
    fake_repo.mark_failed.assert_awaited_once()
    session.commit.assert_awaited_once()
