from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get(
    "",
    summary="Get system metadata",
    description="Returns non-secret system metadata for frontend diagnostics.",
)
def get_system() -> dict[str, str]:
    return {"name": "DeedScout Sarasota API", "mode": "local-first MVP"}
