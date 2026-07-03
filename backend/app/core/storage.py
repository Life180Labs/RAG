"""MinIO object storage client factory."""

from functools import lru_cache

from minio import Minio

from app.core.config import get_settings


@lru_cache
def get_storage_client() -> Minio:
    settings = get_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket_exists(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
