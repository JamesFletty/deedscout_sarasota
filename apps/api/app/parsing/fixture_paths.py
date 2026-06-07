from __future__ import annotations

from pathlib import Path

FIXTURE_HTML_RELATIVE = Path("fixtures/sarasota/html")


def resolve_sarasota_fixtures_dir(configured: Path | None = None) -> Path:
    if configured is not None:
        candidate = configured.expanduser()
        if not candidate.is_absolute():
            candidate = _resolve_relative(candidate)
        if not candidate.is_dir():
            raise FileNotFoundError(f"Sarasota fixtures directory not found: {candidate}")
        return candidate

    discovered = _discover_default_fixtures_dir()
    if discovered is None:
        raise FileNotFoundError(
            f"Could not locate {FIXTURE_HTML_RELATIVE}. "
            "Set SARASOTA_FIXTURES_DIR or run from the monorepo root."
        )
    return discovered


def _resolve_relative(path: Path) -> Path:
    for base in (Path.cwd(), *_repo_roots()):
        candidate = (base / path).resolve()
        if candidate.is_dir():
            return candidate
    return (Path.cwd() / path).resolve()


def _discover_default_fixtures_dir() -> Path | None:
    for base in _repo_roots():
        candidate = (base / FIXTURE_HTML_RELATIVE).resolve()
        if candidate.is_dir():
            return candidate
    return None


def _repo_roots() -> tuple[Path, ...]:
    here = Path(__file__).resolve()
    roots: list[Path] = []
    for parent in here.parents:
        if (parent / "fixtures" / "sarasota" / "html").is_dir():
            roots.append(parent)
        if (parent / "apps" / "api").is_dir() and (parent / "fixtures").is_dir():
            roots.append(parent)
    return tuple(dict.fromkeys(roots))
