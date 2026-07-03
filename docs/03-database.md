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

Implemented (migration `0003_add_tenancy_tables`, models `backend/app/models/organization.py`,
`workspace.py`, `project.py`). The hierarchy is Organization → Workspace → Project, each carrying
its parent's ID (`workspace.organization_id`, `project.workspace_id`) and enforcing it via a
composite unique slug constraint (`uq_workspace_org_slug`, `uq_project_workspace_slug`) so slugs
only need to be unique within their parent, not globally.

```
organizations
      │
      ├── organization_members  (role: owner | admin | developer | viewer)
      │
      └── workspaces
                │
                ├── workspace_members  (role: owner | admin | developer | viewer)
                │
                └── projects
                          │
                          └── project_members  (role: owner | admin | developer | viewer)
```

**Deliberate MVP simplification — explicit membership, no role inheritance.** Every
`require_*_role` dependency (`backend/app/api/tenancy_deps.py`) checks a membership row at
*that exact level*; an organization ADMIN/OWNER does **not** automatically gain access to every
workspace or project under their organization. Creating a workspace requires an organization
role (ADMIN+), but managing it afterward requires a `workspace_members` row — auto-granted OWNER
to whoever created it. The same pattern repeats one level down for projects. This keeps the
access-control model simple and auditable (one row = one grant) at the cost of requiring
explicit re-invitation into child resources; revisit with role inheritance if that friction
proves real once more phases land.

`role_meets_minimum()` (`backend/app/models/membership.py`) ranks roles
`viewer < developer < admin < owner` for every `require_*_role(minimum)` check.

Organization invitations (`invitations` table) are the only cross-cutting mechanism: accepting
one creates an `organization_members` row directly — there is no separate workspace/project
invitation flow yet.

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

Implemented in `backend/app/models/repository.py`, migration `0004_add_repository_tables`. (This
is the "Repository" *resource* — a container for documents/embeddings/evaluations/experiments —
distinct from the `app/repositories/` data-access layer, which already exists for every table.)

```
repositories
  id                       UUID PK
  project_id               UUID FK -> projects.id, ON DELETE CASCADE, indexed
  name                     varchar(255)
  slug                     varchar(255)          -- unique within project (uq_repository_project_slug)
  description              text, nullable
  status                   enum(active, archived)

  -- Settings: identifiers only. The chunking/embedding/retrieval/reranking/prompt engines
  -- these select are implemented in later phases; storing the setting now doesn't imply
  -- the engine exists yet.
  default_chunk_strategy   varchar(100), nullable
  default_embedding_model  varchar(100), nullable
  default_retriever        varchar(100), nullable
  default_reranker         varchar(100), nullable
  default_prompt_version   varchar(100), nullable

  -- Statistics: start at zero, incremented by the document/chunk/embedding/retrieval
  -- phases once they exist.
  document_count           int, default 0
  chunk_count              int, default 0
  embedding_count          int, default 0
  storage_used_bytes       bigint, default 0
  retrieval_count          int, default 0

  created_at / updated_at timestamptz
  deleted_at               timestamptz, nullable
  created_by / updated_by  UUID, nullable

repository_members
  id             UUID PK
  repository_id  UUID FK -> repositories.id, ON DELETE CASCADE, indexed
  user_id        UUID FK -> users.id, ON DELETE CASCADE, indexed
  role           enum(owner, admin, developer, viewer)
  created_at / updated_at timestamptz
  UNIQUE(repository_id, user_id)  -- uq_repository_member
```

Creating a repository auto-creates a `repository_members` row with `role = owner` for the
creator — the same explicit-membership pattern as workspaces/projects (section 6). "Activity"
(docs/05-task.md Phase 3) is served by querying `audit_logs` filtered on
`resource = repository_id` rather than a dedicated activity table — the audit log already
captures every mutation.

**Explicitly not implemented**: Clone/Duplicate/Export/Import (docs/05-task.md Phase 3
Repository Features) only make sense once documents/embeddings exist to actually copy or move,
which is a later phase; Custom Roles and a Permission Matrix remain deferred from Phase 2 for
the same reasons given there.

# 12. Project Schema

Implemented in `backend/app/models/project.py`, migration `0003_add_tenancy_tables`.

```
projects
  id                      UUID PK
  workspace_id            UUID FK -> workspaces.id, ON DELETE CASCADE, indexed
  name                    varchar(255)
  slug                    varchar(255)            -- unique within workspace (uq_project_workspace_slug)
  status                  enum(active, archived)
  owner_id                UUID FK -> users.id, ON DELETE SET NULL, nullable
  created_at / updated_at timestamptz
  deleted_at              timestamptz, nullable
  created_by / updated_by UUID, nullable

project_members
  id           UUID PK
  project_id   UUID FK -> projects.id, ON DELETE CASCADE, indexed
  user_id      UUID FK -> users.id, ON DELETE CASCADE, indexed
  role         enum(owner, admin, developer, viewer)
  created_at / updated_at timestamptz
  UNIQUE(project_id, user_id)  -- uq_project_member
```

