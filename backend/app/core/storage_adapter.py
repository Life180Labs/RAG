"""Storage adapter abstraction (docs/05-task.md Phase 4 "Storage Adapter").

`app/core/storage.py` provides the raw MinIO client; this module wraps
it (and a local-filesystem alternative) behind a uniform interface so
the document service never talks to MinIO or the filesystem directly.

MinIO (S3-compatible) can generate presigned URLs so a download goes
straight from the client to the object store, bypassing the backend
entirely. Local disk storage has no equivalent — there is no "storage
service" to hand a URL to — so `presigned_download_url` returns `None`
for it, and callers fall back to streaming the file through
`open_stream()` instead. This is a real architectural difference, not a
missing feature.
"""

import io
import os
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import BinaryIO

from app.core.config import get_settings
from app.core.storage import get_storage_client


class StorageAdapter(ABC):
    @abstractmethod
    def upload(self, key: str, data: BinaryIO, size: int, content_type: str) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def open_stream(self, key: str) -> BinaryIO: ...

    @abstractmethod
    def presigned_download_url(self, key: str, expires_seconds: int = 3600) -> str | None: ...


class MinioStorageAdapter(StorageAdapter):
    def __init__(self, bucket: str):
        self.client = get_storage_client()
        self.bucket = bucket

    def upload(self, key: str, data: BinaryIO, size: int, content_type: str) -> None:
        self.client.put_object(self.bucket, key, data, length=size, content_type=content_type)

    def delete(self, key: str) -> None:
        self.client.remove_object(self.bucket, key)

    def exists(self, key: str) -> bool:
        try:
            self.client.stat_object(self.bucket, key)
            return True
        except Exception:  # noqa: BLE001 - minio raises a broad S3Error for "not found" too
            return False

    def open_stream(self, key: str) -> BinaryIO:
        response = self.client.get_object(self.bucket, key)
        return io.BytesIO(response.read())

    def presigned_download_url(self, key: str, expires_seconds: int = 3600) -> str | None:
        return self.client.presigned_get_object(
            self.bucket, key, expires=timedelta(seconds=expires_seconds)
        )


class LocalFilesystemStorageAdapter(StorageAdapter):
    """Dev/offline fallback — no object store required. Never used in the
    dockerized stack (which always runs MinIO); useful for running the
    backend standalone without Docker."""

    def __init__(self, root: str):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def _path(self, key: str) -> str:
        path = os.path.join(self.root, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    def upload(self, key: str, data: BinaryIO, size: int, content_type: str) -> None:
        with open(self._path(key), "wb") as f:
            while chunk := data.read(1024 * 1024):
                f.write(chunk)

    def delete(self, key: str) -> None:
        path = self._path(key)
        if os.path.exists(path):
            os.remove(path)

    def exists(self, key: str) -> bool:
        return os.path.exists(self._path(key))

    def open_stream(self, key: str) -> BinaryIO:
        return open(self._path(key), "rb")  # noqa: SIM115 - caller owns/closes the stream

    def presigned_download_url(self, key: str, expires_seconds: int = 3600) -> str | None:
        return None


def get_storage_adapter() -> StorageAdapter:
    settings = get_settings()
    if settings.storage_backend == "local":
        return LocalFilesystemStorageAdapter(settings.local_storage_path)
    return MinioStorageAdapter(settings.minio_bucket)
