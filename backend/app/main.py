from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import QdrantClient
from redis import Redis
from sqlalchemy import text

from app.api.routes import admin, auth, documents, exports, history, metrics, ops, projects, qa, research, search, teams
from app.core.config import get_settings
from app.core.logging import RateLimitMiddleware, RequestLoggingMiddleware, SecurityHeadersMiddleware, configure_logging
from app.core.tracing import configure_tracing
from app.db.session import engine


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    app = FastAPI(title=settings.app_name, version="1.0.0")
    configure_tracing(app, engine)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready():
        checks = {}
        try:
            with engine.connect() as connection:
                connection.execute(text("select 1"))
            checks["postgres"] = "ok"
        except Exception as exc:
            checks["postgres"] = f"error: {exc}"

        try:
            Redis.from_url(settings.redis_url).ping()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error: {exc}"

        try:
            QdrantClient(url=settings.qdrant_url).get_collections()
            checks["qdrant"] = "ok"
        except Exception as exc:
            checks["qdrant"] = f"error: {exc}"

        status = "ready" if all(value == "ok" for value in checks.values()) else "degraded"
        return {"status": status, "checks": checks}

    app.include_router(auth.router, prefix=settings.api_prefix)
    app.include_router(admin.router, prefix=settings.api_prefix)
    app.include_router(documents.router, prefix=settings.api_prefix)
    app.include_router(search.router, prefix=settings.api_prefix)
    app.include_router(qa.router, prefix=settings.api_prefix)
    app.include_router(research.router, prefix=settings.api_prefix)
    app.include_router(projects.router, prefix=settings.api_prefix)
    app.include_router(teams.router, prefix=settings.api_prefix)
    app.include_router(exports.router, prefix=settings.api_prefix)
    app.include_router(ops.router, prefix=settings.api_prefix)
    app.include_router(metrics.router, prefix=settings.api_prefix)
    app.include_router(history.router, prefix=settings.api_prefix)
    return app


app = create_app()
