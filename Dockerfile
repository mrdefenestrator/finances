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
COPY finances.py ./
COPY validate_yaml.py ./
COPY schema.yaml ./

EXPOSE 5001

ENV FINANCES_DATA=/app/data/finances.yaml

CMD [".venv/bin/flask", "--app", "web/app.py", "run", "--host", "0.0.0.0", "--port", "5001"]
