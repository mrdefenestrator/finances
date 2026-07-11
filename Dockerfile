FROM python:3.12-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev


FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /app/.venv ./.venv

COPY finances/ ./finances/
COPY web/ ./web/
COPY migrations/ ./migrations/
COPY finances.py ./
COPY alembic.ini ./

EXPOSE 5001

ENV FINANCES_DB=/app/data/finances.db

CMD ["sh", "-c", "mkdir -p /app/data && .venv/bin/alembic upgrade head && .venv/bin/flask --app web/app.py run --host 0.0.0.0 --port 5001"]
