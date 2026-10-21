from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.api.routers import events, health, sync, tickets
from app.core.config import settings
from app.core.logging import configure_logging
from app.errors import DomainError
from app.services.worker import sync_worker

logger = logging.getLogger(__name__)


configure_logging()

if settings.glitchtip_dsn:
    sentry_sdk.init(
        dsn=settings.glitchtip_dsn,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        traces_sample_rate=0.0,
        send_default_pii=False,
        environment="production",
    )
    logger.info("Sentry/GlitchTip initialized")
else:
    logger.info("GLITCHTIP_DSN not set, Sentry disabled")


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
    return JSONResponse(
        status_code=400,
        content={"detail": exc.errors()},
    )


@app.get("/api/debug/sentry-test", include_in_schema=False)
async def sentry_test() -> dict[str, str]:
    """Temporary endpoint to verify GlitchTip integration. Remove after testing."""
    raise RuntimeError("Sentry test: intentional error to verify GlitchTip")
