# Enterprise RAG Studio

Enterprise RAG Studio is a production-grade, fully observable Retrieval-Augmented Generation platform. Every stage of the RAG pipeline — parsing, chunking, embedding, retrieval, reranking, prompting, generation, and evaluation — is inspectable, measurable, and reproducible.

See [`docs/00-index.md`](docs/00-index.md) for the full documentation set and required reading order before contributing.

## Repository Layout

```
backend/    FastAPI application (API, services, repositories, AI engines)
frontend/   Next.js application
worker/     Celery worker processes (document, chunk, embedding, evaluation)
docker/     Dockerfiles and compose configuration
docs/       Architecture, database, API, task, and rule documentation
scripts/    Developer and operational scripts
tests/      Cross-service integration/e2e tests
```

## Quick Start (Local Development)

Prerequisites: Docker and Docker Compose.

```bash
cp .env.example .env
docker compose -f docker/docker-compose.yml up --build
```

Services:

| Service  | URL                              |
|----------|-----------------------------------|
| Frontend | http://localhost:3000            |
| Backend  | http://localhost:8000             |
| API Docs | http://localhost:8000/docs        |
| MinIO Console | http://localhost:9001         |

## Documentation

Start at [`docs/00-index.md`](docs/00-index.md). Documentation must be read in the order it defines before making changes.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

See [`LICENSE`](LICENSE).
