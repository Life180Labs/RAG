# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Enterprise RAG Studio: a production-grade, fully observable Retrieval-Augmented Generation platform. Every pipeline stage (parsing, chunking, embedding, indexing, retrieval, reranking, prompting, generation, evaluation) is inspectable, measurable, and reproducible. Built in 25 sequential phases defined in `docs/05-task.md`; current progress is tracked there and in this session's task list.

## Documentation-first workflow (mandatory)

This repo is driven by a fixed documentation set in `docs/`, read in this exact order (never skip, never reorder): `00-index.md` → `01-project.md` → `02-architecture.md` → `03-database.md` → `04-api-spec.md` → `05-task.md` → `06-rule.md` → `07-master_prompt.md`.

- **Source-of-truth precedence** when documents conflict: User Requirements > `07-master_prompt.md` > `02-architecture.md` > `03-database.md` > `04-api-spec.md` > `06-rule.md` > `05-task.md` > `01-project.md`. If a conflict can't be resolved by this order, stop and ask — never guess.
- **One phase at a time.** Verify the previous phase's acceptance criteria are met before starting the next; don't implement future phases early.
- **Docs must stay in sync with code.** Any change to schema, API, or architecture requires updating `03-database.md`, `04-api-spec.md`, and `02-architecture.md`, plus checking off the relevant item in `05-task.md`, in the same change.
- `06-rule.md` is the engineering constitution (layered architecture, RBAC/security, testing coverage targets, forbidden practices). Read it before making structural changes.

## Common commands

**Backend** (`backend/`, FastAPI + async SQLAlchemy):
```bash
pip install -e ".[dev]"
ruff check app tests          # lint
mypy app                      # type check (non-blocking in CI)
alembic upgrade head          # apply migrations
alembic revision --autogenerate -m "..."   # new migration
pytest --cov=app --cov-report=term-missing # full suite
pytest tests/test_vector_indexes.py -k test_name  # single test
```

**Worker** (`worker/`, Celery + sync psycopg3 driver):
```bash
pip install -e ".[dev]"
ruff check .
pytest
pytest tests/test_build_index.py -k test_name
```
Worker tests hit the real dockerized Postgres/Redis/Qdrant/Chroma stack — **always run `docker compose -f docker/docker-compose.yml --env-file .env stop worker` before running worker tests or ad hoc scripts locally**, then `start worker` afterward. Otherwise the live worker container and your local process both consume the same Celery task from Redis, racing to insert the same row and producing spurious `ForeignKeyViolation` errors that look like ordering bugs but aren't.

**Frontend** (`frontend/`, Next.js):
```bash
npm run dev
npm run lint
npm run typecheck
npm run format:check
npm run build
```

**Full stack:**
```bash
cp .env.example .env
docker compose -f docker/docker-compose.yml up --build
```
Frontend http://localhost:3000, Backend http://localhost:8000 (`/docs` for OpenAPI), MinIO console http://localhost:9001, Qdrant http://localhost:6333, Chroma http://localhost:8001→8000.

CI (`.github/workflows/ci.yml`) runs backend/worker/frontend jobs in parallel plus a Docker build-validation job; mirror its steps (including running migrations before worker tests) when adding new checks.

## Architecture

**Layered, three-service monorepo**: `backend/` (FastAPI API), `worker/` (Celery background processing), `frontend/` (Next.js), sharing one Postgres+pgvector database and one Redis broker, plus MinIO (object storage), Qdrant and Chroma (self-hosted vector DBs). Backend uses async SQLAlchemy 2.0 + asyncpg; worker uses sync SQLAlchemy + psycopg3 — they are separate installable packages (`backend/pyproject.toml`, `worker/pyproject.toml`), not sharing a virtualenv.

**Backend layering** (enforced, not optional): `Controller → Service → Repository → Database`. Controllers only do auth/validation/calling services; business logic and SQL never belong there. Business logic and transactions live in services; CRUD/queries live in repositories.

**Worker packages**: `document_worker`, `chunk_worker`, `embedding_worker`, `index_worker`, `retrieval_worker`, `evaluation_worker`, `benchmark_worker` are independent deployables registered against one shared `worker/common/celery_app.py`. They communicate by **Celery task name** via `celery_app.send_task("<worker>.<task>", args=[...])`, never by importing across worker packages. When adding a new worker package, it must be added to `celery_app.py`'s `autodiscover_tasks([...])` list — a package can pass all direct-call unit tests (`task.run(...)`) while still being invisible to the real Celery broker if this is missed (this happened with `index_worker` in Phase 8; only live e2e caught it, since tests calling `.run()` bypass Celery's task-registration path entirely).

**Document pipeline**: a state machine (`DocumentStatus` enum) driving one document through `uploaded → validating → validated → parsing → [ocr] → cleaning → chunking → embedding → indexing → ready`, with parallel `failed_*` states per stage. Each stage's Celery task enqueues the next stage's task by name on success (`finalize_upload → parse_document → chunk_document → embed_chunk_set → build_index`). No stage calls the next stage's code directly.

**Regeneration reuses IDs**: re-running the same (parent, key) combination (e.g. re-chunking a document with the same strategy, or rebuilding the same embedding version) updates the existing row and bumps a `version` column rather than inserting a duplicate. This is required because child tables FK-reference the parent row's `id` with no `ON UPDATE CASCADE` — a new id would orphan children.

**Vector index namespace**: `namespace = str(embedding_version_id)` uniformly across all vector providers (Postgres partial-index suffix, Qdrant/Chroma/Pinecone collection name) — a deterministic 1:1 mapping from embedding version to index identity.

**Delete-is-enqueue-only** for vector indexes: `DELETE .../index/{id}` never synchronously deletes the tracking row, since the actual vector data may live in an external store (Qdrant/Chroma/Pinecone). It only enqueues `index_worker.delete_index`, which deletes from the provider then removes the row itself.

## Known gotchas

- **SQLAlchemy reserves `metadata`** as an attribute name on declarative models (shadows `Base.metadata`). JSONB "metadata" columns are named `metadata_payload` (see `backend/app/models/vector_index.py`), not `metadata`.
- **psycopg3 can't infer bound-parameter types inside `CREATE INDEX ... WHERE` predicates** (`IndeterminateDatatype`, even with explicit `CAST(:param AS uuid)`). Where DDL needs a dynamic predicate (see `worker/index_worker/providers/pgvector_provider.py`), validate the value first (e.g. `str(uuid.UUID(namespace))`) then embed it as a literal in the SQL string — only safe because that value is always server-generated, never user input.
- **AuthGuard/AuthProvider race condition** (frontend, unfixed): a full page reload (`window.location.href`, `location.reload()`) on a protected route can bounce to `/login` even with a valid token. Workaround: use client-side navigation only (`<Link>`, `history.back()`) when testing protected routes in a browser.
- `frontend/AGENTS.md` flags that this repo's Next.js version (16.2.10) has breaking changes vs. training data — check `frontend/node_modules/next/dist/docs/` before writing new Next.js code.

## Testing philosophy

Tests run against real infrastructure (Postgres, Redis, MinIO, Qdrant, Chroma) — never mocked. Alembic migrations must be verified upgrade→downgrade→upgrade round-trip against a live database, not just applied once. Coverage targets from `06-rule.md`: backend ≥90%, critical logic ≥95%.

## Git conventions

Never commit directly to `main`/`develop`. Branches: `feature/*`, `bugfix/*`, `hotfix/*`, `release/*`. Conventional commits describing intent: `feat(scope): ...`, `fix(scope): ...`, `refactor(scope): ...`, `docs(scope): ...`, `test(scope): ...`.
