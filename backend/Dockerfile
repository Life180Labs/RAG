# --- Build stage ---
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install .
# tiktoken defaults to caching under `$TMPDIR/data-gym-cache`, which — unlike
# `/install` — is never copied into the runtime stage below, so pointing it
# at an explicit directory here is required for the download below to
# actually survive into the final image (a plain default-location "pre-cache"
# RUN would silently do nothing across this multi-stage build).
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken_cache
RUN python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"

# --- Runtime stage ---
FROM python:3.11-slim AS runtime

WORKDIR /app
ENV PYTHONPATH=/app
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken_cache

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

COPY --from=builder /install /usr/local
COPY --from=builder /opt/tiktoken_cache /opt/tiktoken_cache
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/live || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
