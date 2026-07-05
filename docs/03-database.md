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
`failed_embed` / `failed_index` at each stage. `uploaded` through `chunking` are reachable today:
the backend validates and stores the file synchronously
(size/extension/password-protection/virus-scan-stub, `backend/app/core/document_validation.py`),
then a `BackgroundTasks`-scheduled call (see below) enqueues `document_worker.finalize_upload`
(`uploaded -> validated`/`failed_validation`), which itself enqueues
`document_worker.parse_document` (`validated -> parsing -> [ocr] -> cleaning -> chunking`, or
`failed_parse`/`failed_ocr`) once storage is confirmed. `chunking` is the "ready for the next
phase" marker — Phase 6 (Chunking Engine) is what actually advances a document past it, the same
way `validated` meant "ready for parsing" before Phase 5 existed. Embedding/indexing/ready
continue this state machine in their own future phases.

`DocumentVersion` is **not** given `TimestampMixin` — each row is an immutable snapshot of one
upload, so it owns a plain `created_at`/`created_by` rather than a mutable `updated_at`.

Uploading, soft-deleting, and restoring a document keep `Repository.document_count` and
`.storage_used_bytes` in sync (`DocumentService._bump_repository_stats`, floored at zero) — this
is the one set of repository statistics actually populated today; `chunk_count` /
`embedding_count` / `retrieval_count` remain zero until their phases exist.

Duplicate detection is per-repository, by `sha256_hash` (`get_by_hash_in_repository`) — uploading
identical bytes into the same repository is rejected with `DUPLICATE_DOCUMENT`; the same bytes in
two different repositories are unrelated documents.

**Enqueue timing bug (found via live e2e testing, fixed in Phase 5):** `DocumentService.upload`/
`.create_new_version` run inside the request's still-open DB transaction (`get_db` only commits
after the route handler returns — see `backend/app/db/session.py`). The original code called
`enqueue_finalize_upload` from inside the service, so a fast worker could query for the document
*before* Postgres had actually committed it, reliably reproducing `document_not_found` once the
worker's pickup latency dropped low enough. Fixed by moving the enqueue call to the controller via
FastAPI's `BackgroundTasks`, which only run after the response — and therefore after `get_db`'s
commit — have completed (`app/api/v1/documents.py`).

## Document Content (Phase 5)

Implemented in `backend/app/models/document_content.py`, migration
`0006_add_document_content_table`. Populated by `document_worker.parse_document`
(`worker/document_worker/tasks.py`), not by the backend.

```
document_content
  id                     UUID PK
  document_id            UUID FK -> documents.id, ON DELETE CASCADE, indexed, UNIQUE
  version                int                    -- which document_versions.version this parse is of
  raw_text               text                   -- cleaned, flattened prose (all non-image blocks)
  structured_content     jsonb                  -- ordered typed blocks — see below
  language               varchar(10), nullable  -- ISO 639-1, via langdetect
  page_count             int, nullable          -- PDF only; DOCX/HTML/etc. have no fixed pagination
  word_count             int, nullable
  character_count        int, nullable
  reading_time_seconds   int, nullable          -- word_count / 200wpm
  parser_used            varchar(50)            -- "pymupdf" | "python-docx" | "beautifulsoup4" |
                                                 -- "markdown-it-py" | "native" | "pandas" | "lxml"
  ocr_used               boolean, default false
  ocr_confidence         float, nullable        -- mean Tesseract word confidence (0-100) across
                                                 -- OCR'd pages only, when ocr_used is true
  created_at / updated_at timestamptz
  UNIQUE(document_id)  -- uq_document_content_document
```

One row per *document* (not per version) — re-parsing (e.g. after a new version is uploaded)
overwrites this row via `ON CONFLICT (document_id) DO UPDATE`, since only the current version's
content ever feeds later phases (chunking/embedding); history isn't kept here (the immutable
`document_versions` table already has each version's raw bytes if re-parsing an old version is
ever needed).

`structured_content` is an ordered array of typed blocks — parsers never flatten a document to
plain text (docs/02-architecture.md section 30):

```
{"type": "title" | "heading" | "paragraph" | "list" | "table" | "code" | "image",
 "text": "...", "level": int | null, "page": int | null}
```

