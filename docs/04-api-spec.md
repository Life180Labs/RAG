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

**Pending — Embedding Pipeline phase.**

# 12. Embedding APIs

**Pending — Embedding Pipeline phase.**

# 13. Vector Index APIs

**Pending — Embedding Pipeline phase.**

# 14. Search APIs

**Pending — Retrieval Architecture phase.**

# 15. Retrieval APIs

**Pending — Retrieval Architecture phase.**

# 16. Reranking APIs

**Pending — Reranking Architecture phase.**

# 17. Prompt APIs

**Pending — Prompt Builder phase.**

# 18. LLM APIs

**Pending — LLM Gateway phase.**

# 19. Conversation APIs

**Pending — Conversation Memory phase.**

# 20. Memory APIs

**Pending — Conversation Memory phase.**

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

**Pending.** Used for upload progress, processing status, streaming LLM responses, and
evaluation progress per docs/02-architecture.md section 138. Introduced alongside the Document
Processing and LLM Gateway phases.

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
