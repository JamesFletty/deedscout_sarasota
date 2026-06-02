import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.storage.base import StorageBackend, StoredArtifact

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


class LocalStorage(StorageBackend):
    def __init__(self, root: Path | str = Path("./.storage")) -> None:
        self.root = Path(root)

    def save_html(self, batch_id: str, source_url: str, html: str) -> StoredArtifact:
        return self._write(batch_id, "html", self._source_name(source_url, "html"), html.encode("utf-8"))

    def save_screenshot(self, batch_id: str, source_url: str, image_bytes: bytes) -> StoredArtifact:
        return self._write(batch_id, "screenshots", self._source_name(source_url, "png"), image_bytes)

    def save_json(self, batch_id: str, name: str, payload: dict[str, Any]) -> StoredArtifact:
        data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return self._write(batch_id, "json", self._clean_filename(name, "json"), data)

    def save_export(self, batch_id: str, filename: str, bytes_data: bytes) -> StoredArtifact:
        return self._write(batch_id, "exports", self._clean_filename(filename), bytes_data)

    def _write(self, batch_id: str, category: str, filename: str, data: bytes) -> StoredArtifact:
        digest = hashlib.sha256(data).hexdigest()
        batch = self._safe_segment(batch_id)
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        path = self.root / batch / category / f"{stem}-{digest[:16]}{suffix}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return StoredArtifact(
            uri=str(path),
            content_hash=digest,
            size_bytes=len(data),
            created_at=datetime.now(UTC),
        )

    def _source_name(self, source_url: str, extension: str) -> str:
        parsed = urlparse(source_url)
        candidate = parsed.netloc + parsed.path
        if not candidate:
            candidate = "source"
        return self._clean_filename(candidate, extension)

    def _clean_filename(self, filename: str, extension: str | None = None) -> str:
        path = Path(filename).name
        cleaned = self._safe_segment(path)
        if extension and not cleaned.endswith(f".{extension}"):
            cleaned = f"{cleaned}.{extension}"
        return cleaned

    def _safe_segment(self, value: str) -> str:
        cleaned = _SAFE_NAME.sub("-", value.strip()).strip(".-")
        if not cleaned:
            raise ValueError("storage path segment cannot be empty")
        return cleaned[:120]
