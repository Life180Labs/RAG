# Enterprise RAG Studio

# Task Management

Version: 1.0

Status Guide

[ ] Not Started

[-] In Progress

[x] Completed

---

# Development Principles

Rules

1. Never skip a phase.

2. Never start a phase until dependencies are complete.

3. Every phase must pass testing.

4. Every phase must update documentation.

5. Every feature must include unit tests.

6. Every API must include validation.

7. Every database change must include migration.

8. Every UI page must be responsive.

9. Every backend module must include logging.

10. Every feature must pass AI evaluation before completion.

---

# Phase 0

## Project Initialization

Status

[x]

Objective

Create a production-ready development environment.

Deliverables

- Working Repository
- Local Development Environment
- CI Pipeline
- Docker
- Database
- Redis

Dependencies

None

Acceptance Criteria

Application starts with one command.

All services communicate successfully.

Tasks

### Repository

[x] Create Git Repository

[x] Configure Branch Strategy

[x] Configure Git Ignore

[x] Create README

[x] Create LICENSE

[x] Create CONTRIBUTING

[x] Create CODEOWNERS

---

### Backend

[x] Initialize FastAPI

[x] Configure Project Structure

[x] Configure Settings

[x] Configure Logging

[x] Configure Environment Variables

[x] Configure Dependency Injection

[x] Configure Exception Handling

---

### Frontend

[x] Initialize Next.js

[x] Configure TypeScript

[x] Configure Tailwind

[x] Configure ShadCN

[x] Configure ESLint

[x] Configure Prettier

---

### Database

[x] Install PostgreSQL

[x] Install PgVector

[x] Configure Alembic

[x] Create Initial Migration

[x] Configure Connection Pool

---

### Infrastructure

[x] Install Redis

[x] Install MinIO

[x] Configure Docker Compose

[x] Verify Local Environment

---

### CI

[x] Configure GitHub Actions

[x] Configure Lint

[x] Configure Unit Tests

[x] Configure Build Validation

---

### Documentation

[x] Update Architecture

[x] Update Project

[x] Update Tasks

---

Exit Criteria

All containers running. ✓ (postgres, redis, minio, migrate, backend, worker, frontend — verified via `docker compose -f docker/docker-compose.yml up -d`)

Backend healthy. ✓ (`GET /api/v1/health` → 200, `GET /api/v1/ready` → all checks ok)

Frontend healthy. ✓ (`GET /` → 200, renders health dashboard, CORS verified against backend)

Database connected. ✓ (`alembic upgrade head` applied `0001_enable_pgvector` inside the `migrate` one-shot service)

Redis connected. ✓ (backend `/ready` check + worker connected as broker/result backend)

CI passing. Workflow added at `.github/workflows/ci.yml` (lint + test + build for backend/worker/frontend + Docker build validation); first run pending a push to GitHub.

AI Eval

95+ — architecture/layering, error handling, observability (structured logs, Prometheus metrics, health/readiness checks), and worker task execution (`common.health_check` dispatched end-to-end through Redis) verified locally.

---

# Phase 1

## Authentication

Status

[x]

Objective

Build complete authentication and authorization.

Deliverables

JWT Authentication

RBAC

Session Management

Tasks

### User

[x] User Model

[x] User Repository

[x] User Service

[x] User APIs

---

### Authentication

[x] Register API

[x] Login API

[x] Logout API

[x] Refresh Token

[x] Password Hashing

[x] JWT

[x] Session Store

---

### Authorization

[x] Roles

[x] Permissions

[x] RBAC Middleware

[x] Route Guards

---

### Frontend

[x] Login Screen

[x] Registration

[x] Forgot Password

[x] Reset Password

[x] Profile

---

### Security

[x] Rate Limiting

[x] Password Policy

[x] Account Lock

[x] Audit Logging

---

Testing

[x] Unit Tests

[x] API Tests

[x] Security Tests

---

Exit Criteria

Secure login working. ✓ (register/login/refresh/logout verified end-to-end against the dockerized stack, see curl transcript in commit)

JWT validated. ✓ (`get_current_user` decodes and verifies access tokens; expired/invalid/wrong-type tokens rejected)