`level` is only set for `heading` blocks (1 = h1/Heading 1/etc.); `page` is only set for PDF blocks
(every other format has no fixed pagination, so it's always `null`). Structure is inferred per
format rather than via a separate structure-detection pass: PDF uses font-size ratios (via
PyMuPDF) plus `page.find_tables()` for real table detection; DOCX/HTML/Markdown use their native
style/tag/token markup; TXT/CSV/JSON/XML have no real structure, so CSV/JSON become a single
table/code block and TXT/XML are split into paragraphs.

OCR (`document_worker/parsing/ocr.py`, Tesseract via `pytesseract`/`pdf2image`) only runs on PDF
pages where the text layer PyMuPDF extracted is near-empty (<20 characters) — a real scanned page,
not a re-OCR of already-correct text. EasyOCR/PaddleOCR/cloud OCR providers are documented
alternatives in docs/02-architecture.md section 26 but not implemented; Tesseract is the one real,
tested engine for this phase (same "implement one real path, document the rest as deferred"
pattern as Phase 4's virus-scan stub).

Retries/DLQ: `parse_document` uses Celery's `autoretry_for` (3 attempts, exponential backoff).
There's no separate dead-letter queue infrastructure — once retries are exhausted, the persisted
`FAILED_PARSE`/`FAILED_OCR` status and `status_message` on `documents` *is* the dead-letter record,
consistent with how Phase 4 already surfaces failures.

# 16. Chunk Schema (Phase 6)

Implemented in `backend/app/models/chunk.py`, migration `0007_add_chunk_tables`. Populated by
`chunk_worker.chunk_document` (`worker/chunk_worker/tasks.py`), reading Phase 5's
`document_content.structured_content` blocks — never the flattened `raw_text`, so headings/lists/
tables stay available as chunk boundaries.

```
document_chunk_sets
  id                UUID PK
  document_id       UUID FK -> documents.id, ON DELETE CASCADE, indexed
  version           int                     -- documents.current_version at chunk-time
  strategy          varchar(20)             -- "fixed" | "sliding_window" | "recursive" |
                                             -- "paragraph" | "sentence" | "structural" |
                                             -- "semantic" | "parent_child" | "hierarchical" |
                                             -- "adaptive" (11th, "markdown"/"html", is an alias
                                             -- of "structural" — see below)
  config            jsonb                   -- chunk_size/overlap/etc. actually used
  status            enum(chunk_set_status): pending | ready | failed
  status_message    varchar(500), nullable
  chunk_count       int, default 0
  created_by        UUID FK -> users.id, ON DELETE SET NULL, nullable
  created_at / updated_at timestamptz
  UNIQUE(document_id, strategy)  -- uq_chunk_set_document_strategy

chunks
  id                UUID PK
  chunk_set_id      UUID FK -> document_chunk_sets.id, ON DELETE CASCADE, indexed
  parent_chunk_id   UUID FK -> chunks.id, ON DELETE CASCADE, nullable  -- parent_child/hierarchical only
  chunk_index       int
  text              text
  char_start        int
  char_end          int
  token_count       int                     -- tiktoken cl100k_base
  page              int, nullable           -- carried from the source block, PDF only
  heading           varchar(500), nullable  -- nearest enclosing heading's text
  language          varchar(10), nullable
  status            enum(chunk_status): ready | failed | skipped
  status_message    varchar(500), nullable
  embedding_model   varchar(100), nullable  -- populated by Phase 7; null until then
  created_at        timestamptz
  UNIQUE(chunk_set_id, chunk_index)  -- uq_chunk_set_index
```

**One set per (document, strategy), not one set per document.** `UNIQUE(document_id, strategy)`
deliberately allows several chunk sets to coexist for the same document — one per strategy the
user has actually generated — which is what makes the "Compare Chunkers" UI possible.
Re-generating with a strategy that already has a set reuses that set's `id` (updating `config`/
`status`/`chunk_count` in place) rather than creating a new row, and deletes+replaces its `chunks`
rows; the id is reused specifically because `chunks.chunk_set_id` has no `ON UPDATE CASCADE`, so
swapping the parent's primary key on regen would orphan the FK (found via manual e2e testing
before the automated test suite existed, fixed by reusing the id and deleting old chunks before
the upsert, not after).

**Chunk metadata lives directly on `Chunk`**, not a separate `chunk_metadata` table — it's a
strict 1:1, no independent lifecycle, so a join table would only add overhead. "Section" is
represented by `heading` (nearest enclosing heading's text); there's no separate outline-numbering
system.

**11 named strategies, implemented as fewer underlying algorithms:**
* `fixed` / `sliding_window` — character windows with configurable overlap.
* `recursive` — block → sentence → word fallback, preserving semantic boundaries; the preferred
  default when no strategy is specified.
* `paragraph` / `sentence` — block-level / sentence-level merging up to the token budget.
* `structural` — splits on heading boundaries; `markdown` and `html` are documented names for the
  same function, since both formats already arrive as the same `structured_content` block shape by
  the time chunking runs (Phase 5 already did format-specific structure detection).
* `semantic` — adjacent-sentence TF-IDF cosine similarity (scikit-learn) as the split signal. This
  is a deliberate lightweight proxy, not a stub: real embedding-based semantic chunking needs
  Phase 7's embedding model, so TF-IDF is the honest interim implementation, documented here to be
  revisited once Phase 7 lands.
* `parent_child` — two-level: `structural` parents, `recursive` children (`parent_chunk_id` set).
* `hierarchical` — N-level generalization of `parent_child` with shrinking token budgets per level.
* `adaptive` — heuristic dispatcher choosing among the above based on heading density and document
  size (falls back to `paragraph` for short, headingless documents; `structural` once a document
  has enough headings; `recursive` otherwise).

**`document_chunk_sets.chunk_count` is a per-set count**, not deduplicated across sets — a document
compared across 3 strategies has 3 independent `chunk_count` values, each counting only that set's
own `chunks` rows. There's no repository-wide "total chunks" rollup; it isn't needed until
Phase 7's embedding cost estimation, at which point it can be derived by summing.

Chunks are never deleted for validation failures — `status = failed`/`skipped` chunks stay in the
table (audit trail), the same pattern as Phase 5's `FAILED_PARSE` on `documents`.

# 17. Embedding Schema (Phase 7)

Implemented in `backend/app/models/embedding.py`, migration `0008_add_embedding_tables`.
Populated by `embedding_worker.embed_chunk_set` (`worker/embedding_worker/tasks.py`), reading
Phase 6's `chunks.text` — never re-deriving text from `document_content`, since embeddings are
scoped to one specific chunking run.

```
embedding_versions
  id                UUID PK
  chunk_set_id      UUID FK -> document_chunk_sets.id, ON DELETE CASCADE, indexed
  document_id       UUID FK -> documents.id, ON DELETE CASCADE, indexed  -- denormalized, avoids
                                                                          -- a join for repo-wide queries
  provider          varchar(20)             -- "bge" | "e5" | "nomic" | "openai" | "voyage" | "jina"
  model             varchar(100)            -- e.g. "BAAI/bge-small-en-v1.5"
  dimensions         int                    -- true native dimensionality (see padding note below)
  version           int                     -- bumps on regenerate; see below
  status            enum(embedding_version_status): pending | ready | failed
  status_message    varchar(500), nullable
  embedding_count   int, default 0
  total_tokens      int, default 0
  total_cost_usd    numeric(12,6), nullable -- null for free/local providers
  avg_latency_ms    int, nullable
  created_by        UUID FK -> users.id, ON DELETE SET NULL, nullable
  created_at / updated_at timestamptz
  UNIQUE(chunk_set_id, provider, model)  -- uq_embedding_version_chunk_set_provider_model

embeddings
  id                    UUID PK
  embedding_version_id  UUID FK -> embedding_versions.id, ON DELETE CASCADE, indexed
  chunk_id              UUID FK -> chunks.id, ON DELETE CASCADE, indexed
  embedding             vector(1536)         -- fixed pgvector width; see padding note below
  token_count           int
  cost_usd              numeric(10,6), nullable  -- null for free/local providers
  latency_ms            int
  status                enum(embedding_status): ready | failed
  status_message        varchar(500), nullable
  UNIQUE(embedding_version_id, chunk_id)  -- uq_embedding_version_chunk
```

**One version per (chunk_set, provider, model), mirroring Phase 6's chunk_set pattern exactly.**
`UNIQUE(chunk_set_id, provider, model)` lets several embedding versions coexist per chunk set —
one per provider+model actually tried — which is what makes "Compare Models" possible.
Re-generating with a provider+model that already has a version reuses that version's `id` (bumping
`version`, replacing its `embeddings` rows) rather than creating a new row, for the identical
FK-safety reason Phase 6 needed this: `embeddings.embedding_version_id` has no `ON UPDATE CASCADE`,
so swapping the parent's primary key on regen would orphan the FK.

