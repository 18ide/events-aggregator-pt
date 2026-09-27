from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SyncMetadata(Base):
    __tablename__ = "sync_metadata"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    last_sync_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_changed_at: Mapped[str | None] = mapped_column(String(64))
    sync_status: Mapped[str] = mapped_column(String(32), default="never")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
