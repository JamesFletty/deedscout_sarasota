from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.routes.batches import router as batches_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.records import router as records_router
from app.api.routes.system import router as system_router
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="DeedScout Sarasota API", version="0.1.0")
    app.include_router(health_router)
    app.include_router(batches_router)
    app.include_router(records_router)
    app.include_router(jobs_router)
    app.include_router(system_router)
    return app


app = create_app()