**Fixed-width `vector(1536)` column, zero-padded for smaller models.** pgvector requires one fixed
dimension per column, but this phase's providers range from 384 dims (bge-small) to 1536 (OpenAI
text-embedding-3-small). Every vector is zero-padded out to 1536 before insert; the true
dimensionality is recorded on `embedding_versions.dimensions`. Padding with zeros doesn't corrupt
similarity *within* one embedding version (both sides of any comparison carry the same trailing
zeros), but comparing raw vectors *across* differently-dimensioned embedding versions is
meaningless — retrieval (Phase 9) must always filter ANN search to a single `embedding_version_id`,
never mix versions.

**Providers implemented:**
* `bge`, `e5`, `nomic` — real local inference via `fastembed` (ONNX Runtime, no torch, no API key).
  `bge` (`BAAI/bge-small-en-v1.5`, 384 dims) is the default and the one model pre-cached at Docker
  build time; `e5` (`intfloat/multilingual-e5-large`) and `nomic`
  (`nomic-ai/nomic-embed-text-v1.5`) are equally real but download their weights on first use
  instead, to keep the worker image/build size reasonable.
* `openai`, `voyage`, `jina` — real HTTP integrations against each provider's documented embeddings
  API (not stubs), gated behind `OPENAI_API_KEY`/`VOYAGE_API_KEY`/`JINA_API_KEY`. This dev
  environment has no paid keys configured, so these paths are exercised in tests only when the
  corresponding key is present (`pytest.mark.skipif`, the same convention Phase 5's OCR tests use
  for missing local binaries) — never mocked.
* `instructor` — not implemented (would need a distinct loading mechanism from the other local
  models); explicitly deferred rather than silently omitted, same "implement the real ones,
  document the rest" pattern as Phase 5's EasyOCR/PaddleOCR deferral.

Token counts reuse the same `tiktoken` `cl100k_base` approximation Phase 6 uses for chunks
(`worker/common/tokenizer.py`, promoted out of `chunk_worker` in this phase since both worker
packages now need it) rather than loading each provider's own tokenizer — a deliberate, documented
simplification, not an oversight.

Embeddings are never deleted for failure — a provider that isn't configured (e.g. `openai` without
a key) still gets a `FAILED` `embedding_versions` row recording why, the same audit-trail pattern
Phase 5/6 already established for parse/chunk failures.

# 18. Vector Index Schema (Phase 8)

Implemented in `backend/app/models/vector_index.py`, migration `0009_add_vector_index_tables`.
Populated by `index_worker.build_index` (`worker/index_worker/tasks.py`), reading Phase 7's
`embeddings` table (for PgVector) or copying its vectors into an external store (Qdrant, Chroma,
Pinecone).

```
vector_indexes
  id                    UUID PK
  embedding_version_id  UUID FK -> embedding_versions.id, ON DELETE CASCADE, indexed
  document_id           UUID FK -> documents.id, ON DELETE CASCADE, indexed  -- denormalized
  provider              varchar(20)  -- "pgvector" | "qdrant" | "chroma" | "pinecone"
  index_type            varchar(20)  -- "hnsw" | "ivf_flat" | "flat" | "pq"
  namespace             varchar(200) -- collection/index name in the external store, or the
                                     -- Postgres index name for pgvector; always the
                                     -- embedding_version_id itself, for a stable 1:1 mapping
  dimensions            int
  version               int          -- bumps on rebuild; see below
  status                enum(vector_index_status): pending | building | ready | failed
  status_message        varchar(500), nullable
  vector_count          int, default 0
  build_duration_ms     int, nullable
  created_by            UUID FK -> users.id, ON DELETE SET NULL, nullable
  created_at / updated_at timestamptz
  UNIQUE(embedding_version_id, provider)  -- uq_vector_index_embedding_version_provider

index_versions
  id                UUID PK
  vector_index_id   UUID FK -> vector_indexes.id, ON DELETE CASCADE, indexed
  version           int
  vector_count      int
  status            enum(index_version_status): ready | failed
  status_message    varchar(500), nullable
  build_duration_ms int, nullable

vector_metadata
  id              UUID PK
  vector_index_id UUID FK -> vector_indexes.id, ON DELETE CASCADE, indexed
  chunk_id        UUID FK -> chunks.id, ON DELETE CASCADE, indexed
  metadata_payload jsonb  -- arbitrary per-chunk key/value (heading, page, language, ...),
                          -- attached at index build time for filtered search
  UNIQUE(vector_index_id, chunk_id)  -- uq_vector_metadata_index_chunk
```

