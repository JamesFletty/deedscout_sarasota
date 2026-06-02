from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class StoredArtifact(BaseModel):
    uri: str
    content_hash: str
    size_bytes: int
    created_at: datetime


class StorageBackend(ABC):
    @abstractmethod
    def save_html(self, batch_id: str, source_url: str, html: str) -> StoredArtifact: ...

    @abstractmethod
    def save_screenshot(self, batch_id: str, source_url: str, image_bytes: bytes) -> StoredArtifact: ...

    @abstractmethod
    def save_json(self, batch_id: str, name: str, payload: dict[str, Any]) -> StoredArtifact: ...

    @abstractmethod
    def save_export(self, batch_id: str, filename: str, bytes_data: bytes) -> StoredArtifact: ...
