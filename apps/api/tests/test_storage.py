import hashlib
import json

from app.storage.local_storage import LocalStorage


def test_local_storage_saves_html_with_stable_hash(tmp_path) -> None:  # type: ignore[no-untyped-def]
    storage = LocalStorage(tmp_path)
    html = "<html><body>Sarasota fixture</body></html>"

    artifact = storage.save_html("batch-1", "https://example.test/detail?id=1", html)

    assert artifact.content_hash == hashlib.sha256(html.encode("utf-8")).hexdigest()
    assert artifact.size_bytes == len(html.encode("utf-8"))
    assert artifact.uri.endswith(".html")
    assert (tmp_path / "batch-1" / "html").exists()


def test_local_storage_saves_json_canonically(tmp_path) -> None:  # type: ignore[no-untyped-def]
    storage = LocalStorage(tmp_path)
    payload = {"b": 2, "a": 1}

    artifact = storage.save_json("batch-1", "record", payload)
    saved = json.loads(open(artifact.uri, encoding="utf-8").read())

    assert saved == {"a": 1, "b": 2}
    assert artifact.content_hash == hashlib.sha256(b'{"a":1,"b":2}').hexdigest()