**One index per (embedding_version, provider), mirroring the Phase 6/7 pattern exactly.**
`UNIQUE(embedding_version_id, provider)` lets several indexes coexist per embedding version — one
per provider actually tried. Re-running "create index" for a provider that already has one rebuilds
it in place (same `vector_indexes` id, `version` bumped, a new `index_versions` audit row appended)
rather than creating a duplicate, for the same FK-safety reason Phases 6-7 needed this.

**`index_versions` is a pure audit trail**, distinct from `vector_indexes.version` (the current
state) — every build or rebuild attempt (including failures) appends one row here, so the full
history of a namespace's builds stays inspectable even after the current version has moved on.

**Providers implemented:**
* `pgvector` (default) — no data copy; vectors already live in Phase 7's `embeddings` table.
  "Building an index" means creating a real ANN index scoped to one embedding_version via a partial
  index (`CREATE INDEX ... ON embeddings USING hnsw (embedding vector_cosine_ops) WHERE
  embedding_version_id = ...`). Supports `hnsw` and `ivf_flat` (real pgvector access methods) and
  `flat` (no ANN index at all — pgvector's actual behavior without one, an exact sequential scan,
  which is what "flat" legitimately means). `pq` is not implemented — pgvector has no native
  product-quantization index type, a real limitation, not a deferral choice.
* `qdrant`, `chroma` — real HTTP clients against self-hosted instances
  (`qdrant/qdrant`/`chromadb/chroma` in `docker/docker-compose.yml`), no API key needed. Both
  providers' native ANN index is always HNSW; Qdrant additionally supports `flat` by disabling its
  HNSW graph (`hnsw_config.m = 0`, forcing exact search); Chroma's client API exposes no such
  choice, so it only supports `hnsw`. Neither has an `ivf_flat` or `pq` concept.
* `pinecone` — a real HTTP integration against Pinecone's documented serverless API, gated behind
  `PINECONE_API_KEY`. This dev environment has no paid key configured, so it's exercised in tests
  only when the key is present (`pytest.mark.skipif`, the same convention Phase 7's OpenAI/Voyage/
  Jina tests use) — never mocked.
* `weaviate`, `milvus` — not implemented. Both are real, legitimate self-hostable vector databases,
  but adding two more Docker services (Milvus in particular needs its own etcd + object-storage
  dependencies) was judged disproportionate scope for this phase once PgVector, Qdrant, and Chroma
  already demonstrate the multi-provider story with genuinely different backing architectures
  (embedded-in-Postgres vs. two different standalone vector databases). Documented as an explicit
  deferral, the same "implement several real ones, document the rest honestly" pattern as Phase
  7's Instructor.

Deleting an index is enqueue-only from the API (`index_worker.delete_index`), never a synchronous
ORM delete — removing only the `vector_indexes` tracking row would silently orphan the actual
vectors in an external store, so the worker must reach that store first.

# 19. Retrieval Schema

Implemented in `backend/app/models/retrieval.py`, migrations `0010_add_retrieval_tables` (Phase 9,
dense retrieval), `0011_add_hybrid_retrieval` (Phase 10, hybrid search — adds the
`retrieval_mode`/`fusion_method`/`dense_weight`/`sparse_weight`/`rrf_k` columns on `retrievals` and
`dense_score`/`sparse_score` on `retrieval_results`, all nullable so Phase 9's dense-only rows are
unaffected), and `0012_query_understanding` (Phase 11, query understanding — adds
`query_understanding_enabled`/`query_intent`/`intent_confidence`/`rewritten_query_text`/
`generated_queries`/`detected_metadata_filter` to `retrievals`, opt-in via
`query_understanding_enabled` defaulting to `false` so Phase 9/10 behavior is unchanged when unset).

