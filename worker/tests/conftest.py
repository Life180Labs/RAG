import os
import uuid

# Exercises the real Postgres + MinIO containers from
# docker/docker-compose.yml, same as the backend's integration tests —
# must be set before `common.db`/`common.storage` are first imported.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://rag:rag@localhost:5433/rag")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9002")
os.environ.setdefault("MINIO_ACCESS_KEY", "ragadmin")
os.environ.setdefault("MINIO_SECRET_KEY", "ragadminsecret")
os.environ.setdefault("MINIO_BUCKET", "rag-documents")

import pytest
from sqlalchemy import text

from common.db import SessionLocal


@pytest.fixture
def document_chain():
    """Creates one full organization -> workspace -> project -> repository
    -> user chain via raw SQL (the worker has no ORM models — see
    document_worker/tasks.py) and yields the repository_id/user_id needed
    to insert a document row. Cleans up afterward."""
    ids = {
        "user_id": uuid.uuid4(),
        "organization_id": uuid.uuid4(),
        "workspace_id": uuid.uuid4(),
        "project_id": uuid.uuid4(),
        "repository_id": uuid.uuid4(),
    }

    with SessionLocal() as session:
        session.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, full_name, role, is_active, "
                "failed_login_attempts) VALUES (:id, :email, 'x', 'Worker Test User', 'VIEWER', "
                "true, 0)"
            ),
            {"id": ids["user_id"], "email": f"worker-test-{ids['user_id']}@example.com"},
        )
        session.execute(
            text(
                "INSERT INTO organizations (id, name, slug, status) "
                "VALUES (:id, 'Test Org', :slug, 'ACTIVE')"
            ),
            {"id": ids["organization_id"], "slug": f"test-org-{ids['organization_id']}"},
        )
        session.execute(
            text(
                "INSERT INTO workspaces (id, organization_id, name, slug, status) "
                "VALUES (:id, :org_id, 'Test Workspace', :slug, 'ACTIVE')"
            ),
            {
                "id": ids["workspace_id"],
                "org_id": ids["organization_id"],
                "slug": f"test-ws-{ids['workspace_id']}",
            },
        )
        session.execute(
            text(
                "INSERT INTO projects (id, workspace_id, name, slug, status) "
                "VALUES (:id, :ws_id, 'Test Project', :slug, 'ACTIVE')"
            ),
            {
                "id": ids["project_id"],
                "ws_id": ids["workspace_id"],
                "slug": f"test-project-{ids['project_id']}",
            },
        )
        session.execute(
            text(
                "INSERT INTO repositories (id, project_id, name, slug, status, document_count, "
                "chunk_count, embedding_count, storage_used_bytes, retrieval_count) "
                "VALUES (:id, :project_id, 'Test Repo', :slug, 'ACTIVE', 0, 0, 0, 0, 0)"
            ),
            {
                "id": ids["repository_id"],
                "project_id": ids["project_id"],
                "slug": f"test-repo-{ids['repository_id']}",
            },
        )
        session.commit()

    yield ids

    with SessionLocal() as session:
        session.execute(
            text(
                "TRUNCATE documents, repositories, projects, workspaces, organizations, users "
                "CASCADE"
            )
        )
        session.commit()
