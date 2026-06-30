from fastapi import FastAPI

from app.api.routes.explain import router as explain_router
from app.api.routes.health import router as health_router
from app.api.routes.narratives import router as narratives_router
from app.api.routes.search import router as search_router
from app.api.routes.version import router as version_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.include_router(explain_router, prefix="/api")
    app.include_router(health_router)
    app.include_router(narratives_router, prefix="/api")
    app.include_router(search_router, prefix="/api")
    app.include_router(version_router, prefix="/api")
    return app


app = create_app()
