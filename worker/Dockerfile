FROM python:3.11-slim AS builder
WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY common ./common
COPY document_worker ./document_worker
COPY chunk_worker ./chunk_worker
COPY embedding_worker ./embedding_worker
COPY retrieval_worker ./retrieval_worker
COPY evaluation_worker ./evaluation_worker
COPY benchmark_worker ./benchmark_worker
COPY scheduler ./scheduler

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install .
RUN PYTHONPATH=/install/lib/python3.11/site-packages python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"
RUN PYTHONPATH=/install/lib/python3.11/site-packages:. python -c "from embedding_worker.providers.local import LOCAL_MODEL_NAMES, _load_model; _load_model(LOCAL_MODEL_NAMES['bge'])"

FROM python:3.11-slim AS runtime
WORKDIR /app
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 appuser
COPY --from=builder /install /usr/local
COPY --from=builder /build/common ./common
COPY --from=builder /build/document_worker ./document_worker
COPY --from=builder /build/chunk_worker ./chunk_worker
COPY --from=builder /build/embedding_worker ./embedding_worker
COPY --from=builder /build/retrieval_worker ./retrieval_worker
COPY --from=builder /build/evaluation_worker ./evaluation_worker
COPY --from=builder /build/benchmark_worker ./benchmark_worker
COPY --from=builder /build/scheduler ./scheduler

USER appuser

CMD ["celery", "-A", "common.celery_app", "worker", "--loglevel=info"]
