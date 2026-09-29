from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.db.session import async_session_factory
from app.services.events_provider import EventsProviderClient
from app.services.sync import SyncService

logger = logging.getLogger(__name__)


async def sync_worker() -> None:
    """Background worker that runs sync every SYNC_INTERVAL_SECONDS."""
    while True:
        try:
            async with async_session_factory() as session:
                client = EventsProviderClient(
                    base_url=settings.events_provider_url,
                    api_key=settings.events_provider_api_key,
                )
                service = SyncService(client, session)
                await service.run()
        except Exception:
            logger.exception("Background sync failed, will retry on next tick")

        await asyncio.sleep(settings.sync_interval_seconds)
