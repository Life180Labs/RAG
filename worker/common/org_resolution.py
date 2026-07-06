"""Resolve an organization_id from a document_id.

Raw SQL (not the backend's ORM models), same reasoning as every other
worker task — see document_worker/tasks.py. The join chain mirrors the
tenancy FK hierarchy: documents -> repositories -> projects -> workspaces
-> organizations.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session


def resolve_organization_id(session: Session, document_id: str) -> str | None:
    row = session.execute(
        text(
            "SELECT w.organization_id AS organization_id "
            "FROM documents d "
            "JOIN repositories r ON r.id = d.repository_id "
            "JOIN projects p ON p.id = r.project_id "
            "JOIN workspaces w ON w.id = p.workspace_id "
            "WHERE d.id = :document_id"
        ),
        {"document_id": document_id},
    ).first()
    if row is None:
        return None
    return str(row.organization_id)
