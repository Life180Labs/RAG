# 04-api-spec.md

Version: 1.1

Status: Active — updated incrementally as each phase in `05-task.md` lands. Domain sections not
yet implemented are marked **Pending** with the phase that introduces them. Source of truth
priority is defined in `00-index.md`.

---

# 1. API Design Principles

* Base path: `/api/v1` (`Settings.api_v1_prefix`, `backend/app/core/config.py`).
* REST nouns, plural resources: `/api/v1/projects`, `/api/v1/documents`, `/api/v1/repositories`.
* Every response uses the standard envelope (docs/07-master_prompt.md Response Standards):

Success:

```json
{
  "success": true,
  "data": {},
  "metadata": {},
  "request_id": "..."
}
```

Error:

```json
{
  "success": false,
  "error": { "code": "NOT_FOUND", "message": "..." },
  "request_id": "..."
}
```

Implemented centrally in `backend/app/schemas/common.py` (`SuccessResponse`, `ErrorResponse`) and
`backend/app/core/exceptions.py` (global exception handlers — `AppError`, validation errors,
HTTP errors, and unhandled exceptions all serialize to this shape). Every response carries an
`x-request-id` header and `request_id` body field, bound per-request by
`backend/app/middleware/request_context.py`.

* Every endpoint requires authentication and authorization once Phase 1 lands; health/metrics
  endpoints are the only unauthenticated routes by design.
* OpenAPI documentation is generated automatically by FastAPI at `/docs` and `/openapi.json`.

---

# Platform Endpoints (implemented — Phase 0)

These live outside the versioned domain API surface, matching docs/02-architecture.md section
142 (Platform Health Endpoints).

| Method | Path                | Purpose                                                        | Auth |
|--------|---------------------|-----------------------------------------------------------------|------|
| GET    | `/api/v1/live`      | Liveness probe — process is running.                            | None |
| GET    | `/api/v1/ready`     | Readiness probe — checks database, Redis, object storage.       | None |
| GET    | `/api/v1/health`    | Human-facing status (environment, request id).                  | None |
| GET    | `/metrics`          | Prometheus metrics (`http_requests_total`, latency histogram).  | None |

`/ready` returns `503` with `{"status": "not_ready", "checks": {...}}` if any dependency check
fails; each dependency's individual status (`ok` / `unavailable`) is included so operators can
tell which one failed without reading logs.

---

# 2. Authentication APIs

Implemented (`backend/app/api/v1/auth.py`, `backend/app/services/auth_service.py`).

| Method | Path                          | Auth | Rate limit         | Purpose |
|--------|-------------------------------|------|---------------------|---------|
| POST   | `/api/v1/auth/register`       | None | 5 / 60s per IP      | Create account (default role `viewer`) |
| POST   | `/api/v1/auth/login`          | None | 10 / 60s per IP     | Issue access + refresh token pair |
| POST   | `/api/v1/auth/refresh`        | None | —                   | Rotate access + refresh token pair |
| POST   | `/api/v1/auth/logout`         | None | —                   | Revoke the session behind a refresh token |
| POST   | `/api/v1/auth/forgot-password`| None | 5 / 60s per IP      | Issue a single-use, 30-min reset token (Redis-backed) |
| POST   | `/api/v1/auth/reset-password` | None | —                   | Consume a reset token, set a new password |

Notes:

* Rate limiting is a Redis fixed-window counter per client IP (`backend/app/middleware/rate_limit.py`), returning `429 RATE_LIMIT_EXCEEDED`.
* Login enforces account lockout: 5 consecutive failed attempts locks the account for 15 minutes (`403 ACCOUNT_LOCKED`).
* `/auth/register` and `/auth/reset-password` require passwords ≥12 chars with upper/lower/digit/special character (`backend/app/schemas/auth.py`).
* `/auth/refresh` and `/auth/logout` accept `{"refresh_token": "..."}`. Refresh tokens are single-use — each refresh rotates both tokens and invalidates the previous refresh token.
* `/auth/forgot-password` never reveals whether an email is registered — the response body is identical either way. In `DEBUG=true` environments only, the response additionally includes `data.reset_token` since no email-sending service exists yet; this field is never present when `DEBUG=false`.

Example — login response:

```json
{
  "success": true,
  "data": {
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "bearer",
    "expires_in": 900
  },
  "metadata": {},
  "request_id": "..."
}
```

# 3. User APIs

Implemented (`backend/app/api/v1/users.py`).

| Method | Path              | Auth   | Purpose |
|--------|-------------------|--------|---------|
| GET    | `/api/v1/users/me`| Bearer | Current user's profile |
| PATCH  | `/api/v1/users/me`| Bearer | Update `full_name` |

`UserRead` never includes `hashed_password`. Authorization uses `Depends(get_current_user)`
(`backend/app/api/deps.py`), which decodes the access token and loads the user; role-gated
routes use `Depends(require_role(UserRole.ADMIN, ...))`. No admin-only endpoints exist yet in
Phase 1 — the dependency is exercised by tests but not yet wired to a real route.

# 4. Organization APIs

Implemented (`backend/app/api/v1/organizations.py`, `backend/app/api/v1/invitations.py`).
Every route except create/list requires organization membership at the role shown (RBAC via
`require_organization_role()`, `backend/app/api/tenancy_deps.py`).