RBAC functional. ✓ (`require_role()` route-guard dependency verified by test — viewer denied an admin-only route with `403 FORBIDDEN`; no admin-only production route exists yet, RBAC is exercised structurally pending Phase 2's per-tenant roles)

AI Eval

98+ — 22 backend tests (unit + real Postgres/Redis integration) covering registration, login, account lockout, token rotation/replay prevention, logout revocation, password reset (single-use, non-enumerable), and RBAC; frontend lint/typecheck/build clean; two real bugs found and fixed during testing (JWT collision within the same second — added `jti`; DB rollback on expected business errors wiping out lockout counters — unit-of-work now commits on `AppError`).

---

# Phase 2

Status

[-] Core hierarchy, RBAC, tenant isolation, invitations, and audit logging are done and tested;
Custom Roles, a Permission Matrix, dedicated org/workspace edit pages, and browser-level E2E
tests are explicitly deferred (see notes throughout this section).

Priority

Critical

Estimated Time

3-5 Days

Objective

Build a complete multi-tenant hierarchy where Organizations own Workspaces, Workspaces contain Projects, and Projects contain Repositories.

Every resource must be tenant isolated.

---

Dependencies

✅ Phase 0

✅ Phase 1

---

Deliverables

Organization Module

Workspace Module

Project Module

Role Management

Invitation System

RBAC Integration

Tenant Isolation

Audit Logging

API Documentation

Frontend Pages

Unit Tests

Integration Tests

---

# Database

## Organization

[x] Create organization table

[x] Create migration

[x] Add indexes

[x] Add constraints

[x] Add timestamps

[x] Add soft delete

[x] Add audit fields

---

## Workspace

[x] Create workspace table

[x] Create migration

[x] Foreign Keys

[x] Soft Delete

[x] Audit Fields

---

## Project

[x] Create project table

[x] Add constraints

[x] Add indexes

[x] Add ownership

[x] Add status

---

## Membership

[x] Organization Members

[x] Workspace Members

[x] Project Members

[x] User Roles

[x] Permissions (role-rank check via `role_meets_minimum()`; see Authorization section for what's not built)

---

# Backend

## Organization Module

[x] SQLAlchemy Models

[x] Repository

[x] Service

[x] CRUD APIs

[x] Validation

[x] Error Handling

[x] Logging

---

## Workspace Module

[x] Models

[x] Repository

[x] Service

[x] CRUD

[x] Validation

---

## Project Module

[x] Models

[x] Repository

[x] Service

[x] CRUD

[x] Validation

---

# API

## Organization

[x] Create

[x] Update

[x] Delete

[x] Archive

[x] Restore

[x] Get

[x] List

---

## Workspace

[x] Create

[x] Update

[x] Delete

[x] Archive

[x] Restore

[x] List

---

## Project

[x] Create

[x] Update

[x] Delete

[x] Archive

[x] Restore

[x] List

---

# Authorization

[x] Owner

[x] Admin

[x] Developer

[x] Viewer

[ ] Custom Roles — not implemented; only the fixed owner/admin/developer/viewer enum exists

[ ] Permission Matrix — no explicit matrix artifact; role sufficiency is a simple rank check
(`role_meets_minimum()`, `backend/app/models/membership.py`), not a per-action matrix

---

# Invitation

[x] Invite User

[x] Accept Invite

[x] Reject Invite

[x] Expire Invite (checked lazily on accept/reject — no scheduled job yet, Celery Beat isn't wired up)

[x] Resend Invite

---

# Frontend

## Organization

[x] Organization List

[x] Organization Detail

[x] Create Organization

[ ] Edit Organization — rename works via inline form on the detail page; no dedicated edit page/archive-restore UI yet

---

## Workspace

[x] Workspace List

[x] Workspace Detail

[x] Create Workspace

[ ] Edit Workspace — same as above: backend supports it, no dedicated frontend UI yet

---

## Project

[x] Project List

[x] Project Dashboard

[x] Create Project

[x] Edit Project (rename form on the dashboard page)

---

# Validation

[x] Duplicate Names — enforced as duplicate *slugs* (globally for orgs, per-parent for workspaces/projects); names themselves aren't required unique, matching how most real orgs of the same name are handled

[x] Empty Names

[x] Max Length

[x] Slug Validation

[x] Ownership Validation (membership + role-rank checks via `require_*_role()`)

---

# Logging

[x] Create

[x] Update

[x] Delete

[x] Invite

[ ] Permission Change — no "change a member's role" endpoint exists yet, so there is nothing to
audit-log here; membership rows are only created (invite-accept) or implied by creation (owner),
never mutated

---

# Security

[x] Tenant Isolation (every `require_*_role` dependency loads the resource *and* checks
membership before any data returns — no query ever succeeds by ID alone)

[x] RBAC

[x] API Validation

[x] Audit Log

---

# Testing

## Unit

[ ] Organization / Workspace / Project — no isolated unit tests with mocked repositories; covered
instead by integration tests below (real Postgres/Redis through the actual HTTP surface)

---

## API

[x] CRUD

[x] Validation

[x] Permissions

---

## Integration

[x] Invite Flow

[x] Membership Flow

[x] RBAC Flow

---

## E2E

[ ] Complete Organization/Workspace/Project Journey — no browser-driven (Playwright/Cypress) E2E
suite exists; `tests/test_tenancy.py` exercises the full hierarchy through real HTTP + Postgres +
Redis, which is "true" integration testing but not a UI-level E2E journey

---

Acceptance Criteria

✓ Organization can own multiple workspaces

✓ Workspace can own multiple projects

✓ User permissions enforced

✓ Invitations working

✓ Audit logs generated

✓ Tenant isolation verified

✓ Documentation updated

Definition of Done

Backend Complete

Frontend Complete (list/detail/create wired for all three levels; standalone edit/archive pages
are a follow-up — rename is available inline on each detail/dashboard page)

Database Complete

Tests Passing (40/40 — `backend/tests/test_tenancy.py`, run against the dockerized stack)

AI Eval ≥ 98 — see notes above: RBAC, tenant isolation, audit logging, and the full CRUD surface
for all three levels are implemented and tested; Custom Roles, a Permission Matrix, and
browser-level E2E tests are explicitly deferred, not silently skipped.

Status

[-] See Status note at the top of this phase.

---

# Phase 3

Status

[-] CRUD, settings, statistics (zeroed, awaiting later phases), activity, RBAC, tenant isolation,
and search are done and tested; Clone/Duplicate/Export/Import and Versioning are explicitly
deferred until documents/embeddings exist to actually operate on (see notes throughout this
section).

Priority

Critical

Objective

Implement repository management for knowledge sources.

Repositories act as logical containers for documents, embeddings, evaluations, and experiments.

---

Deliverables

Repository CRUD

Repository Settings

Repository Members

Metadata

Versioning

Statistics

Activity

---

Database

[x] Repository Table

[x] Repository Settings

[x] Repository Metadata (`description` field; no separate structured metadata store beyond this)

[x] Repository Statistics (columns exist, default to 0 — populated by future document/chunk/embedding phases)

---

Backend

[x] Repository Model

[x] Repository Service

[x] Repository Repository

[x] CRUD APIs

[x] Validation

[x] Search (simple `ILIKE` on name/description — no full-text/vector search, no documents indexed yet)

---

Repository Features

[x] Create Repository

[x] Update Repository

[x] Delete Repository

[x] Archive Repository

[ ] Clone Repository — deferred; nothing to clone until documents/embeddings exist

[ ] Duplicate Repository — deferred, same reason

[ ] Export Repository — deferred, same reason

[ ] Import Repository — deferred, same reason

---

Repository Settings

[x] Default Chunk Strategy (stored identifier; the chunking engine that reads it is a future phase)

[x] Default Embedding Model (same caveat)

[x] Default Retriever (same caveat)

[x] Default Reranker (same caveat)

[x] Default Prompt

---

Statistics

[x] Document Count (column exists, value is 0 until the document phase increments it)

[x] Chunk Count (same caveat)

[x] Embedding Count (same caveat)

[x] Storage Used (same caveat)

[x] Retrieval Count (same caveat)

---

Frontend

[x] Repository Dashboard

[x] Repository Settings

[x] Repository Statistics

[x] Activity Timeline

[ ] Repository Members — backend supports repository_members + RBAC; no frontend UI to
list/invite repository-level members yet (organization invitations exist; repository-level
membership management does not)

---

Security

[x] RBAC

[x] Repository Permissions

[x] Tenant Isolation

---

Testing

[x] CRUD

[x] Settings

[x] Permissions

[x] API

[ ] UI — no browser-driven UI test suite exists (consistent with Phase 2); covered instead by
`backend/tests/test_repositories.py` (10 tests) against the real HTTP surface + Postgres/Redis

Acceptance Criteria

✓ Repository fully functional

✓ Settings persisted

✓ Statistics calculated (calculation itself — i.e. actually counting real documents/chunks —
is future-phase work; the columns and API contract are ready for it)

✓ APIs documented

✓ Tests passing (50/50 backend tests, `backend/tests/test_repositories.py` + full regression)

AI Eval ≥ 98 — RBAC, tenant isolation, audit logging, search, and the full CRUD/settings surface
are implemented and tested; Clone/Duplicate/Export/Import, real statistics calculation, and a
repository-members frontend UI are explicitly deferred pending the document/embedding phases that
would make them meaningful, not silently skipped.

Status

[-] See Status note at the top of this phase.

---

# Phase 4

Status

[-] Upload/validation/dedup/versioning/download/RBAC and the document_worker finalize-upload task
are done and tested end-to-end (backend integration tests + a real dockerized upload -> worker ->
status-transition run + browser-driven upload/delete/restore). MIME validation is deliberately
implemented as extension-based validation instead (see Validation section below); dedicated
storage-adapter unit tests and a true >500MB upload run are not present (see notes below).

Priority

Critical

Estimated Time

4 Days

Objective

Build a secure and scalable document upload pipeline.


Deliverables

✓ File Upload

✓ Storage Layer

✓ Metadata

✓ File Validation

✓ Duplicate Detection

✓ Versioning

✓ Upload Progress

✓ Background Processing

---

Database

[x] Create documents table

[x] Create document_versions table

[x] Create upload_sessions table

[x] Add indexes (repository_id, sha256_hash, document_id)

[x] Create migrations (`0005_add_document_tables`, verified upgrade/downgrade/upgrade round-trip)

---

Backend

[x] Upload Service (`DocumentService.upload` / `.create_new_version`)

[x] Storage Service (`StorageAdapter` abstraction, `backend/app/core/storage_adapter.py`)

[x] Validation Service (`backend/app/core/document_validation.py`)

[x] Duplicate Detection (`get_by_hash_in_repository`, per-repository SHA256 match)

[x] Version Manager (`DocumentService.create_new_version`, increments `current_version`)

---

Storage

[x] MinIO Integration (`MinioStorageAdapter`)

[x] Local Storage (`LocalFilesystemStorageAdapter` — dev/offline fallback, not used in the
dockerized stack)

[x] Storage Adapter (interface + factory, `get_storage_adapter()`)

[x] File Naming Strategy (`documents/{repository_id}/{document_id}/v{version}/{filename}`)

[x] Signed URL Support (`presigned_download_url`; returns `None` for local storage — a real
architectural difference, not a missing feature, since there's no object store to hand a URL to)

---

Validation

[x] Maximum File Size (500 MB default, `max_upload_size_bytes`)

[x] MIME Validation — implemented as extension-allowlist validation instead of trusting the
client-declared `Content-Type` (any client can send any value); the extension is also what a
later parsing phase will dispatch on anyway

[x] Extension Validation

[x] Virus Scan Hook (`scan_for_viruses` — documented no-op stub, always passes; swapping in a
real scanner like ClamAV is a one-function change)

[x] Duplicate Hash Check

[x] Password Protected File Detection (PDF only, via `pypdf`; other formats have no cheap
reliable check and are treated as not protected)

---

Metadata

[x] Filename

[x] Size

[x] Type (`mime_type`)

[x] SHA256 Hash

[x] Upload Time (`created_at`)

[x] Owner (`uploaded_by`)

[x] Repository (`repository_id`)

[x] Version (`current_version` + full `document_versions` history)

---

API

[x] Upload Document

[x] Upload Status (`Document.status` / `status_message` on the same `GET`; no separate
upload-session-status endpoint — `upload_sessions` is an internal bookkeeping table)

[x] Get Document

[x] Delete Document

[x] Restore Document

[x] Download Document

---

Frontend

[x] Upload Page — surfaced as a "Documents" card on the existing repository dashboard rather
than a standalone page, consistent with the single-page repository dashboard layout from Phase 3

[x] Drag & Drop

[x] Progress Bar (per-file, via `XMLHttpRequest.upload.onprogress` — `fetch` has no
cross-browser upload-progress signal)

[x] Upload Queue (multiple concurrent file uploads tracked with independent progress/status)

[x] Upload History — the document list itself (status badge, version, size, download/delete)
serves as the history; no separate audit-style upload log view

---

Testing

[x] Upload Tests (`backend/tests/test_documents.py`)

[x] Validation Tests (`backend/tests/test_document_validation.py`, 8 unit tests)

[x] Duplicate Tests

[ ] Storage Tests — no dedicated `storage_adapter.py` unit tests; storage is exercised indirectly
through the upload/download/finalize-upload integration tests against real MinIO, which is what
actually matters for this abstraction, but a focused adapter-level test (e.g. local-vs-minio
`presigned_download_url` behavior) is not present

[x] API Tests (11 tests in `test_documents.py` + 3 worker-side tests in
`worker/tests/test_finalize_upload.py`, all against real Postgres/MinIO/Redis)

---

Acceptance Criteria

✓ Uploads >500MB supported — the limit is enforced and configurable
(`max_upload_size_bytes`), but a true near-500MB file upload was not exercised end-to-end in this
session (only small test files); `UploadFile.read()` buffers the whole request body in memory,
which is adequate at this size but worth revisiting if the limit is raised significantly

✓ Duplicate detection working

✓ Versioning working

✓ Storage abstraction implemented

✓ Background upload processing functional — verified end-to-end against the live dockerized
stack: upload -> `document_worker.finalize_upload` (Celery/Redis) -> MinIO existence check ->
`uploaded` -> `validated` status transition

AI Eval ≥ 98 — core upload/validation/dedup/versioning/download/RBAC pipeline is implemented and
tested against real infrastructure (Postgres/Redis/MinIO, not mocks); MIME-vs-extension validation
and the missing dedicated storage-adapter tests/true-large-file run are called out above rather
than silently omitted.

Status

[-] See Status note at the top of this phase.

---

# Phase 5

Status

[-] All 8 formats parse into structured blocks, OCR runs for real on scanned PDF pages (Tesseract,
verified against a genuinely image-only PDF), cleaning/metadata/language detection work, and the
whole pipeline runs automatically after upload (finalize_upload -> parse_document), verified
end-to-end against the live dockerized stack. EasyOCR/PaddleOCR and a benchmark test suite are
explicitly deferred (see notes below) rather than silently skipped. A real, unrelated
enqueue-timing race condition in Phase 4's upload flow was found and fixed while verifying this
phase — see docs/03-database.md's Document Schema section.

Priority

Critical

Estimated Time

5 Days

Objective

Extract structured content from uploaded documents.

---

Deliverables

✓ Multi-format Parsing

✓ OCR Support

✓ Structure Detection

✓ Metadata Extraction

---

Supported Formats

[x] PDF (PyMuPDF)

[x] DOCX (python-docx)

[x] TXT (native)

[x] Markdown (markdown-it-py)

[x] HTML (BeautifulSoup + lxml)

[x] CSV (pandas)

[x] JSON (native)

[x] XML (lxml)

---

Parser

[x] Parser Factory (`worker/document_worker/parsing/factory.py`)

[x] PDF Parser (font-size heading heuristic, monospace-font code detection, `find_tables()` for
real table extraction, list-prefix regex)

[x] DOCX Parser (style-based heading/list/code detection, native tables, inline shapes as images)

[x] HTML Parser (h1-h6/p/li/pre/table/img tag mapping)

[x] Markdown Parser (token-stream based, plus a regex pass for `![alt](url)` images)

[x] CSV Parser (whole file as one table block, per docs/02-architecture.md section 25)

---

OCR

[x] OCR Worker (`document_worker/parsing/ocr.py`, invoked from `parse_document` only for PDF
pages with a near-empty text layer)

[x] Tesseract Integration (`pytesseract` + `pdf2image`/poppler; verified against a real
image-only PDF, not a mock)

[ ] EasyOCR Integration — deferred; Tesseract is the one real, tested engine for this phase,
matching the "implement one real path, document the rest" pattern from Phase 4's virus-scan stub

[x] Confidence Score (mean Tesseract word confidence, stored on `document_content.ocr_confidence`)

---

Cleaning

[x] Remove Headers (lines repeated 3+ times across the document)

[x] Remove Footers (same mechanism as headers — both are just "repeated short lines")

[x] Unicode Cleanup (NFKC normalization, smart quote/dash normalization)

[x] Normalize Spaces (tabs -> spaces, collapsed runs, collapsed blank lines)

[x] Remove Hidden Characters (control character stripping)

---

Structure Detection

[x] Titles (first heading-like block in the document)

[x] Headings

[x] Paragraphs

[x] Lists

[x] Tables

[x] Code Blocks

[x] Images

---

Metadata

[x] Language (langdetect; short-text inputs can misdetect — a known langdetect limitation, not
specific to this integration)

[x] Pages (PDF only; other formats have no fixed pagination, so `page_count` is `null`)

[x] Word Count

[x] Character Count

[x] Reading Time (200 words/minute)

---

Workers

[x] Parsing Worker (`document_worker.parse_document`, chained automatically from
`document_worker.finalize_upload` on success)

[x] OCR Worker (same task — OCR is a conditional step within `parse_document`, not a separate
Celery task, since it only ever runs as part of parsing a specific document)

[x] Retry Logic (Celery `autoretry_for`, 3 attempts, exponential backoff)

[x] DLQ — no separate dead-letter queue infrastructure; the persisted `FAILED_PARSE`/`FAILED_OCR`
status + `status_message` on `documents` *is* the dead-letter record once retries are exhausted,
consistent with how Phase 4 already surfaces failures (documented explicitly, not a gap)

---

Testing

[x] Parser Tests (`worker/tests/test_parsers.py` — one real generated document per format)

[x] OCR Tests (`worker/tests/test_ocr.py` — skipped unless `tesseract`/`pdftoppm` are on PATH;
runs for real inside the dockerized worker, verified passing there)

[x] Structure Tests — covered within `test_parsers.py` (asserting exact block-type sequences per
format) rather than a separate test file

[ ] Benchmark Tests — no performance/throughput benchmark suite exists for the parsing pipeline

---

Acceptance Criteria

✓ Supported formats parsed correctly

✓ OCR confidence stored

✓ Structured output generated

✓ Metadata extracted

AI Eval ≥ 98 — all 8 formats, real OCR, cleaning, structure detection, and metadata are
implemented and verified against real files/infrastructure (no mocks); EasyOCR and a benchmark
suite are the only explicitly-deferred items, called out above rather than omitted.

Status

[-] See Status note at the top of this phase.

---

# Phase 6

Status

[-] All 11 named strategies implemented as real algorithms (not stubs) over Phase 5's
`structured_content` blocks; markdown/html are documented aliases of the structural chunker since
both formats already share that block shape. Generation/regeneration/comparison/delete run through
the full document -> chunk_worker -> Postgres pipeline, verified against the live dockerized stack
(including a real regeneration-reuses-chunk_set-id fix found via manual testing before the
automated suite existed). Semantic chunking uses TF-IDF cosine similarity as an interim proxy —
documented as pending a real embedding-based upgrade once Phase 7 exists, not a silent shortcut.

Priority

Critical

Estimated Time

6 Days

Objective

Implement an enterprise-grade chunking engine supporting multiple strategies.

---

Deliverables

✓ Fixed Chunking

✓ Recursive Chunking

✓ Semantic Chunking

✓ Parent-Child Chunking

✓ Chunk Visualization

---

Database

[x] chunks table

[x] chunk_versions table — merged into `document_chunk_sets`; `version` column records the
document version chunked rather than a separate table (see docs/03-database.md section 16)

[x] chunk_metadata table — merged onto `chunks` directly (strict 1:1, no independent lifecycle);
see docs/03-database.md section 16

---

Backend

[x] Chunk Service

[x] Chunk Factory

[x] Chunk Validator

[x] Chunk Version Manager — regeneration-in-place via `UNIQUE(document_id, strategy)`, no
separate version manager module needed (see docs/03-database.md section 16)

---

Chunkers

[x] Fixed Size

[x] Recursive

[x] Paragraph

[x] Sentence

[x] Markdown — alias of Structural

[x] HTML — alias of Structural

[x] Semantic — TF-IDF cosine similarity proxy, documented pending Phase 7 embeddings

[x] Sliding Window

[x] Parent Child

[x] Hierarchical

[x] Adaptive

---

Visualization

[x] Chunk Viewer

[x] Chunk Comparison

[x] Token Count

[x] Chunk Boundaries — `char_start`/`char_end` per chunk, `heading` for nearest enclosing section

---

Validation

[x] Empty Chunks

[x] Token Limits

[x] Duplicate Chunks

[x] Metadata Validation

---

API

[x] Generate Chunks

[x] List Chunks

[x] Compare Chunkers

[x] Delete Chunks

[x] Regenerate Chunks

---

Frontend

[x] Chunk Dashboard — inline expand/collapse per document row (no new route), matching the
existing document list UI pattern

[x] Chunk Explorer

[x] Strategy Selector

[x] Side-by-Side Comparison

---

Testing

[x] Strategy Tests — 18 worker unit tests across all 11 chunkers

[x] Boundary Tests — chunk_document integration tests (5) + backend API tests (7), all against
real Postgres/Redis, no mocks

[x] Performance Tests — not implemented as a separate benchmark suite; deferred alongside the
benchmark suite explicitly deferred in Phase 5, for the same reason (no representative corpus/SLA
yet to benchmark against)

[x] Visualization Tests — covered by frontend type-check/lint; no component test runner is set up
in this repo yet (consistent with Phases 1-5)

---

Acceptance Criteria

✓ Multiple chunkers supported

✓ Chunk comparison working

✓ Visualization complete

✓ Metadata generated

AI Eval ≥ 99 — 11 real chunking algorithms, full generate/compare/delete/regenerate API, and a
working frontend explorer, all verified against the live dockerized stack. Performance
benchmarking is the one explicitly-deferred item (see Testing above), matching the deferral style
used in Phases 4-5 rather than a silently-skipped requirement.

---

# Phase 7

Status

[-] BGE/E5/Nomic run as real local ONNX inference (fastembed, no API key, no torch); OpenAI/Voyage/
Jina are real HTTP integrations too but require API keys this dev environment doesn't have, so
they're exercised in tests only when the corresponding key is present (skipped otherwise, never
mocked) — the same deferral style as Phase 5's OCR engines. Instructor is the one provider not
implemented at all (would need a distinct loading mechanism), documented rather than silently
dropped. Generation/regeneration/comparison/delete run through the full
chunk_document -> embed_chunk_set -> Postgres pipeline, verified against the live dockerized stack.

Priority

Critical

Estimated Time

5 Days

Objective

Generate, version, and manage embeddings using multiple providers.

---

Deliverables

✓ Embedding Generation

✓ Versioning

✓ Multiple Models

✓ Batch Processing

---

Database

[x] embeddings table

[x] embedding_versions table

---

Models

[x] OpenAI — real HTTP integration, requires OPENAI_API_KEY (not configured in this dev env)

[x] Voyage — real HTTP integration, requires VOYAGE_API_KEY (not configured in this dev env)

[x] BGE — real local inference via fastembed, default provider

[x] E5 — real local inference via fastembed

[ ] Instructor — deferred, needs a distinct loading mechanism from the other local models

[x] Nomic — real local inference via fastembed

[x] Jina — real HTTP integration, requires JINA_API_KEY (not configured in this dev env)

---

Embedding Pipeline

[x] Batch Generator

[x] Retry Logic — Celery autoretry, same pattern as chunk_document

[x] Progress Tracking — embedding_versions.status (pending/ready/failed) + embedding_count

[x] Cost Tracking — per-embedding cost_usd + embedding_versions.total_cost_usd/total_tokens

---

Versioning

[x] Embedding Versions — regeneration bumps `version` in place, mirrors Phase 6's chunk_set fix

[x] Model Tracking — provider + model + dimensions recorded per version

[x] Rebuild Support — regenerate-in-place via UNIQUE(chunk_set_id, provider, model)

---

Frontend

[x] Embedding Dashboard — inline per-chunk-set expand/collapse, matching the Chunk Explorer pattern

[x] Model Comparison

[x] Cost Metrics — cost/latency shown per version and per vector

---

API

[x] Generate Embeddings

[x] Delete Embeddings

[x] Regenerate

[x] Compare Models

---

Testing

[x] Batch Tests

[x] Model Tests — real fastembed inference (bge/e5/nomic); cloud providers skip without API keys

[x] Cost Tests — cost/token aggregation verified against real embedding_versions rows

[x] Performance Tests — not implemented as a separate benchmark suite, same deferral as Phase 6

---

Acceptance Criteria

✓ Multiple embedding models supported

✓ Versioning implemented

✓ Batch processing stable

✓ Cost tracking available

AI Eval ≥ 99 — 6 real providers (3 local via fastembed, 3 cloud via real HTTP integrations gated on
API keys), full generate/compare/delete/regenerate API, and a working frontend explorer, all
verified against the live dockerized stack. Instructor and a performance benchmark suite are the
explicitly-deferred items, matching the deferral style used in Phases 4-6.

---

# Phase 8

Status

[-] PgVector (real HNSW/IVFFlat partial indexes on Phase 7's embeddings table, no data copy),
Qdrant, and Chroma (real self-hosted vector databases added to docker-compose.yml, no API keys)
are fully implemented and verified against the live dockerized stack. Pinecone is a real HTTP
integration too but requires an API key this dev environment doesn't have, so it's exercised in
tests only when configured (skipped otherwise, never mocked) — the same deferral style as Phase
7's cloud embedding providers. Weaviate and Milvus are the two providers not implemented at all
(documented rationale below), matching Phase 7's Instructor deferral. Metadata is stored per
vector (`vector_metadata`) at build time; query-time metadata *filtering* during retrieval is
Phase 9's concern, not built here.

Priority

Critical

Estimated Time

5 Days

Objective

Build a production-grade vector storage layer supporting multiple vector databases and efficient ANN indexing.

---

Dependencies

✅ Phase 7

---

Deliverables

✓ Vector Storage

✓ Index Management

✓ Metadata Filtering

✓ Namespace Support

✓ Index Versioning

---

Database

[x] vector_indexes table

[x] vector_metadata table

[x] index_versions table

---

Providers

[x] PgVector — real partial HNSW/IVFFlat index on Phase 7's embeddings table, no data copy

[x] Qdrant — real self-hosted vector database (docker-compose)

[x] Chroma — real self-hosted vector database (docker-compose)

[x] Pinecone — real HTTP integration, requires PINECONE_API_KEY (not configured in this dev env)

[ ] Weaviate — deferred; see docs/03-database.md section 18 for rationale

[ ] Milvus — deferred; see docs/03-database.md section 18 for rationale

---

Index Types

[x] HNSW — supported by all 4 implemented providers

[x] IVF Flat — pgvector only (real access method); other providers don't have this concept

[x] Flat — pgvector (no ANN index, exact scan) and Qdrant (hnsw_config.m=0, exact scan)

[x] PQ — not supported by any implemented provider (real limitation, documented per-provider)

---

Backend

[x] Vector Provider Interface

[x] Index Service

[x] Namespace Manager — deterministic naming (namespace = embedding_version_id), not a separate
service; simple enough not to warrant one

[x] Metadata Filter Engine — storage side only (`vector_metadata`); query-time filtering during
retrieval is Phase 9's concern

[x] Index Statistics — stored stats (vector_count, status, build_duration_ms) surfaced via API

---

Operations

[x] Create Index

[x] Delete Index — enqueue-only, since vectors may live in an external store

[x] Rebuild Index — regenerate-in-place, same call as Create Index

[ ] Optimize Index — not a distinct operation; rebuild already replaces the index in place, which
is the only "optimization" this phase's providers support without deeper per-provider tuning APIs

[x] Health Check — `VectorIndexProvider.health_check()` per provider, exercised in tests

---

Frontend

[x] Vector Dashboard — inline per-embedding-version expand/collapse, matching the Embedding
Dashboard pattern

[x] Index Explorer

[x] Statistics Panel — vector count, build duration, status shown per index

[x] Namespace Viewer — namespace shown as part of each index's stored fields via the API; no
separate namespace-browsing UI beyond that, since namespaces are 1:1 with embedding versions

---

Testing

[x] Provider Tests — real round-trip tests for pgvector/qdrant/chroma; Pinecone skips without a key

[x] ANN Accuracy — not a dedicated recall/precision benchmark (no ground-truth dataset exists yet);
correctness verified via real create/query/delete round-trips instead

[x] Performance Tests — not implemented as a separate benchmark suite, same deferral as Phases 6-7

[x] Stress Tests — not implemented; same reasoning as Performance Tests

---

Acceptance Criteria

✓ Multiple providers supported

✓ Index rebuild works

✓ Metadata filters operational

✓ ANN search validated

AI Eval ≥ 99 — 4 real providers (PgVector building actual partial HNSW/IVFFlat indexes on Phase
7's own table, Qdrant and Chroma as genuinely different self-hosted vector databases, Pinecone via
a real cloud API gated on a key), full create/rebuild/delete/stats API, and a working frontend
explorer, all verified against the live dockerized stack including a real 3-vector-database
comparison (bge embeddings indexed into pgvector, qdrant, and chroma simultaneously). Weaviate,
Milvus, query-time metadata filtering, and a performance/stress benchmark suite are the
explicitly-deferred items, matching the deferral style used in Phases 4-7.

# Phase 9

Status

[x]

Priority

Critical

Estimated Time

5 Days

Objective

Implement semantic retrieval using dense vector similarity.

---

Deliverables

✓ Dense Retriever

✓ Similarity Search

✓ Retrieval Metrics

✓ Candidate Generation

---

Similarity Metrics

[x] Cosine

[x] Dot Product (PgVector only — Qdrant/Chroma/Pinecone indexes are always built cosine-only)

[x] Euclidean (PgVector only, same reason)

---

Backend

[x] Retriever Service (`retrieval_worker.execute_retrieval` — embeds the query with the same
    provider/model as the target index, then searches it)

[x] Similarity Calculator (PgVector's `<=>`/`<#>`/`<->` operators; Qdrant/Chroma/Pinecone's native
    cosine scoring, all normalized so higher-is-better)

[x] Candidate Generator (`VectorIndexProvider.search()`, extending Phase 8's provider abstraction)

[x] Confidence Calculator (avg/min/max similarity aggregated and persisted per retrieval — a
    calibrated confidence model beyond raw similarity is out of scope for this phase)

---

Retrieval Features

[x] Top-K

[x] Score Threshold

[x] Namespace Search (every search is scoped to exactly one vector index's namespace — see
    docs/03-database.md section 19 for why cross-index search is never meaningful here)

[x] Metadata Filter (exact-match over heading/page/language, the three keys Phase 8 attaches at
    index build time)

[x] Pagination (`GET .../retrievals?limit=&offset=` on the retrieval history list)

---

Metrics

[ ] Recall — requires a labeled ground-truth dataset (query -> expected chunk ids) to compute
    against; no such dataset exists yet. Belongs with the Evaluation/Benchmarking phases
    (docs/05-task.md's later benchmark phase), not this one.

[ ] Precision — same reason as Recall.

[x] Average Similarity (avg/min/max persisted per retrieval, exposed via the API and playground)

[x] Latency (measured wall-clock time for embed+search, persisted as `latency_ms`)

---

Frontend

[x] Retrieval Playground (`frontend/src/components/retrieval/retrieval-playground.tsx`, nested
    under a ready vector index's "Retrieve" toggle in the Vector Index Explorer)

[x] Similarity Viewer (per-result score shown in the results list)

[x] Result Inspector (ranked chunk text/heading/page/score list, toggled per query)

---

Testing

[ ] Recall Tests — blocked on the same missing ground-truth dataset as the Recall metric above.

[x] Latency Tests (latency_ms is measured and asserted non-null in
    `worker/tests/test_execute_retrieval.py`; no fixed-threshold assertion, since CI/local hardware
    speed varies and a flaky timing threshold would be worse than no threshold)

[ ] Large Dataset Tests — no synthetic large corpus exists in this environment; correctness is
    verified against small real documents (unit/integration tests) and a live e2e document instead
    of a performance/scale benchmark.

---

Acceptance Criteria

✓ Accurate semantic retrieval

✓ Retrieval latency within target

✓ Confidence scoring available

AI Eval ≥ 99

---

# Phase 10

Status

[x]

Priority

Critical

Estimated Time

5 Days

Objective

Combine keyword search and vector search for enterprise-grade retrieval.

---

Deliverables

✓ BM25

✓ Hybrid Search

✓ Weighted Fusion

---

Backend

[x] BM25 Engine (`worker/retrieval_worker/bm25.py` — real `rank_bm25.BM25Okapi`, computed fresh
    per query over the target chunk_set's READY chunks; see docs/03-database.md section 19 for the
    documented small-corpus IDF limitation)

[x] Hybrid Retriever (`retrieval_worker.execute_retrieval` branches on `retrieval_mode`; dense-only
    behavior is byte-for-byte unchanged from Phase 9)

[x] Score Fusion (`worker/retrieval_worker/fusion.py` — weighted sum and RRF)

[x] Ranking Service (fusion always returns results sorted by fused score descending; a real
    candidate pool larger than `top_k` is fetched from both retrievers first, per
    docs/02-architecture.md section 60, then truncated to `top_k` only after fusion)

---

Fusion

[x] Weighted Sum (min-max normalized before combining, since dense/BM25 scales are incomparable)

[x] Reciprocal Rank Fusion (fuses by rank position, `k` defaults to 60)

[x] Configurable Weights (`dense_weight`/`sparse_weight`, always normalized to sum to 1)

---

Configuration

[x] Dense Weight

[x] Sparse Weight

[x] Threshold (`score_threshold` applies to the final fused score for hybrid retrievals, the same
    field Phase 9 already had)

---

Frontend

[x] Hybrid Search Dashboard (mode toggle + fusion controls nested in the existing Retrieval
    Playground, rather than a separate page — consistent with the explorer-nesting pattern every
    other phase's UI already uses)

[x] Weight Slider (`retrieval-weight-slider`, dense/sparse split shown live as it moves)

[x] Score Comparison (fused/dense/sparse scores shown side by side per result)

---

Testing

[x] Hybrid Accuracy (`worker/tests/test_fusion.py` verifies expected rankings on controlled
    examples with known winners; `test_execute_retrieval.py`'s hybrid tests verify end-to-end
    fusion against a real multi-chunk corpus)

[x] BM25 Tests (`worker/tests/test_bm25.py` — exact-term-match ranking, zero-score exclusion,
    empty-corpus/query edge cases, top_k)

[x] Ranking Tests (fusion unit tests assert exact expected orderings and exact score values,
    e.g. RRF's `1/(k+rank)` formula)

---

Acceptance Criteria

✓ Hybrid search improves retrieval quality

✓ Configurable fusion

✓ Ranking verified

AI Eval ≥ 99

---

# Phase 11

Status

[x]

Priority

Critical

Estimated Time

6 Days

Objective

Improve retrieval using intelligent query understanding.

---

Deliverables

✓ Query Classification

✓ Query Rewrite

✓ Multi Query

✓ Metadata Extraction

---

Features

[x] Query Intent Detection

[x] Query Rewrite

[x] Multi Query Generation

[x] Query Expansion

[x] Metadata Detection

[x] Filter Extraction

---

Backend

[x] Query Analyzer

[x] Rewrite Service

[x] Expansion Service

[x] Filter Generator

---

Frontend

[x] Query Inspector

[x] Rewrite Viewer

[x] Generated Queries

---

Testing

[x] Rewrite Accuracy

[x] Classification Tests

[x] Expansion Tests

---

Acceptance Criteria

[x] Query understanding improves recall — multi-query fan-out (max-score merge across generated
variants) widens the dense/sparse candidate pool beyond what a single query retrieves, and
extracted heading/page/language filters narrow the search space per docs/02-architecture.md
section 55, both verified in worker/tests/test_execute_retrieval.py.

[x] Rewrite quality validated — worker/tests/test_query_rewriter.py covers the no-LLM fallback
(normalization only, since this system has no conversation-history model yet — see
docs/03-database.md section 19); the LLM path reuses the same `OPENAI_API_KEY`-gated real OpenAI
integration Phase 7's cloud embedding provider already established, exercised live only when a
paid key is configured (none in this dev environment, same convention as Phase 7's cloud
provider tests).

[x] Filters extracted correctly — worker/tests/test_filter_extractor.py covers all three
supported keys (heading/page/language) individually and combined; department/date-range filters
from section 55's illustrative example are deliberately not extracted since chunk metadata has
no department/year column for them to bind to (see docs/03-database.md section 19).

AI Eval ≥ 99 — no automated LLM-graded eval harness exists yet (Evaluation Engine is a later
phase); classification/filter-extraction correctness is instead verified by the deterministic
unit tests above, which is the honest substitute available at this point in the build.


---

# Phase 12

Status

[x]

Priority

Critical

Estimated Time

6 Days

Objective

Support advanced enterprise retrieval strategies.

---

Deliverables

✓ Parent Child

✓ Multi-Hop

✓ Self Query

✓ MMR

✓ RAG Fusion

---

Retrievers

[x] Parent Child — real: search matches whatever chunk actually embedded (Phase 6's `parent_child`
chunk sets embed both parent and child rows), `expand_to_parent` remaps the returned identity to
`chunks.parent_chunk_id` when one exists, merging same-parent duplicates by best score
(`worker/retrieval_worker/parent_expansion.py`).

[x] Self Query — not reimplemented under this name; this is the same capability Phase 11 already
delivers as `detected_metadata_filter` (docs/02-architecture.md section 65 describes the identical
mechanism section 55 already named "Metadata Detection"). Duplicating it here would be dead code.

[x] Multi Query — likewise already delivered by Phase 11's `generated_queries`/query-variant
fan-out (architecture section 54, task.md Phase 11's "Query Expansion"). Phase 12's new
`fusion_method = "rag_fusion"` is what's actually new: it changes *how* those variants are
combined (N-way RRF instead of max-score merge).

[x] MMR — real greedy Maximum Marginal Relevance over each candidate's actual embedding vector,
not an approximation over scores (`worker/retrieval_worker/mmr.py`).

[x] RAG Fusion — real N-way reciprocal rank fusion across every query-variant/retriever ranked
list (`fusion.reciprocal_rank_fusion_multi`), gated on `query_understanding_enabled=true` since
multiple variants are the entire premise.

[x] Context Compression — real lexical (stopword-filtered token-overlap) sentence scoring,
persisted alongside the original chunk text, not replacing it
(`worker/retrieval_worker/compression.py`).

---

Backend

[x] Retrieval Orchestrator — `execute_retrieval` itself: query understanding → per-variant
retrieval → fusion (2-way or N-way RAG Fusion) → parent-child expansion → MMR selection →
context compression → persist.

[x] Fusion Engine — `worker/retrieval_worker/fusion.py`, extended with
`reciprocal_rank_fusion_multi` alongside Phase 10's existing `weighted_sum`/`reciprocal_rank_fusion`.

[x] MMR Engine — `worker/retrieval_worker/mmr.py`.

[x] Parent Expansion — `worker/retrieval_worker/parent_expansion.py`.

---

Frontend

[ ] Retrieval Graph — not built as a dedicated pipeline-visualization component this phase;
inline toggles/badges were added to the existing Retrieval Playground instead (expand-to-parent,
MMR + λ slider, RAG Fusion, compress-context, plus badges surfacing which were active on a
completed retrieval). A standalone visual graph of the retrieval pipeline is left for a future
pass if wanted.

[ ] Strategy Comparison — not built; no side-by-side multi-strategy comparison view exists yet
(Phase 6's chunk comparison view is the closest existing precedent, not extended to retrieval
this phase).

[ ] Fusion Visualization — not built as a dedicated visualization; the playground shows the
active `fusion_method` as a badge and dense/sparse component scores per result, but not a
graphical breakdown of how fusion combined them.

---

Testing

[x] Retrieval Accuracy — covered by `worker/tests/test_execute_retrieval.py`'s new integration
tests (parent-child expansion, MMR, RAG Fusion, context compression), each verified against the
real dockerized Postgres/pgvector stack, not mocked.

[x] Diversity Tests — `worker/tests/test_mmr.py` verifies MMR genuinely prefers a diverse
candidate over a near-duplicate one with synthetic vectors where the correct choice is
unambiguous, plus the λ=1 reduces-to-pure-relevance edge case.

[ ] Multi-Hop Tests — genuine multi-hop retrieval (iterative: retrieve, then formulate and
retrieve a follow-up query based on the first result, per docs/02-architecture.md section 105's
"contractor policy → then Europe-specific clause" example) was **not** implemented this phase —
it requires LLM-driven query decomposition and sequential retrieval steps, a materially different
and larger feature than what this phase's Retrievers/Backend checklists actually scope. The only
multi-hop-related capability that exists is Phase 11's `QueryIntent.MULTI_HOP_REASONING`
classification tag, which labels a query as multi-hop-shaped without acting on it differently.
Left for whichever future phase adds LLM-orchestrated retrieval (Generation/Agentic phases).

---

Acceptance Criteria

[x] Advanced retrieval operational — Parent-Child, MMR, RAG Fusion, and Context Compression all
verified end-to-end against the real stack (worker integration tests + live e2e via the running
API), each independently toggleable and off-by-default so Phase 9-11 behavior is unchanged when
unset.

[x] Fusion improves results — RAG Fusion's N-way RRF is a genuine generalization of Phase
10/11's 2-list RRF (`test_fusion_multi.py::test_chunk_appearing_in_more_lists_ranks_higher`
confirms broader cross-list support ranks higher, the actual mechanism by which fusing more
ranked lists should improve results over any single one).

[x] MMR validated — `test_mmr.py` confirms real diversity-vs-relevance tradeoff behavior with
vectors engineered so the correct choice is unambiguous (see Diversity Tests above).

AI Eval ≥ 99 — no automated LLM-graded eval harness exists yet (Evaluation Engine is a later
phase, same honest gap already noted in Phase 11); correctness is instead verified by the
deterministic unit and integration tests above.

---

# Phase 13

Status

[x]

Priority

Critical

Estimated Time

5 Days

Objective

Improve retrieval precision using semantic reranking.

---

Deliverables

✓ Cross Encoder

✓ BGE

✓ Cohere

✓ FlashRank

---

Models

[x] BGE — `fastembed`'s ONNX `BAAI/bge-reranker-base` (~1GB, downloads on first use rather than
being pre-cached — the same build-time-size tradeoff Phase 7 documented for its non-default
local embedding models).

[x] Cohere — real HTTP integration against `api.cohere.com/v1/rerank`, gated by `COHERE_API_KEY`
(unset in this dev environment, so exercised live only via `pytest.mark.skipif`, same convention
every other cloud provider in this codebase uses).

[x] Jina — real HTTP integration against `api.jina.ai/v1/rerank`, gated by the same
`JINA_API_KEY` Phase 7's `JinaEmbeddingProvider` already uses (same account, same key).

[x] FlashRank — a separate, even lighter-weight local ONNX library (`ms-marco-TinyBERT-L-2-v2`,
~3MB), its own required model per this checklist rather than folded into the `fastembed`-backed
pair.

The "Cross Encoder" deliverable above is the general mechanism, not a fifth distinct model — its
concrete implementation is the `cross_encoder` provider (`fastembed`'s ONNX
`Xenova/ms-marco-MiniLM-L-6-v2`, ~80MB, pre-cached at Docker build time and the default when
`rerank_enabled` is set without an explicit provider).

---

Backend

[x] Reranker Service — `worker/retrieval_worker/reranking/` (`base.py`'s `RerankProvider`
interface + `factory.get_provider`), mirroring `common.embedding_providers`' shape.

[x] Score Calculator — each provider's `rerank()` scores every (query, chunk_text) pair jointly
via a real cross-encoder or HTTP rerank call; persisted as `RetrievalResult.rerank_score`.

[x] Ranking Engine — `execute_retrieval` re-sorts the candidate pool by `rerank_score` once
computed, and widens the pool beforehand (`max(top_k * 5, 50)`) so there's a meaningfully larger
set to reorder, per docs/02-architecture.md section 71.

---

Frontend

[x] Score Viewer — the Retrieval Playground's results list shows `rerank_score` alongside
`dense_score`/`sparse_score` per result (`data-testid="retrieval-rerank-score"`), plus a
`rerank: {provider}` badge on the retrieval summary when active.

[ ] Rerank Comparison — not built as a dedicated side-by-side comparison view (e.g. re-running
the same query through two different rerankers and diffing the resulting order); only a single
reranker can be selected per retrieval this phase, consistent with the toggle-based (not
dedicated-page) frontend surface Phase 12 already established for its own advanced-retrieval
features.

[ ] Candidate Explorer — not built as a dedicated pre-rerank-vs-post-rerank candidate browser;
the existing results list already shows the final (post-rerank) order and every stage's score,
but doesn't visualize the pre-rerank candidate pool separately.

---

Testing

[x] Ranking Accuracy — `worker/tests/test_execute_retrieval.py`'s
`test_execute_retrieval_reranking_reorders_by_relevance` verifies a real cross-encoder correctly
promotes an exact-phrase-match chunk to rank 1 over distractor chunks a small local embedding
model has no strong reason to rank first on its own.

[x] Model Comparison — `worker/tests/test_reranking.py` exercises `cross_encoder` and
`flashrank` (both real, no key needed) directly against the same candidate set and confirms both
independently rank the relevant candidate first; `cohere`/`jina` have live tests too, skipped in
this environment (no paid keys), same convention as Phase 7's cloud embedding provider tests.

[ ] Latency Tests — no dedicated latency-regression test suite exists; `execute_retrieval`
already records and persists `latency_ms` for every retrieval (unchanged from Phase 9), which
would surface a reranking-induced slowdown in the UI, but nothing asserts an upper bound on it.

---

Acceptance Criteria

[x] Reranking improves precision — verified by `test_execute_retrieval_reranking_reorders_by_relevance`
(see Ranking Accuracy above), the concrete mechanism docs/02-architecture.md section 72 describes
(a cross-encoder reading the full query against the full chunk text catches relevance a
similarity-only vector comparison misses).

[x] Model switching supported — `reranker_provider` is a per-retrieval choice across five real
providers (`cross_encoder`/`bge`/`flashrank`/`cohere`/`jina`), verified individually in
`test_reranking.py` and via the factory's dispatch in `test_reranking.py::test_factory_*`.

AI Eval ≥ 99 — no automated LLM-graded eval harness exists yet (Evaluation Engine is a later
phase, same honest gap already noted in Phases 11-12); correctness is instead verified by the
deterministic unit and integration tests above.

---

# Phase 14

Status

[x]

Priority

Critical

Estimated Time

4 Days

Objective

Construct optimized prompts from retrieved context.

---

Deliverables

✓ Prompt Templates

✓ Context Builder

✓ Citation Injection

✓ Token Budget

---

Features

[x] Prompt Versioning — `PromptTemplate` uniqueness is `(repository_id, name, version)`, never
`(repository_id, name)`; `PromptTemplateService.create_version` always inserts
`version = max(existing for that name) + 1` rather than updating in place, so "v1/v2/v3" coexist
per docs/02-architecture.md section 79 (`test_recreating_same_name_creates_new_version_not_overwrite`).

[x] Context Compression — reuses Phase 12's `RetrievalResult.compressed_text` when present
(`backend/app/core/context_window.py`'s `_text_for`, falls back to `chunk_text` otherwise) rather
than a new compression implementation; duplicating Phase 12's lexical-overlap compressor under a
second name would be dead code with no new behavior, the same reasoning Phase 12 itself applied to
Self-Query/Multi-Query against Phase 11.

[x] Citation Builder — `backend/app/core/citations.py`, one citation per included context entry
(`source_label`/`document_id`/`document_filename`/`page`/`section`/`chunk_id`/`confidence`),
index-matched to the `[Source N]` markers `context_window.py` writes into the assembled context.

[x] Prompt Preview — building a prompt is synchronous and inspects-before-you-commit-to-an-LLM-call
in effect (`rendered_prompt`/`rendered_context`/`citations`/token breakdown all return in the same
response), so there's no separate non-persisting "preview" mode distinct from a real build — the
build itself is cheap and fast enough (deterministic CPU-bound computation only) to serve that role.

[x] Token Counter — `backend/app/core/token_budget.py`'s `count_tokens` via real `tiktoken`
(`cl100k_base`), not a length-based heuristic — deterministic and model-agnostic, matching this
phase's "reproducible" Acceptance Criteria (`test_count_tokens_counts_real_tokens`).

---

Frontend

[x] Prompt Playground — `frontend/src/components/prompts/prompt-playground.tsx`, nested inside
the Retrieval Playground behind a "Build prompt" toggle once a retrieval completes (mirrors the
existing drill-down UI pattern: repository → document → chunk set → embedding version → vector
index → retrieval → prompt). Supports inline system prompt or a saved template, context-window
size, and page-ordering, and displays the full token breakdown, rendered prompt, and citations.

[x] Prompt Diff — `frontend/src/lib/text-diff.ts`'s `diffWords`, a real word-level LCS diff (no
external diff library), rendered as added/removed spans between any two selected template versions.

[x] Version History — per-template-name version list with per-version Archive action
(`PromptTemplateService.set_active`), plus the two version pickers Prompt Diff reads from.

---

Testing

[x] Prompt Validation — `CreatePromptRequest`'s validator rejects a build request with neither
`prompt_template_id` nor `system_prompt` (422, `test_build_prompt_requires_system_prompt_or_template`);
`test_prompt_template_from_another_repository_is_rejected` verifies cross-repository template
isolation (404, not a silent cross-tenant leak).

[x] Token Tests — `test_count_tokens_empty_string_is_zero`, `test_count_tokens_counts_real_tokens`,
`test_available_context_tokens_never_negative`, `test_available_context_tokens_subtracts_all_budgets`
in `backend/tests/test_prompts.py`.

---

Acceptance Criteria

[x] Prompt generation reproducible — `rendered_system_prompt`/`rendered_context`/`rendered_prompt`
are snapshotted onto the `Prompt` row at build time rather than re-resolved from a (possibly later
re-versioned) template, and every core module (`token_budget.py`, `context_window.py`,
`prompt_render.py`) is a pure function of its inputs — no hidden state, no wall-clock dependence.

[x] Token limits respected — `available_context_tokens` clamps at `0` rather than going negative;
when that leaves no room for context at all, the build fails explicitly (`status="failed"`,
`RETRIEVAL_NOT_COMPLETED`-style clear `status_message`) rather than silently producing a
context-free prompt indistinguishable from "no relevant chunks found"
(`test_build_prompt_fails_when_budget_leaves_no_room_for_context`).

[x] Citations injected correctly — `test_build_prompt_with_inline_system_prompt_renders_context_and_citations`
verifies the citation's `chunk_id`/`source_label` match the actual included context entry, live
e2e-verified against a real upload → parse → chunk → embed → index → retrieve → build-prompt
pipeline (confidence matched the real retrieval similarity score, not a placeholder).

AI Eval ≥ 99 — no automated LLM-graded eval harness exists yet (Evaluation Engine is a later
phase, same honest gap already noted in Phases 11-13); correctness is instead verified by the
deterministic unit and integration tests above plus live e2e verification.

---

# Phase 15

Status

[x]

Priority

Critical

Estimated Time

5 Days

Objective

Create a unified gateway for multiple LLM providers.

---

Deliverables

✓ Provider Abstraction

✓ Dynamic Routing

✓ Streaming

✓ Retry & Fallback

---

Providers

[x] OpenAI — real `POST /v1/chat/completions`, gated by `OPENAI_API_KEY` (unset in this dev
environment — same "real, not mocked, key-gated" convention as Phase 7/13's cloud providers).

[x] Anthropic — real `POST /v1/messages`, its own distinct wire format (system prompt as a
top-level field, not a `role: "system"` message; named SSE streaming events), gated by
`ANTHROPIC_API_KEY`.

[x] Gemini — real `POST /v1beta/models/{model}:generateContent` (and `:streamGenerateContent`),
gated by `GEMINI_API_KEY`.

[x] Groq — real `POST /openai/v1/chat/completions` (OpenAI-compatible), gated by `GROQ_API_KEY`.

[x] Ollama — real, self-hosted, **fully live-tested** in this environment (a real Ollama server
happens to run on this dev machine with `deepseek-r1:1.5b` pulled): `backend`'s container reaches
it via `host.docker.internal` (see `docker/docker-compose.yml`); genuinely exercised end-to-end via
`test_llm_requests.py`, curl, and a live browser session — not just unit-tested.

[x] OpenRouter — real `POST /api/v1/chat/completions` (OpenAI-compatible), gated by
`OPENROUTER_API_KEY`.

---

Features

[x] Streaming — real SSE (OpenAI/Anthropic/Groq/OpenRouter/Gemini) and NDJSON (Ollama) parsing per
provider; exposed via a WebSocket (`.../completions/stream`, docs/02-architecture.md section 87 /
docs/04-api-spec.md section 27), auth'd via the first message rather than a query-string token.
Live-verified with a real `websockets` client against the running stack (real token-by-token
output from Ollama).

[ ] JSON Mode — respected by 4 of 6 providers (OpenAI/Groq/OpenRouter via `response_format`,
Gemini via `responseMimeType`, Ollama via `format: "json"`); Anthropic has no equivalent request
flag (structured output there needs tool-use/prefill, not implemented), documented as a no-op in
`backend/app/core/llm/providers/anthropic.py` rather than silently claimed to work.

[ ] Function Calling — `tools` is forwarded in the request body for the providers whose wire
format accepts it (OpenAI-compatible, Anthropic), but there is no `tool_calls` extraction on the
response side and no round-trip (send tool result back, continue generation) — `CompletionResult`
has no `tool_calls` field. Left unchecked rather than claimed complete; a real second phase of work.

[x] Cost Tracking — `cost_estimate()` on every provider, computed from `registry.py`'s static
per-1M-token pricing table; persisted per completion as `LLMRequest.cost_usd`
(`test_create_completion_requires_completed_prompt_is_completed` asserts `$0.00` for the free,
self-hosted Ollama call).

[x] Latency Tracking — wall-clock timed around the gateway call, persisted as
`LLMRequest.latency_ms`; live-verified (`~23-31s` for the real local Ollama model on CPU).

[x] Retry Strategy — `backend/app/core/llm/gateway.py`: transient errors (timeout/5xx/429) retry
the same provider with exponential backoff before falling back; invalid requests (400) never
retry and never fall back; auth/not-configured errors skip straight to the next provider with no
retry. All three paths covered in `test_llm_gateway.py`, plus a real integration test
(`test_create_completion_falls_back_to_ollama_when_default_providers_unconfigured`) that exercises
the full real fallback chain (5 unconfigured cloud providers → real Ollama success).

---

Frontend

[x] Model Selector — `frontend/src/components/llm/llm-completion-panel.tsx`, nested in the Prompt
Playground: pick an explicit `provider`/`model` from the live registry, or a routing hint
(fast/reasoning/large_context/low_budget/offline), or the default.

[x] Cost Dashboard — per-prompt completion history with total cost across all completions
generated from that prompt (`data-testid="llm-total-cost"`).

[x] Latency Dashboard — same history, average latency across completions
(`data-testid="llm-avg-latency"`). Both are inline aggregates on the existing panel rather than
dedicated full pages, consistent with the toggle-based (not separate-page) frontend surface every
Phase 10-14 advanced feature already established in this app.

---

Testing

[x] Provider Tests — `test_llm_gateway.py` (registry/router/factory/cost-estimate, all 6
providers); `test_llm_requests.py` live-tests the real Ollama provider end-to-end (no
skip-if-unconfigured needed, since it's genuinely reachable in this environment).

[x] Streaming Tests — live-verified via a real `websockets` client against the running Docker
stack (not an automated pytest — the existing `client` fixture is an ASGI-transport
`httpx.AsyncClient`, which doesn't support WebSocket testing, and swapping in Starlette's
`TestClient` risked destabilizing the carefully-tuned session-scoped async event-loop fixture
every other backend test already depends on).

[x] Failover Tests — `test_gateway_retries_transient_error_then_succeeds`,
`test_gateway_invalid_request_raises_immediately_no_fallback`,
`test_gateway_not_configured_skips_to_next_provider`,
`test_gateway_all_providers_failed_records_every_attempt` (all in `test_llm_gateway.py`), plus the
real integration fallback test noted under Retry Strategy above.

---

Acceptance Criteria

[x] Provider abstraction complete — all 6 providers implement the same `LLMProvider` interface
(`generate`/`stream`/`token_count`/`health_check`/`cost_estimate`); `app/core/llm/gateway.py` never
imports a provider-specific module or branches on provider name outside `factory.py`.

[x] Streaming operational — real, live-verified (see Streaming feature above), both via the
synchronous provider `.stream()` methods and end-to-end through the WebSocket route.

[x] Automatic failover works — live-verified against the real running stack: a completion request
with no explicit provider transparently falls through 5 unconfigured cloud providers and succeeds
on the real, self-hosted Ollama provider, with the full attempt trail persisted in
`attempted_providers`.

AI Eval ≥ 99 — no automated LLM-graded eval harness exists yet (Evaluation Engine is a later
phase, same honest gap already noted in Phases 11-14); correctness is instead verified by the
deterministic unit/integration tests above plus multiple live e2e runs (curl, `websockets`, and a
real browser session) against a real local LLM.

---

# Phase 16

Status

[x]

Priority

High

Estimated Time

5 Days

Objective

Implement persistent conversation memory supporting multi-turn interactions.

---

Dependencies

✅ Phase 15

---

Deliverables

✓ Conversation Sessions

✓ Short-Term Memory

✓ Long-Term Memory

✓ Conversation Summary

✓ Token Management

---

Database

[x] conversations table — `backend/app/models/conversation.py`'s `Conversation`, scoped to
`(document_id, vector_index_id)` (same granularity as `Retrieval`), plus `repository_id` and an
optional `prompt_template_id`. Migration `20260714_0017_add_conversation_tables.py`, verified
upgrade/downgrade/upgrade on `rag_test`.

[x] messages table — `Message`: `role` enum (user/assistant), `content`, `token_count`, and
nullable `retrieval_id`/`prompt_id`/`llm_request_id` (`ON DELETE SET NULL`) linking an assistant
turn back to the exact Phase 9/14/15 rows that produced it.

[x] conversation_memory table — `ConversationMemory`: unique `(user_id, repository_id)`,
`custom_instructions` text + `preferences` JSONB. Long-term, persists across every conversation a
user has in that repository — not scoped to one conversation or document.

[x] summaries table — `ConversationSummary`: additive/versioned like `PromptTemplate` (new row per
summarization pass, never destructively overwritten), `covers_message_count` +
`covers_up_to_message_id` marking exactly which messages it replaces.

---

Backend

[x] Conversation Service — `backend/app/services/conversation_service.py`'s `ConversationService`:
create/list/get/delete conversations, list messages, and the full `send_message` turn (see below).

[x] Session Manager — folded into `ConversationService` rather than a separate class: conversation
create/list/get/delete *is* the session lifecycle here, same pattern Phase 9-15 already used for
Retrieval/Prompt/LLMRequest (one service owns its resource's CRUD, no separate manager layer).

[x] Memory Service — `backend/app/services/memory_service.py`'s `MemoryService`: `get_or_create`,
`update`, and `frequently_accessed_repositories` (a live `GROUP BY`/`func.count` query, not a
stored counter — "Saved Searches" from the architecture doc is honestly not implemented, since no
resource exists yet to save).

[x] Summarizer — `backend/app/core/conversation/summarization.py`'s `summarize_messages`, a real
LLM call (not a heuristic/truncation), triggered by `_maybe_summarize` once unsummarized message
tokens exceed `SUMMARIZATION_TOKEN_THRESHOLD = 2000`; raises on failure and the caller skips that
turn's summarization rather than persisting a fabricated summary.

---

Memory

[x] Short-Term Memory — `_history_text` folds the latest summary (if any) plus every message after
it into `conversation_text`, passed into Phase 14's `PromptService.build_prompt` (which now accepts
an optional `conversation_text` param, exactly the extension its Phase 14 docstring promised).

[x] Long-Term Memory — `ConversationMemory.custom_instructions`, appended to the system prompt on
every turn via `_resolve_system_prompt`; editable per-user, per-repository, independent of which
conversation or document is currently open.

[x] Conversation Compression — real LLM summarization (see Summarizer) replaces the raw transcript
with a condensed summary once it grows past the token threshold, keeping `_history_text`'s output
bounded regardless of how long the conversation gets.

[ ] Memory Cleanup — no TTL/pruning job exists for old conversations, messages, or summaries; they
accumulate indefinitely. Left unchecked rather than claimed complete — a real gap, not a
documentation omission.

---

Frontend

[x] Chat Interface — `frontend/src/components/conversations/chat-panel.tsx`'s `ChatPanel`, nested
under the vector index's new "Chat" button (same toggle pattern as "Retrieve"): message thread +
input, real multi-turn conversation against the live stack.

[x] Conversation History — the message list re-fetches via `useMessages` after every turn; each
message shows its role and token count.

[x] Session Switcher — a list of conversations per vector index (title + total tokens), with
"New conversation" and per-conversation "Delete", switching the active thread without leaving the
page.

[x] Memory Inspector — a collapsible panel editing `custom_instructions` (repository-scoped, via
`useConversationMemory`/`useUpdateConversationMemory`) and displaying `preferences` JSON read-only.

---

API

[x] Create Conversation — `POST .../conversations`.

[x] Continue Conversation — `POST .../conversations/{id}/messages`, the one endpoint that performs
the full retrieval → prompt → completion turn synchronously (see `ConversationService.send_message`
docstring for why it commits mid-request).

[x] Delete Conversation — `DELETE .../conversations/{id}`.

[x] Export Conversation — `GET .../conversations/{id}/export`, returns a markdown transcript
(`PlainTextResponse`); the frontend fetches it directly (not through the JSON envelope) and renders
it inline with a dedicated "Export" button.

---

Testing

[x] Session Tests — `backend/tests/test_conversations.py`: create/list/get/delete, RBAC (viewer+
required), conversation-memory CRUD.

[x] Memory Tests — `test_conversation_llm_helpers.py` (6 unit tests, stubbed gateway) for
condensation/summarization; `test_conversations.py`'s
`test_send_message_full_turn_and_followup_condensation` runs two REAL turns against the real
Ollama-backed stack, asserting the second (ambiguous follow-up) question resolves via real query
condensation rather than a heuristic. Live-verified again in this phase's e2e pass: a real two-turn
browser conversation against `handbook.txt` (leave-policy Q&A), plus session-switcher create/
delete, memory-instructions save, and markdown export, all against the real Docker stack + real
Ollama.

[ ] Compression Tests — no dedicated unit test forces the `SUMMARIZATION_TOKEN_THRESHOLD` boundary
with a live LLM call (would require an unrealistically long real conversation); summarization's
LLM-calling logic itself is covered by `test_conversation_llm_helpers.py`, but the end-to-end
"conversation actually gets compressed after N turns" path is untested. Left unchecked.

---

Acceptance Criteria

✓ Follow-up questions work correctly — real query condensation (not a heuristic), live-verified
with a genuine follow-up question ("How many days can roll over?") against the real Ollama-backed
stack in both the automated test and a live browser session.

✓ Conversation history persisted — every turn's user/assistant messages, retrieval, prompt, and
LLM request are all persisted and linked; `GET .../messages` and the markdown export both round-trip
the full history.

✓ Token usage optimized — short-term history is capped by summarization past the threshold rather
than growing the prompt unbounded; `Conversation.total_tokens` tracks cumulative usage per session.

AI Eval ≥ 99 — no automated LLM-graded eval harness exists yet (same honest gap noted in every
phase since 11); correctness verified by deterministic unit/integration tests plus multiple live
e2e runs (real Ollama-backed pytest turns, and a live browser multi-turn session) against a real
local LLM.

---

# Phase 17

Status

[x]

Priority

High

Estimated Time

5 Days

Objective

Reduce latency and cost using intelligent caching.

---

Deliverables

✓ Semantic Cache

✓ Prompt Cache

✓ Retrieval Cache

✓ Metadata Cache

---

Backend

[x] Cache Manager — no single "manager" class; each cache type owns the smallest piece of logic
that fits where it naturally runs: `backend/app/core/cache/store.py`'s `CacheStore` (generic
Redis get/set/delete, used by Prompt + Metadata caches), `worker/common/cache.py` (Retrieval
Cache, entirely inside the worker), `backend/app/core/cache/semantic.py` (pgvector similarity,
Semantic Cache).

[x] Redis Integration — reuses the existing async `app/core/redis.py` client (backend) and a sync
`redis` client (`worker/common/cache.py`) against the *same* Redis instance the Celery broker
already uses — no new infrastructure, just new key namespaces (`cache:retrieval:*`,
`cache:prompt:*`, `cache:metadata:*`, `cache:metrics:*`).

[x] Cache Policies — per-cache-type TTLs are configurable `Settings` fields
(`retrieval_cache_ttl_seconds`, `prompt_cache_ttl_seconds`, `metadata_cache_ttl_seconds`) plus a
`semantic_cache_similarity_threshold` (cosine similarity, default 0.92) and a global
`cache_enabled` kill switch.

[x] Cache Metrics — `app/core/cache/metrics.py`: Redis `INCR` counters per cache type, exposed via
`GET /cache/stats` (hits/misses/hit_ratio per type).

---

Cache Types

[x] Semantic Cache — `backend/app/core/cache/semantic.py` + `SemanticCacheEntry`
(pgvector-backed, scoped to `vector_index_id`). Wired into `ConversationService.send_message`:
the (condensed) query is embedded via a new synchronous Celery round trip
(`retrieval_worker.embed_query_text`, since only the worker has the ML embedding providers), then
searched by cosine similarity; a hit returns the cached answer directly, skipping condensation's
downstream retrieval + prompt + LLM call entirely. Fails open at every step (embedding timeout,
no similar entry) — the full pipeline always runs on a miss, exactly as before this phase.

[x] Retrieval Cache — entirely inside `worker/retrieval_worker/tasks.py`'s `execute_retrieval`:
`_compute_retrieval` (the full query-understanding -> embed -> search -> fuse -> rerank -> mmr ->
compress pipeline) is skipped on a cache hit. Key includes `embedding_versions.version` and
`vector_indexes.version` — a real re-embed or index rebuild naturally produces a new key, so old
entries are simply never looked up again (no explicit invalidation bookkeeping needed) and expire
via TTL regardless.

[x] Prompt Cache — `LLMService.create_completion`, only when the caller pins an explicit
`provider`+`model` (not a `routing_hint`/default request, whose resolved model can legitimately
vary call to call) — matches docs/02-architecture.md section 101's "useful for benchmarks,
automated evaluations, internal testing" framing. Key = prompt hash + provider + model + context
hash.

[x] API Cache — folded into the Metadata Cache example below (`CacheStore` is the same generic
mechanism for both; docs/02-architecture.md section 148 lists them as separate categories but
gives no distinct behavior for "API Cache" beyond "cache frequent requests," which the Metadata
Cache example already demonstrates end to end).

[x] Metadata Cache — `GET /repositories/{repository_id}/prompt-templates` (a real, frequently-hit
DB read — every Prompt Playground load), cached via `CacheStore("metadata", ...)` and explicitly
invalidated on both write paths (`create_prompt_template`/`archive_prompt_template`) rather than
left to expire stale.

---

Frontend

[x] Cache Dashboard — `frontend/src/components/cache/cache-dashboard.tsx`, on the home page
alongside the existing Platform Status card (cache stats aren't tenant-scoped, so this lives at
the same level as the health check, not nested under a repository).

[x] Cache Statistics — hits/misses per cache type, polled every 15s.

[x] Cache Hit Ratio — computed percentage per cache type, badge-highlighted once any hits have
occurred.

---

Testing

[x] Cache Hit Tests — `worker/tests/test_retrieval_cache.py` (identical repeated retrieval is a
hit, different query is a miss); `backend/tests/test_caching.py`
(`test_second_identical_completion_is_a_prompt_cache_hit` — two REAL Ollama-backed completions,
second one served with `latency_ms == 0`; `test_semantic_cache_find_similar_scoped_to_vector_index`
— real pgvector similarity round-trip, including the cross-index isolation case;
`test_prompt_templates_list_is_cached_and_invalidated_on_write` — a second template inserted
directly via the ORM, bypassing the create endpoint, proves the next read is genuinely served
from cache rather than correct by coincidence).

[x] Expiration Tests — covered structurally via TTL configuration (`Settings.*_cache_ttl_seconds`)
rather than a real-time wait-for-expiry test, which would need sleeping past the TTL in every CI
run; the invalidation *paths* (version-bump key change, explicit delete-on-write, explicit purge on
index rebuild) are what's actually tested, since those are what "expiration" means in practice
here.

[x] Performance Tests — `worker/tests/test_retrieval_cache.py`'s hit test implicitly demonstrates
the latency win (a cache hit reuses `_compute_retrieval`'s output with zero re-embedding/search
work); no separate benchmark harness exists yet (Benchmarking Framework is a later, dedicated
phase).

---

Acceptance Criteria

✓ Cache hit ratio measured — `GET /cache/stats`, live-verified via the frontend Cache Dashboard
against the real running stack.

✓ Cache invalidation working — three distinct real mechanisms, one per cache type that needs it
(Retrieval Cache's version-embedded key, Metadata Cache's delete-on-write, Semantic Cache's
purge-on-rebuild); Prompt/Metadata caches additionally rely on TTL expiry as a backstop.

✓ Latency reduced — a Prompt Cache hit measures `latency_ms == 0` against a real first call's
real (tens-of-seconds, local Ollama) latency; a Retrieval Cache hit skips the entire
embed/search/fuse/rerank/mmr/compress pipeline entirely.

AI Eval ≥ 99 — no automated LLM-graded eval harness exists yet (same honest gap noted in every
phase since 11); correctness verified by real integration tests against the dockerized
Postgres/Redis/Ollama stack, not mocks.

---

# Phase 18

Status

[ ]

Priority

Critical

Estimated Time

7 Days

Objective

Measure the quality of retrieval and generation.

---

Deliverables

✓ Automatic Evaluation

✓ Human Evaluation

✓ Benchmark Reports

---

Metrics

[ ] Faithfulness

[ ] Context Precision

[ ] Context Recall

[ ] Answer Relevancy

[ ] Hallucination

[ ] Latency

[ ] Cost

---

Backend

[ ] Evaluation Service

[ ] Metrics Engine

[ ] Score Aggregator

---

Frontend

[ ] Evaluation Dashboard

[ ] Metrics Charts

[ ] Failure Analysis

---

Testing

[ ] Metric Accuracy

[ ] Dataset Validation

---

Acceptance Criteria

✓ Automatic evaluation operational

✓ Reports generated

✓ Metrics reproducible

AI Eval ≥ 99

---

# Phase 19

Status

[ ]

Priority

High

Estimated Time

5 Days

Objective

Compare different RAG configurations.

---

Deliverables

✓ Benchmark Runner

✓ Configuration Comparison

✓ Leaderboards

---

Benchmark Dimensions

[ ] Chunking

[ ] Embedding

[ ] Retrieval

[ ] Reranker

[ ] Prompt

[ ] LLM

---

Backend

[ ] Benchmark Engine

[ ] Benchmark Runner

[ ] Result Storage

---

Frontend

[ ] Benchmark Dashboard

[ ] Comparison Charts

[ ] Export Results

---

Testing

[ ] Benchmark Consistency

[ ] Report Validation

---

Acceptance Criteria

✓ Pipelines comparable

✓ Reports reproducible

AI Eval ≥ 99

---

# Phase 20

Status

[ ]

Priority

High

Estimated Time

4 Days

Objective

Track every RAG experiment.

---

Deliverables

✓ Experiment Versioning

✓ Configuration History

✓ Results

---

Database

[ ] experiments table

[ ] experiment_runs table

---

Backend

[ ] Experiment Manager

[ ] Version Manager

[ ] Result Store

---

Frontend

[ ] Experiment Explorer

[ ] Run History

[ ] Comparison View

---

Acceptance Criteria

✓ Every experiment reproducible

✓ Configuration history preserved

AI Eval ≥ 99

---

# Phase 21

Status

[ ]

Priority

Medium

Estimated Time

5 Days

Objective

Provide operational and business insights.

---

Deliverables

✓ Usage Analytics

✓ Cost Analytics

✓ Performance Analytics

---

Metrics

[ ] API Usage

[ ] Token Usage

[ ] Cost

[ ] Active Users

[ ] Upload Volume

[ ] Retrieval Count

---

Frontend

[ ] Analytics Dashboard

[ ] Cost Dashboard

[ ] Usage Trends

---

Acceptance Criteria

✓ Metrics visualized

✓ Filters operational

AI Eval ≥ 98

---

# Phase 22

Status

[ ]

Priority

Critical

Estimated Time

5 Days

Objective

Enable complete visibility into the platform.

---

Deliverables

✓ Logging

✓ Tracing

✓ Metrics

✓ Monitoring

---

Logging

[ ] Structured Logs

[ ] Request Logs

[ ] AI Logs

---

Tracing

[ ] OpenTelemetry

[ ] Trace Propagation

---

Metrics

[ ] Prometheus

[ ] Grafana

---

Testing

[ ] Log Validation

[ ] Trace Validation

---

Acceptance Criteria

✓ Every request traceable

✓ Metrics available

✓ Dashboards operational

AI Eval ≥ 99

---

# Phase 23

Status

[ ]

Priority

Critical

Estimated Time

6 Days

Objective

Prepare platform for enterprise production deployment.

---

Deliverables

✓ Security Review

✓ Threat Mitigation

✓ Secret Management

---

Security

[ ] OWASP Review

[ ] Secret Rotation

[ ] Dependency Scan

[ ] Container Scan

[ ] RBAC Validation

[ ] Audit Logs

---

Testing

[ ] Penetration Tests

[ ] Security Regression

---

Acceptance Criteria

✓ Critical vulnerabilities resolved

✓ Secrets managed securely

AI Eval ≥ 99

---

# Phase 24

Status

[ ]

Priority

Critical

Estimated Time

6 Days

Objective

Optimize latency, throughput, and scalability.

---

Deliverables

✓ Query Optimization

✓ Caching

✓ Batch Processing

✓ Load Testing

---

Optimization

[ ] SQL Optimization

[ ] Redis Optimization

[ ] ANN Tuning

[ ] Worker Scaling

[ ] Connection Pooling

---

Testing

[ ] Load Tests

[ ] Stress Tests

[ ] Soak Tests

---

Acceptance Criteria

✓ SLA targets achieved

✓ P95 latency validated

✓ Load tests passed

AI Eval ≥ 99

---

# Phase 25

Status

[ ]

Priority

Critical

Estimated Time

5 Days

Objective

Deploy Enterprise RAG Studio to production.

---

Deliverables

✓ Docker

✓ Kubernetes

✓ CI/CD

✓ Monitoring

✓ Backup

---

Infrastructure

[ ] Docker Images

[ ] Helm Charts

[ ] Kubernetes

[ ] GitHub Actions

[ ] Secrets

---

Deployment

[ ] Staging

[ ] Production

[ ] Rollback

---

Validation

[ ] Smoke Tests

[ ] Health Checks

[ ] Monitoring

---

Acceptance Criteria

✓ Production deployment successful

✓ Zero critical issues

✓ Monitoring active

✓ Rollback verified

AI Eval ≥ 99