Creating a project auto-creates a `project_members` row with `role = owner` for the creator (see
docs/03-database.md section 6 for why this — not org/workspace role inheritance — is what grants
access).

# 13. User Schema

Implemented in `backend/app/models/user.py`, migration
`backend/alembic/versions/20260703_0002_add_auth_tables.py`.

```
users
  id                      UUID PK
  email                   varchar(320) UNIQUE, indexed
  hashed_password         varchar(255)          -- argon2 (passlib)
  full_name               varchar(255)
  role                    enum(admin, developer, researcher, viewer) -- platform-wide role,
                                                                       -- distinct from per-tenant
                                                                       -- MemberRole (section 6)
  is_active               boolean
  failed_login_attempts   int
  locked_until            timestamptz, nullable  -- account lockout (5 failures -> 15 min)
  last_login_at           timestamptz, nullable
  created_at / updated_at timestamptz
  deleted_at              timestamptz, nullable  -- soft delete
```

New accounts default to `role = viewer`. This platform-wide `UserRole` (`user_role` enum) was
kept separate from the tenant-scoped `MemberRole` (`member_role` enum — owner/admin/developer/
viewer, section 6) introduced in Phase 2 rather than merged: a user's standing at the platform
level (e.g., can they use admin-only future endpoints at all) is a different concern from their
role within a specific organization/workspace/project, and conflating them would force every
tenant-scoped permission check to also reason about platform role.

# 14. Workspace Schema

Implemented in `backend/app/models/workspace.py`, migration `0003_add_tenancy_tables`.

```
workspaces
  id                      UUID PK
  organization_id         UUID FK -> organizations.id, ON DELETE CASCADE, indexed
  name                    varchar(255)
  slug                    varchar(255)            -- unique within organization (uq_workspace_org_slug)
  status                  enum(active, archived)
  created_at / updated_at timestamptz
  deleted_at              timestamptz, nullable
  created_by / updated_by UUID, nullable

workspace_members
  id            UUID PK
  workspace_id  UUID FK -> workspaces.id, ON DELETE CASCADE, indexed
  user_id       UUID FK -> users.id, ON DELETE CASCADE, indexed
  role          enum(owner, admin, developer, viewer)
  created_at / updated_at timestamptz
  UNIQUE(workspace_id, user_id)  -- uq_workspace_member
```

Creating a workspace requires organization role ADMIN+ but auto-creates a `workspace_members`
row with `role = owner` for the creator — see section 6 for why organization role alone doesn't
grant ongoing workspace access.

# 15. Document Schema

Implemented in `backend/app/models/document.py`, migration `0005_add_document_tables`.

```
documents
  id                      UUID PK
  repository_id           UUID FK -> repositories.id, ON DELETE CASCADE, indexed
  filename                varchar(500)
  mime_type               varchar(255)
  size_bytes              bigint
  sha256_hash             varchar(64), indexed  -- dedup key within a repository
  storage_key             varchar(1000)         -- object key: documents/{repo}/{doc}/v{n}/{filename}
  status                  enum(document_status)  -- see state machine below
  status_message          varchar(500), nullable -- populated on any failed_* status
  current_version         int, default 1
  language                varchar(10), nullable  -- populated by a later (parsing) phase
  page_count              int, nullable          -- populated by a later (parsing) phase
  uploaded_by             UUID FK -> users.id, ON DELETE SET NULL, nullable
  created_at / updated_at timestamptz
  deleted_at              timestamptz, nullable
  created_by / updated_by UUID, nullable

document_versions
  id            UUID PK
  document_id   UUID FK -> documents.id, ON DELETE CASCADE, indexed
  version       int
  filename / mime_type / size_bytes / sha256_hash / storage_key  -- own copy, immutable snapshot
  status        enum(document_status)
  created_at    timestamptz
  created_by    UUID FK -> users.id, ON DELETE SET NULL, nullable
  UNIQUE(document_id, version)  -- uq_document_version

upload_sessions
  id             UUID PK
  repository_id  UUID FK -> repositories.id, ON DELETE CASCADE, indexed
  user_id        UUID FK -> users.id, ON DELETE SET NULL, nullable
  document_id    UUID FK -> documents.id, ON DELETE SET NULL, nullable
  filename       varchar(500)
  status         enum(upload_session_status: pending, completed, failed)
  error_message  varchar(1000), nullable
  created_at / updated_at timestamptz
```

`document_status` state machine (docs/02-architecture.md section 46): `uploaded -> validating ->
validated -> parsing -> ocr -> cleaning -> chunking -> embedding -> indexing -> ready`, with a
parallel `failed_upload` / `failed_validation` / `failed_parse` / `failed_ocr` / `failed_chunk` /
`failed_embed` / `failed_index` at each stage. Only `uploaded` / `validating` / `validated` /
`failed_validation` are reachable today — the backend validates and stores the file synchronously
(size/extension/password-protection/virus-scan-stub, `backend/app/core/document_validation.py`),
then enqueues `document_worker.finalize_upload` (`worker/document_worker/tasks.py`) which confirms
the object actually landed in MinIO and flips `uploaded -> validated` (or `failed_validation`).
Parsing/OCR/chunking/embedding/indexing continue this same state machine in later phases.

