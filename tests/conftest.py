import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/events",
)
os.environ.setdefault("EVENTS_PROVIDER_URL", "http://localhost:8000")
os.environ.setdefault("EVENTS_PROVIDER_API_KEY", "test")
os.environ.setdefault("CAPASHINO_URL", "http://localhost:9999")
os.environ.setdefault("CAPASHINO_API_KEY", "test")
