from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_factory
from app.repositories.outbox import SqlAlchemyOutboxRepository

logger = logging.getLogger(__name__)


async def _process_entry(
    repo: SqlAlchemyOutboxRepository,
    entry,
) -> None:
    """Process a single outbox entry.

    Iteration 1: just log. Iteration 2 will call Capashino here.
    """
    logger.info(
        "Processing outbox entry id=%s type=%s attempts=%s",
        entry.id,
        entry.event_type,
        entry.attempts,
    )
    await repo.mark_sent(entry)


async def _process_batch(session: AsyncSession) -> int:
    repo = SqlAlchemyOutboxRepository(session)
    entries = await repo.get_pending(limit=settings.outbox_batch_size)

    processed = 0
    for entry in entries:
        try:
            await _process_entry(repo, entry)
            processed += 1
        except Exception as exc:
            logger.exception("Outbox entry %s failed: %s", entry.id, exc)
            await repo.mark_failed(entry, str(exc))

    await session.commit()
    return processed


async def outbox_worker() -> None:
    """Background coroutine that periodically flushes the outbox."""
    logger.info("Outbox worker started")
    while True:
        try:
            async with async_session_factory() as session:
                processed = await _process_batch(session)
                if processed:
                    logger.info("Outbox: processed %s entries", processed)
        except Exception:
            logger.exception("Outbox worker iteration failed, will retry")
        await asyncio.sleep(settings.outbox_poll_interval_seconds)
