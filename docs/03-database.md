# 03-database.md

Version: 1.1

Status: Active — updated incrementally as each phase in `05-task.md` lands. Sections for
entities not yet implemented are marked **Pending** with the phase that introduces them.
Source of truth priority is defined in `00-index.md`.

---

# 1. Database Philosophy

Polyglot persistence: each storage technology is used only for the workload it is best at
(docs/02-architecture.md section 144).

* PostgreSQL — transactional/relational metadata.
* PgVector (PostgreSQL extension) — embeddings and ANN search.
* Object Storage (MinIO / S3-compatible) — binary documents, OCR output, reports.
* Redis — cache, queue broker, session store.

Every table is version controlled via Alembic migrations, never modified manually in any
environment (docs/07-master_prompt.md Database Migration Rules).

---

# 2. Database Architecture

```
Application (SQLAlchemy 2.0 async, asyncpg driver)
        │
        ▼
Repository layer (backend/app/repositories) — CRUD, pagination, filtering only
        │
        ▼
PostgreSQL 16 + pgvector extension
```

Connection pooling is configured via SQLAlchemy's `create_async_engine` pool
(`DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW` in `backend/app/core/config.py`). A dedicated
PgBouncer layer is introduced when connection volume requires it (docs/02-architecture.md
section 200).

---

# 3. PostgreSQL Design

* Version: 16 (image `pgvector/pgvector:pg16`, see `docker/docker-compose.yml`).
* Access: async SQLAlchemy 2.0 ORM (`backend/app/db/session.py`), never raw psycopg outside the
  repository layer.
* Schema ownership: one Alembic migration history at `backend/alembic/versions`.

---

# 4. PgVector Design

The `vector` extension is enabled by the foundational migration
`backend/alembic/versions/20260703_0001_enable_pgvector_extension.py`.

Embedding tables (introduced in the Embedding Pipeline phase, not yet scheduled in
`05-task.md`) will store, per docs/02-architecture.md section 146:

```
chunk_id        UUID (FK)
embedding       vector(N)
model           text
dimensions      int
version         int
document_id     UUID (FK)
```

Default index: HNSW. Alternatives (IVF Flat, PQ) are evaluated per docs/02-architecture.md
section 201 once real query/recall data exists.

**Pending** — table definitions land with the Embedding Pipeline phase.

---

# 5. Object Storage Design

Bucket: `rag-documents` (configurable via `MINIO_BUCKET`). Created idempotently on backend
startup (`backend/app/core/storage.py::ensure_bucket_exists`, invoked from `app/main.py`
lifespan). Stores original uploads, OCR output, and generated reports — never inside
PostgreSQL (docs/06-rule.md Database Rules).

---

# 6. Multi Tenancy Strategy

**Pending — Phase 2 (Organization/Workspace/Project).** Every tenant-scoped table will carry
`organization_id` (and `workspace_id`/`project_id` where applicable) and every repository query
will filter on it, per docs/02-architecture.md section 122. No cross-tenant query is permitted
without an explicit filter.

---

# 7. UUID Strategy

Every table's primary key is a `UUID` (PostgreSQL native `uuid` type via
`sqlalchemy.dialects.postgresql.UUID`), generated client-side with `uuid.uuid4()` at the ORM
layer. Implemented once, in `backend/app/models/base.py::UUIDPrimaryKeyMixin`, and mixed into
every model — never redefined per table.

```python
class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
```

---

# 8. Audit Strategy

`backend/app/models/base.py::AuditMixin` adds nullable `created_by` / `updated_by` UUID columns
to any model that needs actor tracking. Immutable, append-only audit *log* tables (distinct
from these per-row audit columns) are introduced in the Authentication/RBAC phase
(docs/02-architecture.md section 132).

---

# 9. Soft Delete Strategy

`backend/app/models/base.py::SoftDeleteMixin` adds a nullable `deleted_at` timestamp. Repository
queries must filter `deleted_at IS NULL` by default; hard deletes are reserved for retention
purge jobs (docs/02-architecture.md section 163).

---

# 10. Versioning

Schema versioning uses Alembic's linear revision history (`backend/alembic/versions`). Domain
versioning (embeddings, prompts, experiments) is a separate application-level concept — see
docs/02-architecture.md sections 42 (Embedding Versioning) and 79 (Prompt Versioning) — and is
implemented starting with the phases that introduce those entities.

---

# 11. Repository Schema

**Pending — Phase 3.**

# 12. Project Schema

**Pending — Phase 2.**

# 13. User Schema

**Pending — Phase 1.**

# 14. Workspace Schema

**Pending — Phase 2.**

# 15. Document Schema

**Pending — Document Processing phase (after Phase 3).**

# 16. Chunk Schema

**Pending — Chunking Engine phase.**

# 17. Embedding Schema

