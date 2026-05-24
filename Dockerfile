FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock* ./

RUN uv sync --frozen --no-dev


FROM python:3.13-slim

WORKDIR /app

COPY --from=builder /app/.venv ./.venv

COPY src/ ./src/
COPY migrations/ ./migrations/
COPY src/main.py ./

ENV PATH="/app/.venv/bin:$PATH"

CMD ["sh", "-c", "python -m src.main migrate && python -m src.main run"]