# Events Aggregator

Backend-сервис-агрегатор для Events Provider API.

## Стек

- Python 3.11+, FastAPI, SQLAlchemy 2.x async, PostgreSQL, Alembic
- uv, Ruff, pytest, GitHub Actions

## Локальный запуск

1. `cp .env.example .env` и заполнить
2. `docker compose up -d`
3. `uv sync`
4. `uv run alembic upgrade head`
5. `uv run uvicorn app.main:app --reload --app-dir src`

Swagger: http://localhost:8000/docs

## Проверки

- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run pytest`