| Method | Path                                                        | Min role | Purpose |
|--------|--------------------------------------------------------------|----------|---------|
| POST   | `/api/v1/organizations`                                       | — (any authenticated user) | Create org; creator becomes OWNER |
| GET    | `/api/v1/organizations`                                        | — | List orgs the caller belongs to |
| GET    | `/api/v1/organizations/{organization_id}`                       | VIEWER | Get org |
| PATCH  | `/api/v1/organizations/{organization_id}`                       | ADMIN | Rename org |
| POST   | `/api/v1/organizations/{organization_id}/archive`               | ADMIN | Archive |
| POST   | `/api/v1/organizations/{organization_id}/restore`               | ADMIN | Restore |
| DELETE | `/api/v1/organizations/{organization_id}`                       | VIEWER (service enforces OWNER) | Soft delete |
| POST   | `/api/v1/organizations/{organization_id}/invitations`           | ADMIN | Invite by email + role |
| GET    | `/api/v1/organizations/{organization_id}/invitations`           | ADMIN | List invitations |
| POST   | `/api/v1/organizations/{organization_id}/invitations/{invitation_id}/resend` | ADMIN | Rotate token + extend TTL |
| POST   | `/api/v1/invitations/accept`                                    | Bearer (any user) | Accept — email must match invitee |
| POST   | `/api/v1/invitations/reject`                                    | Bearer (any user) | Reject |

Notes:

* Slugs are validated (`backend/app/schemas/validators.py`): lowercase alphanumeric with single
  hyphens between segments, 3–63 characters. Duplicate slugs return `409 SLUG_TAKEN`.
* Deleting an organization requires the caller's role to be exactly OWNER
  (`403 OWNER_REQUIRED` otherwise) — checked in the service layer since the dependency only
  guarantees membership, not a specific role, for this route.
* `POST /invitations` returns `data.invite_token` only when `DEBUG=true` (no email service
  exists yet, same pattern as Phase 1 password reset).
* Invitation acceptance is rejected with `403 EMAIL_MISMATCH` if the authenticated user's email
  doesn't match the invited address, and with `409 INVITATION_NOT_PENDING` /
  `401 INVITATION_EXPIRED` for already-resolved or expired invitations.

# 5. Workspace APIs

Implemented (`backend/app/api/v1/workspaces.py`). Creating a workspace requires organization
ADMIN+; every other route requires workspace membership (`require_workspace_role()`) — see
docs/03-database.md section 6 for why organization role alone isn't sufficient.

| Method | Path                                                  | Min role | Purpose |
|--------|--------------------------------------------------------|----------|---------|
| POST   | `/api/v1/organizations/{organization_id}/workspaces`     | Org ADMIN | Create; creator becomes workspace OWNER |
| GET    | `/api/v1/organizations/{organization_id}/workspaces`     | Org VIEWER | List workspaces in the org |
| GET    | `/api/v1/workspaces/{workspace_id}`                       | Workspace VIEWER | Get |
| PATCH  | `/api/v1/workspaces/{workspace_id}`                       | Workspace ADMIN | Rename |
| POST   | `/api/v1/workspaces/{workspace_id}/archive`               | Workspace ADMIN | Archive |
| POST   | `/api/v1/workspaces/{workspace_id}/restore`               | Workspace ADMIN | Restore |
| DELETE | `/api/v1/workspaces/{workspace_id}`                       | Workspace OWNER | Soft delete |

# 6. Project APIs

Implemented (`backend/app/api/v1/projects.py`). Same pattern as workspaces, one level down:
creating a project requires workspace ADMIN+; managing it requires project membership.

| Method | Path                                                | Min role | Purpose |
|--------|-------------------------------------------------------|----------|---------|
| POST   | `/api/v1/workspaces/{workspace_id}/projects`            | Workspace ADMIN | Create; creator becomes project OWNER |
| GET    | `/api/v1/workspaces/{workspace_id}/projects`            | Workspace VIEWER | List projects in the workspace |
| GET    | `/api/v1/projects/{project_id}`                          | Project VIEWER | Get |
| PATCH  | `/api/v1/projects/{project_id}`                          | Project ADMIN | Rename |
| POST   | `/api/v1/projects/{project_id}/archive`                  | Project ADMIN | Archive |
| POST   | `/api/v1/projects/{project_id}/restore`                  | Project ADMIN | Restore |
| DELETE | `/api/v1/projects/{project_id}`                          | Project OWNER | Soft delete |

# 7. Repository APIs

Implemented (`backend/app/api/v1/repositories.py`). (This is the "Repository" *resource* — a
document container — distinct from the `app/repositories/` data-access layer used throughout the
backend.) Creating a repository requires project ADMIN+; every other route requires
repository-level membership.

| Method | Path                                                     | Min role | Purpose |
|--------|-------------------------------------------------------------|----------|---------|
| POST   | `/api/v1/projects/{project_id}/repositories`                  | Project ADMIN | Create; creator becomes repository OWNER |
| GET    | `/api/v1/projects/{project_id}/repositories`                  | Project VIEWER | List repositories in the project |
| GET    | `/api/v1/projects/{project_id}/repositories/search?q=`        | Project VIEWER | Search by name/description (`ILIKE`) |
| GET    | `/api/v1/repositories/{repository_id}`                         | Repository VIEWER | Get |
| PATCH  | `/api/v1/repositories/{repository_id}`                         | Repository ADMIN | Rename / update description |
| PATCH  | `/api/v1/repositories/{repository_id}/settings`                | Repository ADMIN | Update default chunk strategy/embedding model/retriever/reranker/prompt version |
| POST   | `/api/v1/repositories/{repository_id}/archive`                 | Repository ADMIN | Archive |
| POST   | `/api/v1/repositories/{repository_id}/restore`                 | Repository ADMIN | Restore |
| DELETE | `/api/v1/repositories/{repository_id}`                         | Repository OWNER | Soft delete |
| GET    | `/api/v1/repositories/{repository_id}/activity`                | Repository VIEWER | Recent audit log entries for this repository |

