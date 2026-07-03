# Contributing to Enterprise RAG Studio

## Before You Start

Read the documentation in the order defined by [`docs/00-index.md`](docs/00-index.md). Implementation must follow `docs/07-master_prompt.md` (the engineering operating system) and `docs/06-rule.md` (the engineering constitution).

## Branch Strategy

Protected branches: `main`, `develop`. Never commit directly to them.

Working branches:

```
feature/<short-description>
bugfix/<short-description>
hotfix/<short-description>
release/<version>
```

## Commit Messages

Conventional commits, describing intent:

```
feat(retrieval): implement hybrid search with BM25 fusion
fix(auth): enforce RBAC on repository APIs
refactor(chunking): simplify recursive chunk strategy
docs(api): update evaluation endpoints
test(worker): add embedding worker retry tests
```

## Development Workflow

1. Read relevant documentation (architecture, database, API spec, task).
2. Confirm task dependencies in `docs/05-task.md` are satisfied.
3. Implement following the layered architecture (Controller → Service → Repository → Database).
4. Add unit, integration, and API tests.
5. Run lint and static analysis.
6. Update documentation (`docs/03-database.md`, `docs/04-api-spec.md`, `docs/02-architecture.md` as applicable).
7. Update `docs/05-task.md` checkboxes.
8. Open a pull request.

## Pull Request Requirements

* Summary, scope, related task, risks, testing performed.
* CI passing, no unresolved TODOs, no unrelated changes.
* Documentation and `task.md` synchronized with the change.

## Code Standards

* Backend: Controllers never contain business logic or SQL. Business logic lives in services; data access lives in repositories.
* Frontend: pages must implement loading/empty/error/success states; business logic lives in hooks/services, not components.
* Every table needs a UUID primary key, `created_at`, `updated_at`, and (where applicable) soft delete and audit fields.
* Never hardcode secrets or prompts inside business logic.
