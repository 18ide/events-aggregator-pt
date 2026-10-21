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

## Интеграции

### Capashino (уведомления)

`CAPASHINO_URL=http://student-system-capashino-web.student-system-capashino.svc:8000`

### GlitchTip (отслеживание ошибок)

LMS выдаёт внешний URL `glitchtip.dev-2.python-labs.ru`, но изнутри кластера
он недоступен (network policy блокирует egress на публичный IP). Используется
внутренний Kubernetes-сервис:

`GLITCHTIP_DSN=http://336cdcda4ff645eaa108a07a60250aa7@glitchtip-web.glitchtip.svc:80/<project_id>`

SDK: `sentry-sdk[fastapi]`. Инициализация — в `src/app/main.py`.
SSL-проверка отключена через кастомный transport (self-signed cert внутреннего CA).