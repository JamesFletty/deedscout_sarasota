from fastapi import APIRouter

from app.core.config import get_settings
from app.db.session import is_database_reachable

router = APIRouter()


@router.get("/health")
def health() -> dict[str, object]:
    settings = get_settings()
    database_reachable = is_database_reachable()
    return {
        "status": "ok" if database_reachable else "degraded",
        "app_env": settings.app_env,
        "database_reachable": database_reachable,
    }
