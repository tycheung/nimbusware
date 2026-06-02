# syntax=docker/dockerfile:1

FROM python:3.11-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir poetry==2.1.3
COPY pyproject.toml poetry.lock ./
COPY packages ./packages
RUN poetry config virtualenvs.create false \
  && poetry install --only main --no-interaction --no-ansi

FROM python:3.11-slim AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
  NIMBUSWARE_REPO_ROOT=/app \
  HERMES_SKIP_PREFLIGHT=1 \
  NIMBUSWARE_API_HOST=0.0.0.0 \
  PORT=8000
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY pyproject.toml poetry.lock ./
COPY packages ./packages
COPY configs ./configs
COPY scripts ./scripts
EXPOSE 8000
CMD ["nimbusware-api"]