`DocumentVersion` is **not** given `TimestampMixin` — each row is an immutable snapshot of one
upload, so it owns a plain `created_at`/`created_by` rather than a mutable `updated_at`.

Uploading, soft-deleting, and restoring a document keep `Repository.document_count` and
`.storage_used_bytes` in sync (`DocumentService._bump_repository_stats`, floored at zero) — this
is the one set of repository statistics actually populated today; `chunk_count` /
`embedding_count` / `retrieval_count` remain zero until their phases exist.

Duplicate detection is per-repository, by `sha256_hash` (`get_by_hash_in_repository`) — uploading
identical bytes into the same repository is rejected with `DUPLICATE_DOCUMENT`; the same bytes in
two different repositories are unrelated documents.

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

Implemented in `backend/app/models/audit_log.py`. Immutable/append-only: no `updated_at`, no
soft delete, per docs/06-rule.md.

```
audit_logs
  id           UUID PK
  user_id      UUID FK -> users.id, ON DELETE SET NULL, nullable, indexed
  action       varchar(100), indexed              -- e.g. "login", "register", "password_reset"
  resource     varchar(255), nullable
  ip_address   varchar(64), nullable
  result       varchar(20)                          -- "success" | "failure" | "locked"
  created_at   timestamptz, indexed
```

Written by `AuthService` for register/login (success and failure)/logout/password_reset. Broader
audit coverage (permission changes, uploads, deletes) expands as those features ship.

# 27. API Keys Schema

**Pending — not yet scheduled in `05-task.md`.** Phase 2 as scoped implemented the
organization/workspace/project hierarchy, membership, and invitations, but did not include API
key management.

---

# Organization and Invitation Schema (no dedicated section number in the original TOC)

**Organizations** — implemented in `backend/app/models/organization.py`, migration
`0003_add_tenancy_tables`:

```
organizations
  id                      UUID PK
  name                    varchar(255)
  slug                    varchar(255) UNIQUE, indexed
  status                  enum(active, archived)
  created_at / updated_at timestamptz
  deleted_at              timestamptz, nullable
  created_by / updated_by UUID, nullable

organization_members
  id               UUID PK
  organization_id  UUID FK -> organizations.id, ON DELETE CASCADE, indexed
  user_id          UUID FK -> users.id, ON DELETE CASCADE, indexed
  role             enum(owner, admin, developer, viewer)
  invited_by       UUID FK -> users.id, ON DELETE SET NULL, nullable
  joined_at        timestamptz
  UNIQUE(organization_id, user_id)  -- uq_org_member
```

Creating an organization always creates its first `organization_members` row with
`role = owner` — there is no such thing as an organization with zero owners.

**Invitations** — implemented in `backend/app/models/invitation.py`:

```
invitations
  id               UUID PK
  organization_id  UUID FK -> organizations.id, ON DELETE CASCADE, indexed
  email            varchar(320), indexed
  role             enum(owner, admin, developer, viewer)  -- role granted on acceptance
  invited_by       UUID FK -> users.id, ON DELETE CASCADE
  token_hash       varchar(255) UNIQUE   -- sha256(raw token); raw token never persisted
  status           enum(pending, accepted, rejected, expired)
  expires_at       timestamptz            -- 7-day TTL
  accepted_at      timestamptz, nullable
  created_at / updated_at timestamptz
```

Expiry is checked lazily (on accept/reject), not via a scheduled job — Celery Beat isn't wired up
yet (docs/02-architecture.md section 166). No email service exists yet either; the raw invite
token is returned directly in the API response only when `DEBUG=true`, mirroring the Phase 1
password-reset pattern.

# 28. Session Schema

Implemented in `backend/app/models/session.py`. One row per issued refresh token; refresh
rotates the row's hash in place rather than inserting a new row.

```
sessions
  id                  UUID PK
  user_id             UUID FK -> users.id, ON DELETE CASCADE, indexed
  refresh_token_hash  varchar(255) UNIQUE            -- sha256(raw refresh token); raw token
                                                        never stored
  device              varchar(255), nullable
  ip_address          varchar(64), nullable
  user_agent          varchar(512), nullable
  last_activity_at    timestamptz
  expires_at          timestamptz
  revoked_at          timestamptz, nullable          -- set on logout
  created_at / updated_at timestamptz
```

Password-reset tokens are intentionally *not* stored here — they're single-use, short-TTL
(30 min), and live only in Redis (`password_reset:<sha256(token)> -> user_id`) so a stolen
reset token can't be replayed and never touches durable storage.

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

Applied so far: `users.email` (unique), `sessions.user_id`, `audit_logs.user_id`,
`audit_logs.action`, `audit_logs.created_at` (migration `0002_add_auth_tables`);
`organizations.slug` (unique), `organization_members.organization_id`/`.user_id`,
`workspaces.organization_id`, `workspace_members.workspace_id`/`.user_id`,
`projects.workspace_id`, `project_members.project_id`/`.user_id`,
`invitations.organization_id`/`.email` (migration `0003_add_tenancy_tables`).

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
