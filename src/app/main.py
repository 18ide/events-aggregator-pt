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
from sentry_sdk.transport import HttpTransport

from app.api.routers import events, health, sync, tickets
from app.core.config import settings
from app.core.logging import configure_logging
from app.errors import DomainError
from app.services.outbox import outbox_worker
from app.services.worker import sync_worker

logger = logging.getLogger(__name__)


class NoSslVerifyTransport(HttpTransport):
    """HttpTransport that skips SSL verification (for self-signed GlitchTip CA).

    Not used when DSN is http://, but kept in case it flips back to https.
    """

    def _get_pool(self):
        from urllib3 import PoolManager
        from urllib3.util.retry import Retry

        return PoolManager(
            num_pools=10,
            maxsize=10,
            cert_reqs="CERT_NONE",
            retries=Retry(0),
        )


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
        transport=NoSslVerifyTransport,
    )
    logger.info("Sentry/GlitchTip initialized")
else:
    logger.info("GLITCHTIP_DSN not set, Sentry disabled")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Events Aggregator")
    sync_task = asyncio.create_task(sync_worker())
    outbox_task = asyncio.create_task(outbox_worker())
    try:
        yield
    finally:
        logger.info("Shutting down Events Aggregator")
        sync_task.cancel()
        outbox_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sync_task
        with contextlib.suppress(asyncio.CancelledError):
            await outbox_task


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
