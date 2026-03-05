FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install runtime dependencies (no dev deps)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy app source
COPY finances/ ./finances/
COPY web/ ./web/
COPY finances.py ./
COPY validate_yaml.py ./
COPY schema.yaml ./

EXPOSE 5001

# Default data path — override by mounting a volume and setting this env var
ENV FINANCES_DATA=/data/finances.yaml

CMD [".venv/bin/flask", "--app", "web/app.py", "run", "--host", "0.0.0.0", "--port", "5001"]
