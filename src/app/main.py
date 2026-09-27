from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # здесь позже запустим фоновый воркер синхронизации
    yield
    # здесь позже аккуратно его остановим


app = FastAPI(
    title="Events Aggregator",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router, prefix="/api")
