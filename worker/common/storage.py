"""Minimal MinIO client for workers.

Deliberately not the backend's full `StorageAdapter` abstraction — the
worker and backend are separate deployables (separate Docker images, no
shared codebase mount), and a worker task only ever needs to check that
an object exists or fetch its bytes, never the presigned-URL/local-disk
logic that only the API layer's downloads need.
"""

from minio import Minio

from common.config import get_worker_settings


def get_storage_client() -> Minio:
    settings = get_worker_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def object_exists(bucket: str, key: str) -> bool:
    client = get_storage_client()
    try:
        client.stat_object(bucket, key)
        return True
    except Exception:  # noqa: BLE001 - minio raises a broad S3Error for "not found" too
        return False
