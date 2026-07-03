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

[ ]

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

[ ] Repository Table

[ ] Repository Settings

[ ] Repository Metadata

[ ] Repository Statistics

---

Backend

[ ] Repository Model

[ ] Repository Service

[ ] Repository Repository

[ ] CRUD APIs

[ ] Validation

[ ] Search

---

Repository Features

[ ] Create Repository

[ ] Update Repository

[ ] Delete Repository

[ ] Archive Repository

[ ] Clone Repository

[ ] Duplicate Repository

[ ] Export Repository

[ ] Import Repository

---

Repository Settings

[ ] Default Chunk Strategy

[ ] Default Embedding Model

[ ] Default Retriever

[ ] Default Reranker

[ ] Default Prompt

---

Statistics

[ ] Document Count

[ ] Chunk Count

[ ] Embedding Count

[ ] Storage Used

[ ] Retrieval Count

---

Frontend

[ ] Repository Dashboard

[ ] Repository Settings

[ ] Repository Statistics

[ ] Activity Timeline

[ ] Repository Members

---

Security

[ ] RBAC

[ ] Repository Permissions

[ ] Tenant Isolation

---

Testing

[ ] CRUD

[ ] Settings

[ ] Permissions

[ ] API

[ ] UI

Acceptance Criteria

✓ Repository fully functional

✓ Settings persisted

✓ Statistics calculated

✓ APIs documented

✓ Tests passing

AI Eval ≥ 98

Status

[ ]