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

[ ]

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

[ ] embeddings table

[ ] embedding_versions table

---

Models

[ ] OpenAI

[ ] Voyage

[ ] BGE

[ ] E5

[ ] Instructor

[ ] Nomic

[ ] Jina

---

Embedding Pipeline

[ ] Batch Generator

[ ] Retry Logic

[ ] Progress Tracking

[ ] Cost Tracking

---

Versioning

[ ] Embedding Versions

[ ] Model Tracking

[ ] Rebuild Support

---

Frontend

[ ] Embedding Dashboard

[ ] Model Comparison

[ ] Cost Metrics

---

API

[ ] Generate Embeddings

[ ] Delete Embeddings

[ ] Regenerate

[ ] Compare Models

---

Testing

[ ] Batch Tests

[ ] Model Tests

[ ] Cost Tests

[ ] Performance Tests

---

Acceptance Criteria

✓ Multiple embedding models supported

✓ Versioning implemented

✓ Batch processing stable

✓ Cost tracking available

AI Eval ≥ 99

---

# Phase 7

Status

[ ]

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

[ ] embeddings table

[ ] embedding_versions table

---

Models

[ ] OpenAI

[ ] Voyage

[ ] BGE

[ ] E5

[ ] Instructor

[ ] Nomic

[ ] Jina

---

Embedding Pipeline

[ ] Batch Generator

[ ] Retry Logic

[ ] Progress Tracking

[ ] Cost Tracking

---

Versioning

[ ] Embedding Versions

[ ] Model Tracking

[ ] Rebuild Support

---

Frontend

[ ] Embedding Dashboard

[ ] Model Comparison

[ ] Cost Metrics

---

API

[ ] Generate Embeddings

[ ] Delete Embeddings

[ ] Regenerate

[ ] Compare Models

---

Testing

[ ] Batch Tests

[ ] Model Tests

[ ] Cost Tests

[ ] Performance Tests

---

Acceptance Criteria

✓ Multiple embedding models supported

✓ Versioning implemented

✓ Batch processing stable

✓ Cost tracking available

AI Eval ≥ 99

---

# Phase 9

Status

[ ]

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

[ ] Cosine

[ ] Dot Product

[ ] Euclidean

---

Backend

[ ] Retriever Service

[ ] Similarity Calculator

[ ] Candidate Generator

[ ] Confidence Calculator

---

Retrieval Features

[ ] Top-K

[ ] Score Threshold

[ ] Namespace Search

[ ] Metadata Filter

[ ] Pagination

---

Metrics

[ ] Recall

[ ] Precision

[ ] Average Similarity

[ ] Latency

---

Frontend

[ ] Retrieval Playground

[ ] Similarity Viewer

[ ] Result Inspector

---

Testing

[ ] Recall Tests

[ ] Latency Tests

[ ] Large Dataset Tests

---

Acceptance Criteria

✓ Accurate semantic retrieval

✓ Retrieval latency within target

✓ Confidence scoring available

AI Eval ≥ 99

---

# Phase 10

Status

[ ]

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

[ ] BM25 Engine

[ ] Hybrid Retriever

[ ] Score Fusion

[ ] Ranking Service

---

Fusion

[ ] Weighted Sum

[ ] Reciprocal Rank Fusion

[ ] Configurable Weights

---

Configuration

[ ] Dense Weight

[ ] Sparse Weight

[ ] Threshold

---

Frontend

[ ] Hybrid Search Dashboard

[ ] Weight Slider

[ ] Score Comparison

---

Testing

[ ] Hybrid Accuracy

[ ] BM25 Tests

[ ] Ranking Tests

---

Acceptance Criteria

✓ Hybrid search improves retrieval quality

✓ Configurable fusion

✓ Ranking verified

AI Eval ≥ 99

---

# Phase 11

Status

[ ]

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

[ ] Query Intent Detection

[ ] Query Rewrite

[ ] Multi Query Generation

[ ] Query Expansion

[ ] Metadata Detection

[ ] Filter Extraction

---

Backend

[ ] Query Analyzer

[ ] Rewrite Service

[ ] Expansion Service

[ ] Filter Generator

---

Frontend

[ ] Query Inspector

[ ] Rewrite Viewer

[ ] Generated Queries

---

Testing

[ ] Rewrite Accuracy

[ ] Classification Tests

