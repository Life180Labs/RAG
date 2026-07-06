"""Per-organization provider credential lookup.

Decrypts `provider_credentials.encrypted_key` rows written by the backend
(`backend/app/core/security.py`'s `encrypt_credential`). Duplicated Fernet
logic rather than importing the backend module — same "separate
deployables, no shared codebase mount" rule as the rest of this package;
both sides must be configured with an identical `CREDENTIAL_ENCRYPTION_KEY`.
"""

from functools import lru_cache

from cryptography.fernet import Fernet
from sqlalchemy import text
from sqlalchemy.orm import Session

from common.config import get_worker_settings


@lru_cache
def _fernet() -> Fernet:
    return Fernet(get_worker_settings().credential_encryption_key.encode())


def get_org_credential(session: Session, organization_id: str, provider: str) -> str | None:
    row = session.execute(
        text(
            "SELECT encrypted_key FROM provider_credentials "
            "WHERE organization_id = :organization_id AND provider = :provider"
        ),
        {"organization_id": organization_id, "provider": provider},
    ).first()
    if row is None:
        return None
    return _fernet().decrypt(row.encrypted_key.encode()).decode()
