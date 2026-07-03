# 00-index.md

# Enterprise RAG Studio

## Documentation Index

Version: 1.0

Status: Active

---

# Purpose

This document is the entry point for the entire project documentation.

Every developer and AI coding agent must start here before reading any other document.

This file defines:

* Documentation loading order
* Purpose of each document
* Rules for resolving conflicts
* Development workflow
* Project navigation

---

# Documentation Loading Order

Always load documents in the following order.

```
00-index.md

↓

01-project.md

↓

02-architecture.md

↓

03-database.md

↓

04-api-spec.md

↓

05-task.md

↓

06-rule.md

↓

07-master_prompt.md
```

Never skip documents.

Never change this order.

---

# Document Purpose

## 00-index.md

Purpose

Project navigation.

Defines how documentation should be read.

---

## 01-project.md

Purpose

Defines

* Vision
* Business Goals
* Functional Requirements
* Non-functional Requirements
* Product Scope
* Success Criteria

Read this first after the index.

---

## 02-architecture.md

Purpose

Defines the complete technical architecture.

Includes

* System Architecture
* AI Pipeline
* Deployment
* Security
* Scalability
* Infrastructure

This is the primary technical reference.

---

## 03-database.md

Purpose

Defines

* Database Schema
* Relationships
* Constraints
* Indexes
* Versioning
* Partitioning
* Query Strategy

Every database change must follow this document.

---

## 04-api-spec.md

Purpose

Defines

* REST APIs
* Request Models
* Response Models
* Validation
* Error Codes
* Authentication
* WebSocket Events

Every API implementation must follow this specification.

---

## 05-task.md

Purpose

Defines

* Development Phases
* Task Order
* Dependencies
* Acceptance Criteria
* Definition of Done

Implementation must always follow the current phase.

Never skip phases.

---

## 06-rule.md

Purpose

Defines the Engineering Constitution.

Includes

* Coding Standards
* Security Rules
* Testing Rules
* Performance Rules
* Documentation Rules

These rules are mandatory.

---

## 07-master_prompt.md

Purpose

Defines the AI Engineering Operating System.

Includes

* Execution Workflow
* Decision Framework
* Quality Gates
* Self Review
* Release Process

This document controls AI implementation behavior.

---

# Source of Truth

When documents conflict, use the following precedence.

1. User Requirements
2. 07-master_prompt.md
3. 02-architecture.md
4. 03-database.md
5. 04-api-spec.md
6. 06-rule.md
7. 05-task.md
8. 01-project.md

If conflicts cannot be resolved, stop implementation and request clarification.

Never guess.

---

# Development Workflow

Every implementation cycle follows:

```
Read Documentation

↓

Understand Requirements

↓

Review Current Phase

↓

Review Architecture

↓

Review Database

↓

Review API

↓

Implement

↓

Test

↓

Self Review

↓

Update Documentation

↓

Update task.md

↓

Complete
```

---

# Phase Execution Rules

Only work on one phase at a time.

Before starting a phase:

* Verify dependencies are complete.
* Verify previous phase is complete.
* Verify acceptance criteria have been met.

Do not work on future phases.

---

# Documentation Synchronization

Whenever implementation changes, review whether the following documents require updates:

* 02-architecture.md
* 03-database.md
* 04-api-spec.md
* 05-task.md
* 06-rule.md

Documentation must remain synchronized with implementation.

---

# AI Agent Rules

Before writing code:

* Read all required documents.
* Create an implementation plan.
* Identify dependencies.
* Validate assumptions.

During implementation:

* Follow architecture.
* Follow coding rules.
* Write tests.
* Log important operations.
* Keep code modular.

After implementation:

* Run quality checks.
* Update documentation.
* Update task.md.
* Verify Definition of Done.

---

# Repository Structure

```
docs/
│
├── 00-index.md
├── 01-project.md
├── 02-architecture.md
├── 03-database.md
├── 04-api-spec.md
├── 05-task.md
├── 06-rule.md
├── 07-master_prompt.md
├── 08-testing.md
├── 09-evaluation.md
├── 10-observability.md
├── 11-deployment.md
├── 12-security.md
├── 13-roadmap.md
├── 14-benchmark.md
├── 15-adr.md
└── README.md
```

---

# Quality Gates

Before marking any task complete, verify:

* Architecture followed
* Database updated (if required)
* API documented
* Tests passing
* Documentation updated
* AI evaluation target achieved

Target AI Evaluation Score:

* Overall ≥ 99
* Security ≥ 99
* Architecture ≥ 99
* Maintainability ≥ 99
* Documentation ≥ 99

---

# Definition of Success

The project is considered successful only if:

* Every feature is production-ready.
* Documentation accurately reflects implementation.
* AI coding agents can implement the project without ambiguity.
* The platform is secure, scalable, observable, and maintainable.
* Every completed task satisfies the documented acceptance criteria and Definition of Done.

This document should always be the first document loaded before any implementation work begins.
