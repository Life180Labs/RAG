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

**Pending — Phase 2.** CRUD + archive/restore per `05-task.md` Phase 2 API section.

# 5. Workspace APIs

**Pending — Phase 2.**

# 6. Project APIs

**Pending — Phase 2.**

# 7. Repository APIs

**Pending — Phase 3.**

# 8. Document APIs

**Pending — Document Processing phase.**

# 9. Upload APIs

**Pending — Document Processing phase.** Contract will match docs/02-architecture.md section 22:
`POST /api/v1/documents/upload` returns `{"document_id": "...", "status": "processing"}`
immediately; processing happens asynchronously via workers.

# 10. Parsing APIs

**Pending — Document Processing phase.**

# 11. Chunking APIs

**Pending — Chunking Engine phase.**

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
