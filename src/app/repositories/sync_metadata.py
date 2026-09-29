from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SyncMetadata


class SqlAlchemySyncMetadataRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self) -> SyncMetadata:
        meta = await self._session.get(SyncMetadata, 1)
        if meta is None:
            meta = SyncMetadata(id=1, sync_status="never")
            self._session.add(meta)
            await self._session.flush()
        return meta

    async def mark_success(self, last_changed_at: str) -> None:
        meta = await self.get()
        meta.last_sync_time = datetime.now(UTC)
        meta.last_changed_at = last_changed_at
        meta.sync_status = "success"
        await self._session.flush()

    async def mark_failure(self, error: str) -> None:
        meta = await self.get()
        meta.last_sync_time = datetime.now(UTC)
        meta.sync_status = f"error: {error[:200]}"
        await self._session.flush()