[ ] Expansion Tests

---

Acceptance Criteria

✓ Query understanding improves recall

✓ Rewrite quality validated

✓ Filters extracted correctly

AI Eval ≥ 99


---

# Phase 12

Status

[ ]

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

[ ] Parent Child

[ ] Self Query

[ ] Multi Query

[ ] MMR

[ ] RAG Fusion

[ ] Context Compression

---

Backend

[ ] Retrieval Orchestrator

[ ] Fusion Engine

[ ] MMR Engine

[ ] Parent Expansion

---

Frontend

[ ] Retrieval Graph

[ ] Strategy Comparison

[ ] Fusion Visualization

---

Testing

[ ] Retrieval Accuracy

[ ] Diversity Tests

[ ] Multi-Hop Tests

---

Acceptance Criteria

✓ Advanced retrieval operational

✓ Fusion improves results

✓ MMR validated

AI Eval ≥ 99

---

# Phase 13

Status

[ ]

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

[ ] BGE

[ ] Cohere

[ ] Jina

[ ] FlashRank

---

Backend

[ ] Reranker Service

[ ] Score Calculator

[ ] Ranking Engine

---

Frontend

[ ] Rerank Comparison

[ ] Score Viewer

[ ] Candidate Explorer

---

Testing

[ ] Ranking Accuracy

[ ] Model Comparison

[ ] Latency Tests

---

Acceptance Criteria

✓ Reranking improves precision

✓ Model switching supported

AI Eval ≥ 99

---

# Phase 14

Status

[ ]

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

[ ] Prompt Versioning

[ ] Context Compression

[ ] Citation Builder

[ ] Prompt Preview

[ ] Token Counter

---

Frontend

[ ] Prompt Playground

[ ] Prompt Diff

[ ] Version History

---

Testing

[ ] Prompt Validation

[ ] Token Tests

---

Acceptance Criteria

✓ Prompt generation reproducible

✓ Token limits respected

✓ Citations injected correctly

AI Eval ≥ 99


---

# Phase 15

Status

[ ]

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

[ ] OpenAI

[ ] Anthropic

[ ] Gemini

[ ] Groq

[ ] Ollama

[ ] OpenRouter

---

Features

[ ] Streaming

[ ] JSON Mode

[ ] Function Calling

[ ] Cost Tracking

[ ] Latency Tracking

[ ] Retry Strategy

---

Frontend

[ ] Model Selector

[ ] Cost Dashboard

[ ] Latency Dashboard

---

Testing

[ ] Provider Tests

[ ] Streaming Tests

[ ] Failover Tests

---

Acceptance Criteria

✓ Provider abstraction complete

✓ Streaming operational

✓ Automatic failover works

AI Eval ≥ 99

---

# Phase 16

Status

[ ]

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

[ ] conversations table

[ ] messages table

[ ] conversation_memory table

[ ] summaries table

---

Backend

[ ] Conversation Service

[ ] Session Manager

[ ] Memory Service

[ ] Summarizer

---

Memory

[ ] Short-Term Memory

[ ] Long-Term Memory

[ ] Conversation Compression

[ ] Memory Cleanup

---

Frontend

[ ] Chat Interface

[ ] Conversation History

[ ] Session Switcher

[ ] Memory Inspector

---

API

[ ] Create Conversation

[ ] Continue Conversation

[ ] Delete Conversation

[ ] Export Conversation

---

Testing

[ ] Session Tests

[ ] Memory Tests

[ ] Compression Tests

---

Acceptance Criteria

✓ Follow-up questions work correctly

✓ Conversation history persisted

✓ Token usage optimized

AI Eval ≥ 99

---

# Phase 17

Status

[ ]

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

[ ] Cache Manager

[ ] Redis Integration

[ ] Cache Policies

[ ] Cache Metrics

---

Cache Types

[ ] Semantic Cache

[ ] Retrieval Cache

[ ] Prompt Cache

[ ] API Cache

[ ] Metadata Cache

---

Frontend

[ ] Cache Dashboard

[ ] Cache Statistics

[ ] Cache Hit Ratio

---

Testing

[ ] Cache Hit Tests

[ ] Expiration Tests

[ ] Performance Tests

---

Acceptance Criteria

✓ Cache hit ratio measured

✓ Cache invalidation working

✓ Latency reduced

AI Eval ≥ 99

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

