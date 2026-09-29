from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routers import events, health, sync, tickets
from app.core.logging import configure_logging
from app.errors import DomainError
from app.services.worker import sync_worker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Events Aggregator")
    task = asyncio.create_task(sync_worker())
    try:
        yield
    finally:
        logger.info("Shutting down Events Aggregator")
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


configure_logging()

app = FastAPI(
    title="Events Aggregator",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router, prefix="/api")
app.include_router(sync.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(tickets.router, prefix="/api")


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "code": exc.code},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return 400 for validation errors instead of FastAPI's default 422."""
    return JSONResponse(
        status_code=400,
        content={"detail": exc.errors()},
    )