Statistics (`document_count`, `chunk_count`, `embedding_count`, `storage_used_bytes`,
`retrieval_count`) are returned on every `RepositoryRead` response and currently always zero —
they're incremented by the document/chunk/embedding/retrieval phases once those exist, not by
anything in this phase. Search is a simple `ILIKE` match on name/description, not a full-text or
vector search (no documents are indexed yet).

# 8. Document APIs

Implemented (`backend/app/api/v1/documents.py`). Documents are created/listed under their
repository but addressed by their own `document_id` afterward. Upload routes require repository
ADMIN+ (matching the create-requires-parent-ADMIN pattern used throughout the tenancy hierarchy);
reads require VIEWER+; delete/restore require ADMIN+.

| Method | Path                                              | Min role | Purpose |
|--------|----------------------------------------------------|----------|---------|
| GET    | `/api/v1/repositories/{repository_id}/documents`    | Repository VIEWER | List (excludes soft-deleted) |
| GET    | `/api/v1/documents/{document_id}`                   | Document VIEWER | Get one |
| GET    | `/api/v1/documents/{document_id}/versions`          | Document VIEWER | List versions, newest first |
| DELETE | `/api/v1/documents/{document_id}`                   | Document ADMIN | Soft delete; decrements repository stats |
| POST   | `/api/v1/documents/{document_id}/restore`            | Document ADMIN | Restore a soft-deleted document; re-increments stats |
| GET    | `/api/v1/documents/{document_id}/download`           | Document VIEWER | Presigned URL (MinIO) or streamed bytes (local storage) — see below |

`GET .../download` returns `SuccessResponse<{url, stream_via_backend}>` when a presigned URL is
available (`url` set, `stream_via_backend: false`); when the storage backend can't produce one
(local-filesystem dev mode), it instead responds with the raw file as a `StreamingResponse`
(`Content-Disposition: attachment`) — callers must check the response `Content-Type` rather than
always parsing JSON.

# 9. Upload APIs

Implemented (`backend/app/api/v1/documents.py`), synchronous multipart upload — not the
fire-and-forget `POST /api/v1/documents/upload` contract originally sketched in
docs/02-architecture.md section 22. The backend validates and stores the file *before* responding
(size/extension/password-protection/virus-scan-stub, `backend/app/core/document_validation.py`),
then enqueues `document_worker.finalize_upload` to confirm the object landed in storage; the
response already reflects the created `Document` row (`status: "uploaded"`), not a bare
`processing` placeholder.

| Method | Path                                                    | Min role | Purpose |
|--------|-----------------------------------------------------------|----------|---------|
| POST   | `/api/v1/repositories/{repository_id}/documents`            | Repository ADMIN | Upload a new document (multipart, field name `file`) |
| POST   | `/api/v1/documents/{document_id}/versions`                  | Document ADMIN | Upload a new version of an existing document |

Validation order: extension allowlist (`pdf, docx, txt, md, csv, html, json, xml`) → size (empty
or over `max_upload_size_bytes`, 500 MB) → PDF password-protection (via `pypdf`; other formats are
not checked) → virus scan (documented no-op stub, always passes — swap in a real scanner later
without touching call sites). Duplicate detection is by `sha256_hash` within the same repository
(`DUPLICATE_DOCUMENT`, 409) — re-uploading identical bytes elsewhere is not blocked.

# 10. Parsing APIs

Parsing itself runs entirely in the background (`document_worker.parse_document`, triggered
automatically after `finalize_upload` succeeds) — there is no endpoint to trigger or poll parsing
directly. Its results surface in two places:

- `GET /api/v1/documents/{document_id}` (section 8) now returns populated `language` and
  `page_count` fields once parsing completes (previously always `null`, since Phase 4 had nothing
  that computed them). `status` progresses `validated -> parsing -> [ocr] -> cleaning -> chunking`
  (or `failed_parse`/`failed_ocr`) — the same field Phase 4 already exposed.
- The full structured content, word/character counts, reading time, OCR usage/confidence, and
  parser used are persisted to `document_content` (docs/03-database.md "Document Content (Phase
  5)"), but **no endpoint exposes this table yet** — a `GET .../content` route is deferred to
  whichever future phase first needs to display or consume parsed content directly (most likely
  Phase 6, Chunking, which reads it internally rather than over HTTP anyway).

# 11. Chunking APIs