```
retrievals
  id                   UUID PK
  vector_index_id      UUID FK -> vector_indexes.id, ON DELETE CASCADE, indexed
  document_id          UUID FK -> documents.id, ON DELETE CASCADE, indexed
  query_text           varchar(2000)
  top_k                integer, default 10
  score_threshold      float, nullable
  similarity_metric    enum(cosine, dot, euclidean), default cosine
  metadata_filter      jsonb, nullable                 -- exact-match filter on heading/page/language
  retrieval_mode       enum(dense, hybrid), default dense
  fusion_method        enum(weighted_sum, rrf), nullable   -- only set when retrieval_mode = hybrid
  dense_weight         float, nullable                     -- only set for hybrid + weighted_sum
  sparse_weight        float, nullable                     -- only set for hybrid + weighted_sum
  rrf_k                integer, nullable                   -- only set for hybrid + rrf
  query_understanding_enabled  boolean, default false       -- opt-in (Phase 11)
  query_intent         enum(fact_lookup, definition, summarization, comparison,
                            multi_hop_reasoning, numerical_query, code_question,
                            table_lookup, policy_lookup, conversational_followup), nullable
  intent_confidence    float, nullable
  rewritten_query_text varchar(2000), nullable
  generated_queries    jsonb, nullable                      -- list[str], includes rewritten original
  detected_metadata_filter  jsonb, nullable                 -- auto-extracted, merged under caller's
                                                             -- metadata_filter (caller wins on conflict)
  status               enum(pending, completed, failed)
  status_message       varchar(500), nullable
  result_count         integer, default 0
  avg_similarity       float, nullable
  min_similarity       float, nullable
  max_similarity       float, nullable
  latency_ms           integer, nullable
  created_by           UUID FK -> users.id, ON DELETE SET NULL, nullable
  created_at / updated_at   timestamptz

retrieval_results
  id             UUID PK
  retrieval_id   UUID FK -> retrievals.id, ON DELETE CASCADE, indexed
  chunk_id       UUID FK -> chunks.id, ON DELETE CASCADE, indexed
  rank           integer                    -- 1-indexed position in the ranked result list
  score          float                      -- normalized so higher is always better (see below);
                                             -- for hybrid retrievals, this is the *fused* score
  dense_score    float, nullable            -- only populated for hybrid retrievals
  sparse_score   float, nullable            -- only populated for hybrid retrievals
```

**Phase 10 (hybrid search) extends this same model rather than introducing a parallel
"HybridRetrieval" concept** — `retrieval_mode` distinguishes dense-only (Phase 9's original
behavior, byte-for-byte unchanged) from hybrid (dense + BM25 sparse, fused).
`worker/retrieval_worker/bm25.py` computes BM25 fresh per query directly over the target
`vector_index`'s embedding version's `chunk_set`'s READY chunk texts via `rank_bm25` (a real
BM25Okapi implementation), rather than maintaining a persisted inverted index — chunk sets in this
system are individual documents, not a web-scale corpus, so re-tokenizing per query is fast and
avoids a second index artifact that would need to stay in sync with chunk regeneration the same
way vector indexes already must. A real, documented limitation of this choice: BM25's IDF is
degenerate over very small corpora (a term appearing in exactly half of a 2-document corpus gets
an exact-zero IDF; a 1-document corpus collapses entirely), so single-chunk documents will
routinely produce a `null` `sparse_score` even for exact keyword matches — not a bug, a genuine
property of the BM25 formula at that scale.

`worker/retrieval_worker/fusion.py` implements both fusion methods task.md requires: **weighted
sum** (min-max normalizes dense and sparse scores to `[0, 1]` first, since their raw scales are
incomparable, then combines via `dense_weight`/`sparse_weight`, which the backend always
normalizes to sum to 1 before storing) and **reciprocal rank fusion** (fuses by rank position
instead of raw score — the standard approach systems like Elasticsearch's hybrid search use,
sidestepping the scale problem entirely; `rrf_k` defaults to 60, the constant from the original RRF
paper). Both retrievers are asked for a candidate pool of `max(top_k * 3, 20)` results — not just
`top_k` — before fusion, per docs/02-architecture.md section 60's "never send only Top-K directly"
guidance; the fused, re-ranked list is truncated to `top_k` only after fusion.

A `Retrieval` always targets one `VectorIndex` (never a whole repository in a single call) — the
same constraint `embedding.py` documents for indexing: pgvector's zero-padded columns make
cross-embedding-version vector comparison meaningless, so a query is always embedded with the
same provider/model that produced the target index, then searched against that one index.

Unlike `VectorIndex`/`EmbeddingVersion` (rebuilt in place, id reused), a `Retrieval` is a
point-in-time query execution — re-running "the same" query text creates a new row rather than
updating one, since two executions can legitimately return different results (index rebuilt in
between, non-deterministic ANN search). No regenerate-reuses-id handling applies here.

