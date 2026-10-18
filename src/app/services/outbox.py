from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import OutboxEntry
from app.db.session import async_session_factory
from app.repositories.outbox import SqlAlchemyOutboxRepository
from app.services.capashino import CapashinoClient, CapashinoError

logger = logging.getLogger(__name__)


def _build_message(payload: dict[str, Any]) -> str:
    event_name = payload.get("event_name") or "мероприятие"
    seat = payload.get("seat") or ""
    first_name = payload.get("first_name") or ""
    parts = [
        f"Вы успешно зарегистрированы на мероприятие «{event_name}»",
    ]
    if seat:
        parts.append(f"место {seat}")
    text = ", ".join(parts) + "."
    if first_name:
        text += f" {first_name}, ждём вас!"
    return text


async def _process_entry(
    repo: SqlAlchemyOutboxRepository,
    entry: OutboxEntry,
    client: CapashinoClient,
) -> None:
    logger.info(
        "Processing outbox entry id=%s type=%s attempts=%s",
        entry.id,
        entry.event_type,
        entry.attempts,
    )

    if entry.event_type != "ticket_purchased":
        logger.warning(
            "Unknown outbox event_type=%s, marking as sent to avoid loop",
            entry.event_type,
        )
        await repo.mark_sent(entry)
        return

    payload = entry.payload
    ticket_id = payload.get("ticket_id")
    if not ticket_id:
        raise ValueError("outbox entry missing ticket_id in payload")

    message = _build_message(payload)
    await client.send_notification(
        message=message,
        reference_id=str(ticket_id),
        idempotency_key=str(ticket_id),
    )
    await repo.mark_sent(entry)


async def _process_batch(
    session: AsyncSession,
    client: CapashinoClient,
) -> int:
    repo = SqlAlchemyOutboxRepository(session)
    entries = await repo.get_pending(
        limit=settings.outbox_batch_size,
        max_attempts=settings.outbox_max_attempts,
    )

    if not entries:
        return 0

    processed = 0
    for entry in entries:
        try:
            await _process_entry(repo, entry, client)
            processed += 1
        except CapashinoError as exc:
            logger.error(
                "Capashino rejected entry id=%s: status=%s message=%s",
                entry.id,
                exc.status_code,
                exc.message,
            )
            await repo.mark_failed(entry, exc.message)
        except Exception as exc:
            logger.exception("Outbox entry %s failed: %s", entry.id, exc)
            await repo.mark_failed(entry, str(exc))

    await session.commit()
    return processed


async def outbox_worker() -> None:
    logger.info("Outbox worker started")
    while True:
        try:
            async with (
                CapashinoClient(
                    base_url=settings.capashino_url,
                    api_key=settings.capashino_api_key,
                ) as client,
                async_session_factory() as session,
            ):
                processed = await _process_batch(session, client)
                if processed:
                    logger.info("Outbox: processed %s entries", processed)
        except Exception:
            logger.exception("Outbox worker iteration failed, will retry")
        await asyncio.sleep(settings.outbox_poll_interval_seconds)