Implemented (`backend/app/api/v1/chunks.py`), nested under their document. Like parsing, actual
chunk generation always runs in `chunk_worker` (`chunk_worker.chunk_document`) — these routes only
enqueue it (via the same post-commit `BackgroundTasks.add_task` pattern as section 9's uploads, so
the enqueue can't race ahead of the DB transaction) and read back whatever's already persisted;
there's no synchronous "wait for the chunks" response.

| Method | Path                                                              | Min role | Purpose |
|--------|-------------------------------------------------------------------|----------|---------|
| POST   | `/api/v1/documents/{document_id}/chunk-sets`                      | Document ADMIN | Generate (or regenerate) chunks with a given `strategy`; body `{"strategy": "recursive"}` |
| GET    | `/api/v1/documents/{document_id}/chunk-sets`                      | Document VIEWER | List chunk sets for the document (one per strategy tried) |
| GET    | `/api/v1/documents/{document_id}/chunk-sets/compare`               | Document VIEWER | Query params `strategy_a`, `strategy_b` — chunks from both sets side by side |
| GET    | `/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}/chunks` | Document VIEWER | List chunks in a set, paginated (`limit` 1-500 default 100, `offset`) |
| DELETE | `/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}`        | Document ADMIN | Delete a chunk set and its chunks |

`POST .../chunk-sets` returns `SuccessResponse<{enqueued: true, strategy}>` immediately — it does
not return the chunks themselves or a chunk_set id, since generation is async and (for a new
strategy) the row doesn't exist as `ready` yet. Poll `GET .../chunk-sets` and check `status`.
Calling it again with a strategy that already has a set **regenerates in place** (same chunk_set
`id`, old chunks replaced) rather than creating a duplicate — see docs/03-database.md section 16.

`strategy` accepts any of the 11 names: `fixed`, `sliding_window`, `recursive`, `paragraph`,
`sentence`, `structural`, `semantic`, `parent_child`, `hierarchical`, `adaptive`, plus `markdown`/
`html` as aliases of `structural`. An unrecognized strategy returns `422` before enqueueing.

# 12. Embedding APIs

Implemented (`backend/app/api/v1/embeddings.py`), nested under both their document and chunk set
(embeddings belong to a specific chunking run, not the document as a whole). Like chunking, actual
embedding generation always runs in `embedding_worker` (`embedding_worker.embed_chunk_set`) — these
routes only enqueue it and read back whatever's already persisted.

| Method | Path                                                                          | Min role | Purpose |
|--------|--------------------------------------------------------------------------------|----------|---------|
| POST   | `/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings`          | Document ADMIN | Generate (or regenerate) embeddings with a given `provider` (+ optional `model`); body `{"provider": "bge"}` |
| GET    | `/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings`          | Document VIEWER | List embedding versions for the chunk set (one per provider+model tried) |
| GET    | `/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings/compare`  | Document VIEWER | Query params `provider_a`, `provider_b` — both versions' vectors side by side |
| GET    | `/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings/{embedding_version_id}/vectors` | Document VIEWER | List per-chunk embedding rows in a version, paginated (`limit` 1-500 default 100, `offset`) — metadata only (token count, cost, latency, status), never the raw vector array |
| DELETE | `/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings/{embedding_version_id}` | Document ADMIN | Delete an embedding version and its vectors |

`POST .../embeddings` returns `SuccessResponse<{enqueued: true, provider, model}>` immediately —
same async-generation contract as chunking (section 11): no embedding_version id or vectors in the
response, poll `GET .../embeddings` and check `status`. Calling it again with a provider+model that
already has a version **regenerates in place** (same id, `version` bumped, old vectors replaced)
rather than creating a duplicate — see docs/03-database.md section 17.

`provider` accepts `bge`, `e5`, `nomic` (real local inference, no API key required), or `openai`,
`voyage`, `jina` (real cloud APIs, require the corresponding `{PROVIDER}_API_KEY` to be configured
on the worker — an unconfigured provider doesn't 422 at request time, since generation is async;
instead the resulting embedding_version ends up `status: "failed"` with `status_message` explaining
the missing key, discoverable via `GET .../embeddings`). `instructor` is not yet implemented (see
docs/03-database.md section 17).

# 13. Vector Index APIs

Implemented (`backend/app/api/v1/vector_indexes.py`), nested under document, chunk set, and
embedding version. Both index build and delete always run in `index_worker` — these routes only
enqueue and read back whatever's already persisted.

| Method | Path | Min role | Purpose |
|--------|------|----------|---------|
| POST   | `/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings/{embedding_version_id}/index` | Document ADMIN | Create (or rebuild) an index; body `{"provider": "pgvector", "index_type": "hnsw"}` (`index_type` defaults to `hnsw`) |
| GET    | `/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings/{embedding_version_id}/index` | Document VIEWER | List indexes for the embedding version (one per provider tried) |
| GET    | `/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings/{embedding_version_id}/index/{vector_index_id}` | Document VIEWER | Get one index's stored stats (vector_count, status, build_duration_ms, ...) |
| DELETE | `/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings/{embedding_version_id}/index/{vector_index_id}` | Document ADMIN | Delete an index — enqueue-only, see below |

`POST .../index` returns `SuccessResponse<{enqueued: true, provider, index_type}>` immediately —
same async contract as chunking/embedding (sections 11-12). Calling it again for a provider that
already has an index **rebuilds it in place** (same id, `version` bumped) rather than creating a
duplicate — see docs/03-database.md section 18.

`DELETE .../index/{vector_index_id}` is enqueue-only too (`{"enqueued": true}`), unlike chunk/
embedding delete (which delete synchronously): the actual vectors may live in an external store
(Qdrant/Chroma/Pinecone), so only `index_worker` can safely remove them, and a synchronous delete
of just the tracking row would silently orphan that external data.

`provider` accepts `pgvector` (default, no data copy — builds a real ANN index directly on
Phase 7's `embeddings` table), `qdrant`/`chroma` (real self-hosted vector databases, no API key),
or `pinecone` (real cloud API, requires `PINECONE_API_KEY` on the worker — same async-failure
contract as Phase 7's cloud embedding providers: an unconfigured key doesn't 422 at request time,
the resulting index ends up `status: "failed"` with `status_message` explaining why). `weaviate`
and `milvus` are not implemented (see docs/03-database.md section 18). `index_type` accepts `hnsw`,
`ivf_flat`, `flat`, `pq` — not every provider supports every type (a real limitation for that
provider, not a request validation error: an unsupported combination also surfaces as
`status: "failed"` on the index, since the check happens inside the async worker task).

# 14. Search APIs

**Pending — Retrieval Architecture phase.**

# 15. Retrieval APIs

Nested under document and vector index. Create requires Document VIEWER+ (running a search is a
read-oriented action, unlike building/deleting an index, which require ADMIN); reads require
VIEWER+.

| Method | Path | Auth | Notes |
|--------|------|----------|---------|
| POST   | `/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}/retrievals` | Document VIEWER | Run a retrieval query; body `{"query_text": "...", "top_k": 10, "score_threshold": null, "similarity_metric": "cosine", "metadata_filter": null, "retrieval_mode": "dense", "fusion_method": null, "dense_weight": null, "sparse_weight": null, "rrf_k": null, "query_understanding_enabled": false, "expand_to_parent": false, "use_mmr": false, "mmr_lambda": null, "compress_context": false, "rerank_enabled": false, "reranker_provider": null}` (only `query_text` required) |
| GET    | `/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}/retrievals` | Document VIEWER | List past retrievals against this index, most recent first; `?limit=50&offset=0` |
| GET    | `/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}/retrievals/{retrieval_id}` | Document VIEWER | Get one retrieval's status and aggregate stats |
| GET    | `/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}/retrievals/{retrieval_id}/results` | Document VIEWER | Get the ranked candidate list (chunk text, heading, page, rank, score) |

`POST .../retrievals` differs from Phase 8's index create in one important way: it does **not**
return `{"enqueued": true}` — it synchronously creates and returns the full `Retrieval` row
(`status: "pending"`) in the same request, then enqueues `retrieval_worker.execute_retrieval` in
the background. This mirrors how `POST .../documents` returns the created `Document` row
immediately (status `uploaded`) rather than an enqueue acknowledgment — see
docs/03-database.md section 19 for why a Retrieval's row-creation is plain CRUD rather than
enqueue-only. Poll `GET .../retrievals/{retrieval_id}` until `status` leaves `"pending"`.

`similarity_metric` accepts `cosine` (default), `dot`, `euclidean` — PgVector supports all three at
query time, but Qdrant/Chroma/Pinecone indexes are always built cosine-only (Phase 8 never exposed
a metric choice at build time), so requesting `dot`/`euclidean` against one of those three fails
the retrieval with `status: "failed"` and an explanatory `status_message`, the same
worker-surfaces-the-real-limitation contract Phase 8 uses for unsupported `index_type`s.

`metadata_filter` is an optional exact-match object over `heading`/`page`/`language` (the same keys
Phase 8 attaches to every chunk at index build time) — e.g. `{"language": "en"}`.

`score` in the results response is always normalized so *higher is better* regardless of metric —
see docs/03-database.md section 19.

**Hybrid search (Phase 10)**: `retrieval_mode` accepts `dense` (default) or `hybrid`. For `hybrid`,
`fusion_method` accepts `weighted_sum` (default if omitted) or `rrf`:

- `weighted_sum`: `dense_weight`/`sparse_weight` default to `0.7`/`0.3`
  (docs/02-architecture.md section 58's example) if omitted, and are always normalized to sum to 1
  before being stored (e.g. `{"dense_weight": 2, "sparse_weight": 1}` is stored as `0.667`/`0.333`)
  — both cannot be zero (`422`).
- `rrf`: `rrf_k` defaults to `60` if omitted.

The results response gains `dense_score`/`sparse_score` alongside the existing (now fused, for
hybrid) `score` — either can be `null` for a given chunk (a chunk with no BM25 term overlap has no
`sparse_score`; see docs/03-database.md section 19 for the small-corpus BM25 caveat). Dense-only
retrievals leave every hybrid-specific field `null`, exactly as before Phase 10.

**Query understanding (Phase 11)**: `query_understanding_enabled` (default `false`) opts a
retrieval into pre-search classification, rewrite, multi-query expansion, and metadata filter
extraction — see docs/03-database.md section 19 for the full pipeline description. The
`Retrieval` response gains `query_intent`, `intent_confidence`, `rewritten_query_text`,
`generated_queries` (`list[str]`), and `detected_metadata_filter` — all `null` when
`query_understanding_enabled` is `false`, and only populated once the retrieval reaches
`status: "completed"` (they're computed by the worker, same as every other analysis field on this
resource). `detected_metadata_filter` is merged under any caller-supplied `metadata_filter` before
search — the caller's explicit filter always wins on a key conflict.

**Advanced retrieval (Phase 12)**: four independent opt-in flags, each defaulting off so
Phase 9-11 behavior is unchanged when unset — see docs/03-database.md section 19 for the full
pipeline description of each.

- `expand_to_parent` (default `false`): remaps each result to its parent chunk when one exists
  (Phase 6 `parent_child` chunk sets only; a no-op otherwise). Results that share a parent are
  merged, keeping the highest-scoring one.
- `use_mmr`/`mmr_lambda` (default `false`/`null`): diversifies the final result list via real
  Maximum Marginal Relevance over each candidate's embedding vector. `mmr_lambda` (0-1, higher
  favors relevance over diversity) defaults to `0.7` when `use_mmr` is `true` and omitted.
- `fusion_method` gains `rag_fusion`: N-way reciprocal rank fusion across every query variant's
  ranked list (docs/02-architecture.md section 103), instead of the max-score merge Phase 11 uses
  before Phase 10's 2-list dense/sparse fusion. **Requires `query_understanding_enabled: true`**
  (`422` otherwise) — fusing multiple query variants is RAG Fusion's entire premise. `rrf_k`
  applies the same way it does for plain `rrf`.
- `compress_context` (default `false`): compresses each result's chunk text to its query-relevant
  sentences. The results response gains `compressed_text` (`null` unless `compress_context` was
  set) — populated *alongside* the unabridged `chunk_text`, never replacing it.

**Reranking (Phase 13)**: `rerank_enabled` (default `false`) opts a retrieval into cross-encoder
reranking — see docs/03-database.md section 19 for the full pipeline description and provider
list. `reranker_provider` accepts `cross_encoder` (default when `rerank_enabled` is `true` and
this is omitted), `bge`, `flashrank`, `cohere`, or `jina`; the last two require the corresponding
`COHERE_API_KEY`/`JINA_API_KEY` to be configured on the worker (not exposed via this API — a
misconfigured cloud reranker fails the retrieval with `status: "failed"` and an explanatory
`status_message`, the same contract every other provider-gated failure in this API uses). The
results response gains `rerank_score` (`null` unless `rerank_enabled` was set) — populated
*alongside* `score`, `dense_score`, and `sparse_score`, never replacing any of them, so every
stage's signal stays independently inspectable.

# 16. Reranking APIs

Folded into the Retrieval APIs above (section 15) rather than a separate endpoint — reranking is
one more opt-in stage of the same `POST .../retrievals` request/response, not an independent
resource with its own lifecycle. See section 15's "Reranking (Phase 13)" entry.

# 17. Prompt APIs

Phase 14. Two resource families, each following an existing pattern in this API rather than
inventing a new one:

**Prompt templates** (repository-scoped, same create-requires-repository-ADMIN+/read-requires-
VIEWER+ pattern as `documents.py`):

- `POST /repositories/{repository_id}/prompt-templates` — always creates a **new version** under
  `name` (`version = max(existing for that name) + 1`); there is no PATCH/PUT for an existing
  version, since docs/02-architecture.md section 79 requires versions to coexist for experiment
  comparison, not be overwritten.
- `GET /repositories/{repository_id}/prompt-templates` — latest version per name.
- `GET /repositories/{repository_id}/prompt-templates/{name}/versions` — full version history for
  one template name, oldest first.
- `GET /repositories/{repository_id}/prompt-templates/{template_id}` — one version by id.
- `POST /repositories/{repository_id}/prompt-templates/{template_id}/archive` — sets
  `is_active=false`; the row is never deleted, since past `Prompt` rows may still reference it.

**Prompts** (nested under document/vector-index/retrieval, mirroring `retrievals.py`; building a
prompt is a read-oriented action over an already-completed retrieval, so it requires Document
VIEWER+ like creating a retrieval does, not ADMIN+):

- `POST .../retrievals/{retrieval_id}/prompts` — builds and returns a `Prompt` **synchronously**
  (no enqueue, no polling) — unlike Phase 9's `POST .../retrievals`, there is no Celery task here;
  token counting and context assembly are deterministic CPU-bound computation over data already
  fetched by the request. Body: either `prompt_template_id` or an inline `system_prompt` (422 if
  neither given), plus optional `formatting_instructions`/`output_schema` overrides,
  `model_context_window` (default 8192), `response_reserve_tokens` (default 1024),
  `order_by_page` (default false — see section 20's Context Window Builder note). 409
  `RETRIEVAL_NOT_COMPLETED` if the underlying retrieval hasn't finished yet.
- `GET .../retrievals/{retrieval_id}/prompts` — all prompts built from that retrieval, newest first.
- `GET .../retrievals/{retrieval_id}/prompts/{prompt_id}` — one prompt, including
  `rendered_prompt`, `citations`, and the full token breakdown.

# 18. LLM APIs

Phase 15. Two resource groups, both requiring authentication:

**Registry/health** (not tenant-scoped — describes the gateway itself):

- `GET /llm/models` — every registered `ModelSpec` across all six providers (OpenAI, Anthropic,
  Gemini, Groq, OpenRouter, Ollama): context window, per-1M-token pricing, capability flags.
- `GET /llm/models/{provider}/health` — `{provider, configured, healthy}`. `configured` reflects
  whether an API key (or, for `ollama`, nothing — it's self-hosted) is set; `healthy` additionally
  makes a real call to confirm the provider is actually reachable right now.

**Completions** (nested under a `Prompt`, same VIEWER+ pattern as reading one — generating a
completion from an already-built, already-citation-grounded prompt is a read-oriented action, not
a mutation):

- `POST .../retrievals/{retrieval_id}/prompts/{prompt_id}/completions` — generates and persists an
  `LLMRequest` **synchronously**. Body: optional `provider`+`model` together (422 if only one is
  given), or `routing_hint` (`fast`/`reasoning`/`large_context`/`low_budget`/`offline`) instead, or
  neither for the default model. 409 `PROMPT_NOT_COMPLETED` if the prompt hasn't finished building.
  Always returns 200 even when generation fails — a `status="failed"` row with `attempted_providers`
  filled in, mirroring how `POST .../prompts` handles a token-budget failure (Phase 14) rather than
  a bare 500.
- `GET .../retrievals/{retrieval_id}/prompts/{prompt_id}/completions` — every completion generated
  from that prompt, newest first.
- `GET .../retrievals/{retrieval_id}/prompts/{prompt_id}/completions/{request_id}` — one completion.
- `WS .../retrievals/{retrieval_id}/prompts/{prompt_id}/completions/stream` — token-by-token
  streaming per docs/02-architecture.md section 87's "LLM -> Gateway -> WebSocket -> Frontend"
  diagram and section 27 below. Browsers' native WebSocket API can't set a custom `Authorization`
  header on the handshake, so auth happens via the first message the client sends after the socket
  opens (`{"token": "<jwt>", "provider": ..., "model": ..., "routing_hint": ..., "json_mode": ...}`)
  — never a `?token=` query string, which would leak the token into server/proxy access logs.
  Server messages: `{"type": "delta", "text": ...}` per chunk, then either
  `{"type": "done", "provider", "model", "input_tokens", "output_tokens"}` or
  `{"type": "error", "message": ...}`.

# 19. Conversation APIs

Phase 16. Nested under document/vector-index (same granularity as retrievals), same VIEWER+
pattern as retrievals/prompts — starting or continuing a chat is a read-oriented action over an
existing index, not a mutation of it:

- `POST /documents/{document_id}/vector-indexes/{vector_index_id}/conversations` — creates a
  `Conversation`. Body: optional `title`, optional `prompt_template_id` (used as the base system
  prompt for every turn instead of the built-in default).
- `GET .../conversations` — every conversation for that document/vector-index, newest first.
- `GET .../conversations/{conversation_id}` — one conversation.
- `DELETE .../conversations/{conversation_id}` — hard-deletes the conversation row; `messages`/
  `conversation_summaries` cascade with it (`ON DELETE CASCADE`), unlike the vector-index delete
  path (section 12), since there is no external store involved here — everything lives in Postgres.
- `GET .../conversations/{conversation_id}/messages` — full message history, oldest first.
- `POST .../conversations/{conversation_id}/messages` — the one endpoint that does real work: a
  full retrieval → prompt → completion turn, run **synchronously** within the request (not
  enqueue-and-poll, since a chat message has no "come back later" UX). Body: `content` (1-4000
  chars). Internally: persists the user message, condenses it against prior history into a
  standalone query via a real Phase 15 LLM call (`app/core/conversation/condensation.py` — not a
  heuristic, since Phase 11's query understanding never sees prior turns), runs a real Phase 9
  retrieval, builds a real Phase 14 prompt (folding in short-term history and this user's Phase 16
  long-term custom instructions), generates a real Phase 15 completion, persists the assistant
  message, and summarizes the conversation if it's grown past the token threshold. Returns
  `{user_message, assistant_message}`. If the retrieval doesn't complete within 20s, returns a
  graceful fallback assistant message ("couldn't retrieve context... try again") rather than
  blocking indefinitely or erroring.
- `GET .../conversations/{conversation_id}/export` — returns the full transcript as
  `text/markdown` (`PlainTextResponse`, not the usual JSON envelope — there is nothing else a
  client would do with an export except display or save it as-is).

# 20. Memory APIs

Phase 16. Long-term conversation memory lives at the **repository** level, not nested under a
document or conversation — docs/02-architecture.md section 95 requires it to persist "across
conversations," so a document/vector-index-scoped path would be the wrong resource identity for
it. Same VIEWER+ pattern as reading repository-level resources:

- `GET /repositories/{repository_id}/conversation-memory` — returns (creating on first access if
  none exists yet) the calling user's `ConversationMemory` for that repository:
  `custom_instructions` (free text, appended to every conversation's system prompt) and
  `preferences` (JSONB, currently unused by any feature but reserved for future per-user settings).
  Scoped to `(user_id, repository_id)` — every user has their own instructions, never shared.
- `PATCH /repositories/{repository_id}/conversation-memory` — updates `custom_instructions` and/or
  `preferences` for the calling user.

Two items docs/02-architecture.md section 95 lists under long-term memory are honestly **not**
implemented as separate resources: "Frequently Accessed Repositories" is deliberately not stored —
`MemoryService.frequently_accessed_repositories` computes it live via a `GROUP BY`/`func.count`
query over existing audit/conversation data rather than a stale counter, and is not yet exposed
through a dedicated endpoint; "Saved Searches" has no resource at all yet, since nothing in this
API represents a savable "search" independent of a retrieval/conversation.

# Cache APIs (no dedicated section number in the original TOC)

Phase 17 (Intelligent Caching, docs/02-architecture.md section 148). One endpoint, authenticated but
not tenant-scoped — like `/llm/models`, this describes the caching *system* itself, not any one
repository's data:

- `GET /cache/stats` — hit/miss counts and computed hit ratio per cache type (`retrieval`,
  `prompt`, `semantic`, `metadata`), read from Redis counters (`app/core/cache/metrics.py`).

There is no create/delete/invalidate endpoint for any individual cache entry — invalidation is
handled internally, not exposed as an API surface: the Retrieval Cache's key already embeds the
embedding-version/index-version numbers Phase 7/8 bump on every regeneration (so a real re-embed or
rebuild naturally produces a new key), the Prompt Cache and Metadata Cache both TTL-expire, and the
Semantic Cache is explicitly purged by `index_worker.build_index` whenever its vector index is
rebuilt (see `docs/03-database.md`'s Semantic Cache Schema section for all three mechanisms).

# 21. Evaluation APIs

**Pending — Evaluation Engine phase.**

# 22. Benchmark APIs

**Pending — Benchmarking Framework phase.**

# 23. Experiment APIs

**Pending — Evaluation Engine phase.**

# 24. Analytics APIs

**Pending — Analytics Pipeline phase.**

# 25. Settings APIs

**Pending — not yet scheduled in `05-task.md`.**

# 26. Admin APIs

**Pending — not yet scheduled in `05-task.md`.**

# 27. WebSocket Events

Streaming LLM responses (Phase 15) is implemented — see section 18's `.../completions/stream`
route. Upload progress, processing status, and evaluation progress (docs/02-architecture.md
section 138) remain **pending**: Phases 4-6's document pipeline still uses REST polling
(`refetchInterval` on the frontend) rather than WebSocket, a gap this phase didn't retroactively
fix since it was out of scope for the LLM Gateway deliverable specifically.

# 28. Error Codes

Implemented today (`backend/app/core/exceptions.py`):

| Code                | HTTP Status | Meaning                                  |
|----------------------|-------------|-------------------------------------------|
| `VALIDATION_ERROR`    | 400 / 422   | Request failed schema or business validation |
| `UNAUTHORIZED`        | 401         | Missing/invalid credentials (Phase 1)     |
| `FORBIDDEN`           | 403         | Authenticated but not permitted (Phase 1) |
| `NOT_FOUND`           | 404         | Resource does not exist                   |
| `CONFLICT`            | 409         | Duplicate/conflicting state                |
| `HTTP_ERROR`          | varies      | Generic Starlette HTTP exception          |
| `INTERNAL_ERROR`      | 500         | Unhandled exception (never exposes internals) |
| `RATE_LIMIT_EXCEEDED` | 429         | Redis fixed-window limit hit (`backend/app/middleware/rate_limit.py`) |

Authentication-specific (Phase 1, all subclass the codes above):

| Code                | HTTP Status | Meaning |
|----------------------|-------------|---------|
| `EMAIL_TAKEN`         | 409         | Registration with an already-registered email |
| `INVALID_CREDENTIALS` | 401         | Wrong email/password on login |
| `ACCOUNT_LOCKED`      | 403         | 5+ consecutive failed logins; locked for 15 minutes |
| `INVALID_TOKEN`       | 401         | Access/refresh/reset token missing, malformed, or expired |
| `SESSION_REVOKED`     | 401         | Refresh token's session was logged out |
| `SESSION_EXPIRED`     | 401         | Refresh token's session TTL elapsed |
| `USER_NOT_FOUND`      | 404         | Referenced user no longer exists |

Multi-tenancy-specific (Phase 2):

| Code                      | HTTP Status | Meaning |
|----------------------------|-------------|---------|
| `ORGANIZATION_NOT_FOUND`    | 404         | Org doesn't exist or is soft-deleted |
| `WORKSPACE_NOT_FOUND`       | 404         | Workspace doesn't exist or is soft-deleted |
| `PROJECT_NOT_FOUND`         | 404         | Project doesn't exist or is soft-deleted |
| `NOT_A_MEMBER`              | 403         | Caller has no membership row at this level |
| `OWNER_REQUIRED`            | 403         | Action requires the OWNER role specifically |
| `SLUG_TAKEN`                | 409         | Slug already used (scope depends on level: global for orgs, per-parent for workspaces/projects) |
| `ALREADY_MEMBER`            | 409         | Invitee is already a member of the organization |
| `INVITE_ALREADY_PENDING`    | 409         | A pending invitation already exists for that email |
| `INVITATION_NOT_PENDING`    | 409         | Invitation was already accepted/rejected/expired |
| `INVITATION_EXPIRED`        | 401         | Invitation's 7-day TTL has elapsed |
| `EMAIL_MISMATCH`            | 403         | Accepting/rejecting user's email doesn't match the invitation |

Repository-specific (Phase 3):

| Code                       | HTTP Status | Meaning |
|-----------------------------|-------------|---------|
| `REPOSITORY_NOT_FOUND`      | 404         | Repository doesn't exist or is soft-deleted |

(`NOT_A_MEMBER`, `OWNER_REQUIRED`, and `SLUG_TAKEN` are reused from the Phase 2 table above —
repositories follow the identical org/workspace/project RBAC and slug-uniqueness pattern.)

Document-specific (Phase 4):

| Code                    | HTTP Status | Meaning |
|--------------------------|-------------|---------|
| `DOCUMENT_NOT_FOUND`      | 404         | Document doesn't exist or is soft-deleted |
| `DUPLICATE_DOCUMENT`      | 409         | Identical `sha256_hash` already exists in this repository |
| `UNSUPPORTED_EXTENSION`   | 400         | File extension not in the allowlist |
| `FILE_TOO_LARGE`          | 400         | File exceeds `max_upload_size_bytes` (500 MB) |
| `EMPTY_FILE`              | 400         | Uploaded file is zero bytes |
| `PASSWORD_PROTECTED_FILE` | 400         | PDF is encrypted (detected via `pypdf`) |
| `VIRUS_DETECTED`          | 400         | Reserved for when `scan_for_viruses` becomes a real scanner (always passes today) |

(`NOT_A_MEMBER` and repository-role checks are reused as-is; a document's membership is resolved
via its `repository_id`, not a separate document-level membership table.)

Domain-specific codes (e.g. `DOCUMENT_NOT_FOUND`) are added by raising a subclass of `AppError`
(`backend/app/core/exceptions.py`) with a specific `code` as each domain is implemented — never
by hardcoding strings inline in controllers.

# 29. Pagination Standards

`backend/app/repositories/base.py::BaseRepository.list(limit, offset)` implements
offset/limit pagination for the base case. Response `metadata` will carry `total`, `limit`,
`offset` once the first paginated list endpoint (Organizations, Phase 2) ships. Keyset
pagination is adopted for high-volume resources (documents, chunks) when those phases land.

# 30. Versioning Strategy

URL-based versioning: `/api/v1/...`, reserving `/api/v2/` and `/api/internal/` per
docs/02-architecture.md section 134. Breaking changes require a new version prefix; additive
changes (new optional fields, new endpoints) ship within `v1`.