Row lifecycle mirrors `Document` on upload, not `VectorIndex` on build: the backend creates the
row synchronously (status=PENDING, just the caller's query parameters, no AI computation yet) via
a plain repository `.add()`, then enqueues `retrieval_worker.execute_retrieval(retrieval_id)`,
which embeds the query, runs the search, and updates the row to COMPLETED/FAILED plus inserts the
`retrieval_results` rows. This is a plain CRUD create — not "AI pipeline execution" — since no
computation has happened yet at that point, unlike chunk/embedding/index rows which only ever get
written by the worker once real results exist.

**Similarity metric support is asymmetric across providers**, the same "document real limitations
honestly" pattern already established for index_type in section 18: PgVector can select
cosine/dot/euclidean per query (raw vectors always live in Postgres, so any of its three distance
operators — `<=>`, `<#>`, `<->` — is a valid query regardless of which operator class the ANN
index itself used), but Qdrant/Chroma/Pinecone all fix their distance metric to cosine at
collection/index creation time (Phase 8 never exposed a metric choice there), so requesting
`dot`/`euclidean` against those three fails with a clear "not supported" error rather than
silently ignoring the request.

`score` is always normalized so *higher is better* regardless of metric — cosine/dot similarity as
computed, but euclidean distance is negated — so `score_threshold` ("keep hits with score >=
threshold") means the same thing for every metric.

`metadata_filter` is an exact-match equality filter, scoped to exactly the three keys Phase 8
attaches at index build time (`heading`, `page`, `language`) — not an arbitrary key/value filter —
applied natively per provider (a join back to `chunks` for PgVector, since that's the original
source of that data; each provider's own upserted payload for Qdrant/Chroma/Pinecone).

**Phase 11 (query understanding, docs/02-architecture.md sections 51-55) is an opt-in
preprocessing pass**, not a parallel pipeline — `query_understanding_enabled` defaults to `false`,
leaving Phase 9/10 behavior untouched when unset. When enabled, `retrieval_worker.execute_retrieval`
runs four steps before search:

- **Classification** (`query_understanding.classifier`): rule-based (regex/keyword over the fixed
  10-way taxonomy architecture section 51 specifies), not a trained model — deterministic and fully
  testable without any external dependency, the same scoping choice Phase 10 made for BM25.
  Persisted as `query_intent`/`intent_confidence` for the frontend's Query Inspector; does not
  change retrieval behavior itself (no automatic mode-switching to the doc's illustrative "Hybrid +
  Metadata Filter" preferred-retriever example — that would be a bigger behavior change than this
  phase's scope covers).
- **Rewrite** (`query_understanding.rewriter`): architecture section 53's own example rewrites using
  prior *conversation context*, which this system has no model for yet (Conversation Memory is
  section 95, a separate future architecture concern with no backing table today) — so Phase 11's
  rewrite operates on the single query in isolation via an LLM call (OpenAI, gated by the same
  `OPENAI_API_KEY` Phase 7's cloud embedding provider already uses), falling back to whitespace/
  punctuation normalization (no rewrite) when the key isn't configured or the call fails. A query
  understanding failure must never block retrieval.
- **Multi-query expansion** (`query_understanding.expander`): generates up to 3 alternative
  phrasings via one LLM call (same fallback: `[query_text]` alone without a key). `generated_queries`
  fans out both the dense embed+search call and, for hybrid mode, BM25 search — each chunk's best
  score across variants is kept (a max-score merge across query variants, a different concern from
  Phase 10's dense/sparse fusion and deliberately kept simpler).
- **Filter extraction** (`query_understanding.filter_extractor`): regex-based, extracting only
  `heading`/`page`/`language` — the three keys `metadata_filter` above actually supports. Section
  55's own example (department/year filters) isn't extracted because chunk metadata has no
  department or publication-year column; building detection for a filter nothing downstream can
  apply would be dead code, not a real feature. `detected_metadata_filter` is merged under the
  caller-supplied `metadata_filter` — caller wins on key conflicts, since an explicit filter should
  never be silently overridden by a heuristic guess.

**Phase 12 (advanced retrieval, docs/02-architecture.md sections 62-63, 75, 103) adds migration
`0013_advanced_retrieval`**: `expand_to_parent`/`use_mmr`/`mmr_lambda`/`compress_context` on
`retrievals` (each independently opt-in, defaulting off/`false`/`null`), `RAG_FUSION` added to the
`fusion_method` enum, and `compressed_text` on `retrieval_results`. Two of this phase's task.md
"Retrievers" deliverables — Self-Query and Multi-Query — are **not** separately implemented here;
they're the same capability Phase 11 already delivers as `detected_metadata_filter` and
`generated_queries` (docs/02-architecture.md sections 65 and 54 describe the identical mechanism
Phase 11's task.md already named "Metadata Detection" and "Query Expansion") — duplicating that
logic under this phase's name would just be dead code with no new behavior.

The four real additions, applied in this order inside `retrieval_worker.execute_retrieval` after
fusion and before persisting:

- **Parent-Child retrieval** (`expand_to_parent`, section 63): search still runs against whatever
  chunk actually matched — the chunk-level embedding is unchanged, since Phase 6's `parent_child`
  chunking strategy already embeds both parent and child rows in the same chunk_set. This flag only
  remaps each result's *returned* identity to `chunks.parent_chunk_id` when one exists
  (`retrieval_worker.parent_expansion`), merging duplicates that land on the same parent by keeping
  the highest-scoring one whole (so its `dense_score`/`sparse_score` stay attributable to the score
  that won, rather than averaged). Chunks from any other chunking strategy have no `parent_chunk_id`
  at all, so this is a safe no-op for them — nothing needs to check the chunk set's strategy first.
- **MMR diversification** (`use_mmr`/`mmr_lambda`, section 62): a real greedy Maximum Marginal
  Relevance selection (`retrieval_worker.mmr`) over each candidate's actual embedding vector — not
  an approximation over scalar scores — fetched via `SELECT embedding::text` (the same manual
  pgvector-text-format parsing `index_worker.tasks._parse_vector_text` already established, no
  pgvector adapter registered on this sync engine) and compared with plain Python
  dot-product/`math.sqrt` cosine similarity (no numpy dependency: these vectors are already
  zero-padded to `EMBEDDING_DIM_MAX`, and trailing zero components don't change either a dot
  product or a norm, so comparing the full padded vectors is identical to comparing just the real
  prefix). `mmr_lambda` defaults to `0.7` (relevance-weighted, matching `dense_weight`'s Phase
  10 default split) when `use_mmr` is set without an explicit value.
- **RAG Fusion** (`fusion_method = "rag_fusion"`, section 103): rather than max-score-merging each
  retriever's per-query-variant lists into one list *before* fusing dense against sparse (Phase
  10/11's approach), every per-variant per-retriever list is kept separate and N-way RRF-fused at
  once (`fusion.reciprocal_rank_fusion_multi`, a genuine generalization of the existing 2-list
  `reciprocal_rank_fusion` — kept as a separate function since the dense/sparse component-score
  breakdown that 2-list version reports doesn't cleanly generalize past two lists). Requires
  `query_understanding_enabled=true` (backend-validated, 422 otherwise) since fusing multiple query
  variants is the entire premise — with a single variant it degenerates to plain RRF, which the
  cheaper `"rrf"` option already covers.
- **Context compression** (`compress_context`, section 75): after the final top_k is chosen,
  compresses each result's chunk text down to its query-relevant sentences
  (`retrieval_worker.compression`) and stores that *alongside*, not instead of, the original in
  `retrieval_results.compressed_text` — the original is always still inspectable. Scoring is lexical
  token-overlap against a fixed English stopword list, not embedding-based — the same "real but
  bounded" scope choice BM25 made in Phase 10: scoring every sentence via a fresh embedding call at
  retrieval time would add real latency this phase doesn't need to pay for a working compression
  step. Falls back to the single highest-overlap sentence rather than ever returning empty text.

**Phase 13 (reranking, docs/02-architecture.md sections 71-74) adds migration `0014_add_reranking`**:
`rerank_enabled`/`reranker_provider` on `retrievals` (opt-in, off by default), `rerank_score` on
`retrieval_results`. A real cross-encoder scores every remaining candidate's `(query, chunk_text)`
pair *jointly* — the reason reranking improves precision over the embedding-based retrieval score,
which encodes query and chunk independently and only compares their vectors afterward
(docs/02-architecture.md section 72's "Python threading" example: vector search ranks "Python
snake" above "Python threading" on embedding similarity alone; a cross-encoder that actually reads
both texts together doesn't make that mistake).

`reranker_provider` supports five real providers (`worker/retrieval_worker/reranking/`):
`cross_encoder` (default — `fastembed`'s ONNX `Xenova/ms-marco-MiniLM-L-6-v2`, ~80MB, pre-cached
at Docker build time) and `bge` (`fastembed`'s `BAAI/bge-reranker-base`, ~1GB, downloads on first
use — the same build-time-size tradeoff Phase 7 already documented for its non-default local
embedding models) both run via the same `fastembed.rerank.cross_encoder.TextCrossEncoder` class
Phase 7's local embedding providers' ONNX approach mirrors; `flashrank` is a separate, even
lighter-weight local ONNX library (`ms-marco-TinyBERT-L-2-v2`, ~3MB) listed as its own required
model in task.md rather than folded into the `fastembed`-backed pair; `cohere`/`jina` are real
HTTP integrations against each provider's rerank API, gated by `COHERE_API_KEY`/`JINA_API_KEY`
(Jina reuses the same key Phase 7's `JinaEmbeddingProvider` already gates on) — no paid keys are
configured in this dev environment, so those two are exercised live only when the corresponding
key is set, the same `pytest.mark.skipif` convention every other cloud provider in this codebase
uses.

Applied between "parent-child expand" and "MMR select/truncate" inside `execute_retrieval`: the
candidate pool widens further when `rerank_enabled` (`max(top_k * 5, 50)`, echoing section 71's
"Top 100" example at a scale this system's typically smaller chunk sets actually warrant) since
reranking only has something to do with a pool noticeably larger than the final `top_k`.
`rerank_score` is persisted *alongside* `score`, never overwriting it — the same pattern
`dense_score`/`sparse_score` already established — so the pre- and post-rerank signals stay
independently inspectable; final result order follows `rerank_score` once reranking has run, and
MMR (if also enabled) uses `rerank_score` rather than `score` as its relevance term at that point,
since it's the more accurate signal.

# 20. Prompt Schema

Migration `0015_add_prompt_tables` adds two new tables — `prompt_templates` and `prompts` — the
first genuinely new resource type since Phase 10 (every Phase 10-13 addition extended the existing
`Retrieval`/`RetrievalResult` rows instead). Prompt construction is conceptually downstream of
retrieval (it consumes a completed `Retrieval`'s ranked results), not another retrieval mode, so it
gets its own tables rather than more opt-in columns on `retrievals`.

**`prompt_templates`** is repository-scoped (`repository_id` FK, `ON DELETE CASCADE`).
docs/02-architecture.md section 79 requires "Prompt v1/v2/v3" to coexist for experiment
comparison, so unlike `embedding_versions` (Phase 7, which replaces its row in place on a
same-provider+model re-run), creating a new version under an existing `name` always **inserts** a
new row with `version = max(existing) + 1` — uniqueness is `(repository_id, name, version)`, never
`(repository_id, name)`. `is_active` marks whether a version is still offered when building new
prompts; archived versions are left in place (not deleted) since past `prompts` rows may still
reference them, and reproducibility (this phase's Acceptance Criteria) requires that link to stay
valid. Columns: `name`, `version`, `system_prompt`, `formatting_instructions` (nullable),
`output_schema` (JSONB, nullable — for structured-output prompts), `is_active`, `created_by`.

**`prompts`** is one built prompt, always tied to a single `retrieval_id` (`ON DELETE CASCADE`) —
the Context Window Builder (section 77) explicitly assembles "the final context... after
reranking", i.e. from that retrieval's already-ranked `retrieval_results` rows.
`prompt_template_id` (`ON DELETE SET NULL`) is nullable to allow an ad-hoc prompt without a saved
template, but the resolved system prompt/context/full prompt text is always **snapshotted** onto
the row itself (`rendered_system_prompt`/`rendered_context`/`rendered_prompt`) rather than
re-resolved from the template at read time — a template can gain new versions later, and
reproducibility requires the exact text used at build time to stay stable regardless.

Token accounting (Token Budget Manager, section 76) is first-class columns rather than one JSONB
blob, matching this codebase's existing convention of dedicated columns for anything the frontend
charts/inspects directly (e.g. `retrievals.avg_similarity`): `model_context_window`,
`system_prompt_tokens`, `conversation_tokens`, `context_tokens`, `query_tokens`,
`response_budget_tokens`, `total_tokens`. `conversation_tokens` is always `0` in this phase —
persistent conversation memory is Phase 16, which doesn't exist yet — but the column exists now so
Phase 16 can populate it without another migration, the same way `retrievals.detected_metadata_filter`
anticipated Phase 11 while Phases 9-10 left it null.

`citations` (Citation Engine, section 80) is JSONB — a list of `{source_label, chunk_id,
document_id, document_filename, page, section, confidence}` objects — because its shape is a
derived, display-only projection of data already living in normalized form on
`chunks`/`documents`/`retrieval_results`; there is no independent citation identity worth a join
table. `confidence` is a best-effort proxy (whichever relevance signal ordered the retrieval —
`rerank_score` if reranking ran, else `score` — clamped to `[0.0, 1.0]`), not a calibrated
probability; documented as such in `backend/app/core/citations.py` rather than invented.

`status` (`pending`/`completed`/`failed`) mirrors `retrievals.status`'s shape, but in practice a
`Prompt` resolves synchronously within the request — there is no Celery task for prompt building,
since token counting and context assembly are deterministic CPU-bound computation over data the
caller already fetched, unlike embedding generation or reranking. `failed` is reached when
`system_prompt_tokens + conversation_tokens + query_tokens + response_reserve_tokens` alone already
exceed `model_context_window`, leaving no room for retrieved context regardless of chunk sizes —
a real, surfaced failure rather than a silently context-free prompt.

# 21. Conversation Schema

**Pending — Conversation Memory phase.**

# 22. Memory Schema

**Pending — Conversation Memory phase.**

# 23. Evaluation Schema

**Pending — Evaluation Engine phase.**

# 24. Experiment Schema

**Pending — Evaluation Engine phase.**

# 25. Benchmark Schema

**Pending — Benchmarking Framework phase.**

# 26. Analytics Schema

**Pending — Analytics Pipeline phase.**

# 27. Audit Schema

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

# 28. API Keys Schema

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

# 29. Session Schema

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

# 30. Notification Schema

**Pending — not yet scheduled in `05-task.md`.**

# 31. Queue Schema

Celery uses Redis directly as broker/result backend (see `worker/common/celery_app.py`); no
relational queue table exists. A Dead Letter Queue table is introduced alongside the Document
Processing phase per docs/02-architecture.md section 151.

---

# 32. Index Strategy

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

# 33. Partitioning

**Pending.** Time-based partitioning is planned for `audit_logs` and usage/analytics tables once
they exist, per docs/02-architecture.md section 163.

---

# 34. Constraints

* `NOT NULL` on every required column.
* Foreign keys use `ON DELETE` behavior appropriate to the soft-delete strategy (`RESTRICT` by
  default; cascades are explicit, never implicit).
* Uniqueness constraints (e.g., slugs, emails) are added when the owning entity is implemented.

---

# 35. Foreign Keys

All foreign keys reference the UUID primary key of the parent table and are indexed
(docs/06-rule.md — "Never skip indexes on large tables").

---

# 36. Query Optimization

* Repositories only ever issue queries needed for the current use case (no `SELECT *` beyond
  ORM-mapped columns).
* Pagination uses `LIMIT`/`OFFSET` today (`backend/app/repositories/base.py`); keyset pagination
  is adopted for high-volume tables (chunks, audit logs) once they exist.
* N+1 queries are forbidden; eager-loading strategy is defined per relationship as models are
  added.

---

# 37. Row Level Security

**Pending — Phase 2.** Tenant isolation is enforced at the application/repository layer first;
PostgreSQL RLS is evaluated as defense-in-depth once the multi-tenant schema exists.

---

# 38. Backup Strategy

Local development: Docker named volumes (`postgres_data`, `minio_data` in
`docker/docker-compose.yml`). Production backup cadence (daily full + hourly incremental) is
defined in docs/02-architecture.md section 161 and implemented when a production environment is
provisioned.

---

# 39. Migration Strategy

* Tool: Alembic, async engine (`backend/alembic/env.py`), configured to read
  `Settings.database_url` rather than a hardcoded URL.
* One linear history under `backend/alembic/versions`; no branching migrations.
* Every migration implements both `upgrade()` and `downgrade()`.
* Migrations run via the `migrate` one-shot service in `docker/docker-compose.yml`
  (`alembic upgrade head`) before `backend`/`worker` start.
* Naming: `YYYYMMDD_NNNN_description.py`.

---

# 40. ER Diagram

**Pending.** Generated once entity schemas beyond Phase 0 exist; will be regenerated after each
phase that adds tables.

---

# 41. Naming Convention

* Tables: `snake_case`, plural (`documents`, `chunks`).
* Columns: `snake_case`.
* Primary key column: always `id`.
* Foreign key columns: `<singular_table>_id` (e.g., `document_id`).
* Migration files: `YYYYMMDD_NNNN_description.py`.

---

# 42. Sample Queries

No domain queries exist yet. The base repository (`backend/app/repositories/base.py`) provides
`get_by_id`, `list`, `add`, `delete` — every domain repository extends this rather than
reimplementing CRUD.

---

# 43. Best Practices

* Never bypass the repository layer for data access.
* Never store large binaries in PostgreSQL — use object storage.
* Always add indexes for foreign keys and frequently filtered/sorted columns before a table
  reaches production traffic, not after.
* Every new table adds `UUIDPrimaryKeyMixin` + `TimestampMixin`, and `SoftDeleteMixin` /
  `AuditMixin` where applicable (`backend/app/models/base.py`).
