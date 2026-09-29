from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.services.events_provider import EventsProviderClient
from app.services.sync import SyncService

router = APIRouter(tags=["sync"])


@router.post("/sync/trigger")
async def trigger_sync(session: AsyncSession = Depends(get_session)) -> dict[str, int]:
    client = EventsProviderClient(
        base_url=settings.events_provider_url,
        api_key=settings.events_provider_api_key,
    )
    service = SyncService(client, session)
    processed = await service.run()
    return {"processed": processed}
