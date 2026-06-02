from typing import Any

from app.storage.base import StorageBackend, StoredArtifact


class AzureBlobStorage(StorageBackend):
    def __init__(self, connection_string: str | None = None, container_name: str | None = None) -> None:
        if not connection_string or not container_name:
            raise ValueError("Azure Blob storage requires connection_string and container_name")
        self.connection_string = connection_string
        self.container_name = container_name

    def save_html(self, batch_id: str, source_url: str, html: str) -> StoredArtifact:
        raise NotImplementedError("Azure Blob storage adapter is configured but upload support is not enabled")

    def save_screenshot(self, batch_id: str, source_url: str, image_bytes: bytes) -> StoredArtifact:
        raise NotImplementedError("Azure Blob storage adapter is configured but upload support is not enabled")

    def save_json(self, batch_id: str, name: str, payload: dict[str, Any]) -> StoredArtifact:
        raise NotImplementedError("Azure Blob storage adapter is configured but upload support is not enabled")

    def save_export(self, batch_id: str, filename: str, bytes_data: bytes) -> StoredArtifact:
        raise NotImplementedError("Azure Blob storage adapter is configured but upload support is not enabled")
