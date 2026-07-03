# 06-rule.md

# Enterprise RAG Studio Engineering Rules

Version: 2.0

Status: Mandatory

---

# Purpose

This document defines the mandatory engineering rules that must be followed throughout the project.

These rules are non-negotiable.

If implementation conflicts with these rules, implementation must be corrected.

---

# Rule Priority

If multiple documents conflict, follow this priority.

1. master_prompt.md
2. architecture.md
3. database.md
4. api-spec.md
5. rule.md
6. task.md

---

# General Engineering Rules

* Always implement production-ready code.
* Never implement demo-quality shortcuts.
* Never duplicate business logic.
* Keep modules loosely coupled.
* Keep components highly cohesive.
* Every feature must be testable.
* Every feature must be documented.

---

# Architecture Rules

Must Follow

* Layered Architecture
* SOLID Principles
* Dependency Injection
* Repository Pattern
* Service Layer Pattern
* Domain Driven Design (where applicable)

Forbidden

* Business logic inside Controllers
* Database access from UI
* Circular dependencies
* God classes
* Utility classes containing unrelated logic

---

# Backend Rules

Every backend module must follow:

```
Controller

↓

Service

↓

Repository

↓

Database
```

Controllers

Allowed

* Authentication
* Validation
* Calling services
* Returning responses

Forbidden

* SQL queries
* Business logic
* External API orchestration
* AI pipeline execution

Services

Allowed

* Business rules
* Transactions
* Orchestration
* External integrations

Repositories

Allowed

* CRUD
* Optimized queries
* Pagination
* Filtering

Forbidden

* Business validation
* HTTP requests
* AI logic

---

# Frontend Rules

Every page must include:

* Loading state
* Error state
* Empty state
* Success state

Components

* Small
* Reusable
* Stateless where possible

Business logic belongs in:

* Hooks
* Services
* State management

Never inside presentation components.

---

# Database Rules

Every table must contain:

* UUID Primary Key
* created_at
* updated_at
* created_by
* updated_by
* Soft Delete (where applicable)

Migrations

* Version controlled
* Reversible
* Reviewed
* Tested

Indexes

Required on

* Foreign keys
* Search fields
* Sort fields
* Frequently filtered columns

Never

* Store large binary objects in PostgreSQL
* Perform N+1 queries
* Skip indexes on large tables

---

# API Rules

REST Standards

Use nouns.

Examples

```
/api/v1/projects
/api/v1/documents
/api/v1/repositories
```

Every endpoint must include

* Authentication
* Authorization
* Validation
* Logging
* Error handling
* OpenAPI documentation

---

# AI Pipeline Rules

Every pipeline stage must expose

* Input
* Output
* Duration
* Cost
* Version
* Metrics

Pipeline

```
Upload

↓

Parser

↓

Chunking

↓

Embedding

↓

Retrieval

↓

Reranking

↓

Prompt Builder

↓

LLM

↓

Evaluation
```

No hidden processing.

---

# Prompt Rules

* Prompts must be versioned.
* Prompts must be parameterized.
* Never hardcode prompts inside services.
* Store prompts centrally.

---

# Retrieval Rules

Required

* Hybrid Search
* Metadata Filtering
* Reranking
* Citation Support

Forbidden

* Returning raw Top-K without reranking
* Ignoring metadata filters
* Hallucinating when confidence is low

---

# Security Rules

Mandatory

* JWT validation
* RBAC
* Input validation
* Output validation
* Secret management
* Audit logging
* Rate limiting

Forbidden

* Hardcoded credentials
* Logging secrets
* Returning stack traces
* Trusting client input

---

# Logging Rules

Every request logs

* Request ID
* Trace ID
* User ID
* Organization ID
* Endpoint
* Duration
* Status

Every AI execution logs

* Embedding model
* Retriever
* Reranker
* LLM
* Tokens
* Cost
* Latency

---

# Error Handling Rules

All errors must

* Be categorized
* Be logged
* Include request ID
* Return user-friendly messages

Never expose internal implementation details.

---

# Performance Rules

Targets

API

<200 ms (excluding LLM)

Retrieval

<300 ms

Streaming

First token <1.5 s

Optimization Rules

* Batch expensive operations
* Cache frequently accessed data
* Use asynchronous workers
* Optimize SQL queries
* Monitor token usage

---

# Caching Rules

Use

* Metadata Cache
* Semantic Cache
* Retrieval Cache
* Prompt Cache

Cache invalidation must occur after relevant updates.

---

# Worker Rules

Every worker must be

* Idempotent
* Retryable
* Observable

Failed jobs

* Retry with exponential backoff
* Move to Dead Letter Queue after retry limit

---

# Testing Rules

Every feature requires

* Unit Tests
* Integration Tests
* API Tests

Critical flows require

* End-to-End Tests

Coverage Targets

Backend ≥ 90%

Critical Logic ≥ 95%

---

# Documentation Rules

Whenever implementation changes

Review and update

* architecture.md
* database.md
* api-spec.md
* task.md
* rule.md

Documentation must never lag behind implementation.

---

# Git Rules

Branch Names

```
feature/*
bugfix/*
hotfix/*
release/*
```

Commit Messages

```
feat(...)
fix(...)
refactor(...)
docs(...)
test(...)
```

---

# Code Review Rules

Reject code if

* Tests fail
* Documentation missing
* Architecture violated
* Security issue exists
* Duplicate logic exists
* Large unrelated changes included

---

# AI Evaluation Rules

Before marking any task complete

Verify

* Architecture compliance
* Security
* Maintainability
* Performance
* Documentation
* Testing
* Observability

Target

Overall AI Evaluation Score ≥ 99

If score is below target

Refactor

Retest

Re-evaluate

Only then mark complete.

---

# Forbidden Practices

Never

* Hardcode secrets
* Skip validation
* Ignore failed tests
* Merge incomplete work
* Bypass architecture
* Leave TODOs without tracking
* Ignore documentation updates
* Duplicate business logic
* Use magic numbers without explanation
* Suppress exceptions silently

---

# Definition of Engineering Excellence

The implementation is considered complete only when it is:

* Correct
* Secure
* Performant
* Scalable
* Observable
* Testable
* Maintainable
* Well documented
* Production ready

Anything less is considered incomplete.