**Pending — Embedding Pipeline phase.**

# 18. Retrieval Schema

**Pending — Retrieval Architecture phase.**

# 19. Prompt Schema

**Pending — Prompt Builder phase.**

# 20. Conversation Schema

**Pending — Conversation Memory phase.**

# 21. Memory Schema

**Pending — Conversation Memory phase.**

# 22. Evaluation Schema

**Pending — Evaluation Engine phase.**

# 23. Experiment Schema

**Pending — Evaluation Engine phase.**

# 24. Benchmark Schema

**Pending — Benchmarking Framework phase.**

# 25. Analytics Schema

**Pending — Analytics Pipeline phase.**

# 26. Audit Schema

**Pending — Phase 1 (Authentication/Security).**

# 27. API Keys Schema

**Pending — Phase 2 (Enterprise platform).**

# 28. Session Schema

**Pending — Phase 1.**

# 29. Notification Schema

**Pending — not yet scheduled in `05-task.md`.**

# 30. Queue Schema

Celery uses Redis directly as broker/result backend (see `worker/common/celery_app.py`); no
relational queue table exists. A Dead Letter Queue table is introduced alongside the Document
Processing phase per docs/02-architecture.md section 151.

---

# 31. Index Strategy

Mandatory indexes, per docs/06-rule.md Database Rules:

* Every foreign key.
* Every field used in `WHERE`/`ORDER BY` on tables expected to grow large (documents, chunks,
  audit logs).
* HNSW index on every `vector` column once embedding tables exist.

No index has been added yet beyond the implicit primary-key index, since no domain tables exist
before Phase 1.

---

# 32. Partitioning

**Pending.** Time-based partitioning is planned for `audit_logs` and usage/analytics tables once
they exist, per docs/02-architecture.md section 163.

---

# 33. Constraints

* `NOT NULL` on every required column.
* Foreign keys use `ON DELETE` behavior appropriate to the soft-delete strategy (`RESTRICT` by
  default; cascades are explicit, never implicit).
* Uniqueness constraints (e.g., slugs, emails) are added when the owning entity is implemented.

---

# 34. Foreign Keys

All foreign keys reference the UUID primary key of the parent table and are indexed
(docs/06-rule.md — "Never skip indexes on large tables").

---

# 35. Query Optimization

* Repositories only ever issue queries needed for the current use case (no `SELECT *` beyond
  ORM-mapped columns).
* Pagination uses `LIMIT`/`OFFSET` today (`backend/app/repositories/base.py`); keyset pagination
  is adopted for high-volume tables (chunks, audit logs) once they exist.
* N+1 queries are forbidden; eager-loading strategy is defined per relationship as models are
  added.

---

# 36. Row Level Security

**Pending — Phase 2.** Tenant isolation is enforced at the application/repository layer first;
PostgreSQL RLS is evaluated as defense-in-depth once the multi-tenant schema exists.

---

# 37. Backup Strategy

Local development: Docker named volumes (`postgres_data`, `minio_data` in
`docker/docker-compose.yml`). Production backup cadence (daily full + hourly incremental) is
defined in docs/02-architecture.md section 161 and implemented when a production environment is
provisioned.

---

# 38. Migration Strategy

* Tool: Alembic, async engine (`backend/alembic/env.py`), configured to read
  `Settings.database_url` rather than a hardcoded URL.
* One linear history under `backend/alembic/versions`; no branching migrations.
* Every migration implements both `upgrade()` and `downgrade()`.
* Migrations run via the `migrate` one-shot service in `docker/docker-compose.yml`
  (`alembic upgrade head`) before `backend`/`worker` start.
* Naming: `YYYYMMDD_NNNN_description.py`.

---

# 39. ER Diagram

**Pending.** Generated once entity schemas beyond Phase 0 exist; will be regenerated after each
phase that adds tables.

---

# 40. Naming Convention

* Tables: `snake_case`, plural (`documents`, `chunks`).
* Columns: `snake_case`.
* Primary key column: always `id`.
* Foreign key columns: `<singular_table>_id` (e.g., `document_id`).
* Migration files: `YYYYMMDD_NNNN_description.py`.

---

# 41. Sample Queries

No domain queries exist yet. The base repository (`backend/app/repositories/base.py`) provides
`get_by_id`, `list`, `add`, `delete` — every domain repository extends this rather than
reimplementing CRUD.

---

# 42. Best Practices

* Never bypass the repository layer for data access.
* Never store large binaries in PostgreSQL — use object storage.
* Always add indexes for foreign keys and frequently filtered/sorted columns before a table
  reaches production traffic, not after.
* Every new table adds `UUIDPrimaryKeyMixin` + `TimestampMixin`, and `SoftDeleteMixin` /
  `AuditMixin` where applicable (`backend/app/models/base.py`).
