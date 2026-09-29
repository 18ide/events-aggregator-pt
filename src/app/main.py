from __future__ import annotations

import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routers import health, sync
from app.core.logging import configure_logging
from app.services.worker import sync_worker

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(sync_worker())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="Events Aggregator",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router, prefix="/api")
app.include_router(sync.router, prefix="/api")
