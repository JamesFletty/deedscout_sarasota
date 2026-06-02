import os

from app.core.config import Settings, get_settings
from app.storage.azure_blob_storage import AzureBlobStorage
from app.storage.base import StorageBackend
from app.storage.local_storage import LocalStorage


def build_storage(settings: Settings | None = None) -> StorageBackend:
    active = settings or get_settings()
    if active.storage_backend == "local":
        return LocalStorage(active.local_storage_root)
    if active.storage_backend == "azure_blob":
        return AzureBlobStorage(
            connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
            container_name=os.getenv("AZURE_STORAGE_CONTAINER"),
        )
    raise ValueError(f"Unsupported storage backend: {active.storage_backend}")
