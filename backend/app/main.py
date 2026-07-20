import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_admin import router as admin_router
from app.api.routes_analysis import router as analysis_router
from app.api.routes_auth import router as auth_router
from app.api.routes_demo import router as demo_router
from app.api.routes_deployment import router as deployment_router
from app.api.routes_discovery import router as discovery_router
from app.api.routes_documents import router as documents_router
from app.api.routes_evaluation import router as evaluation_router
from app.api.routes_health import router as health_router
from app.api.routes_knowledge_base import router as knowledge_base_router
from app.api.routes_market_data import router as market_data_router
from app.api.routes_monitoring import router as monitoring_router
from app.api.routes_options import router as options_router
from app.api.routes_organizations import router as organizations_router
from app.api.routes_protocols import router as protocols_router
from app.api.routes_reports import router as reports_router
from app.api.routes_simulation import router as simulation_router
from app.api.routes_theses import router as theses_router
from app.api.routes_vast import router as vast_router
from app.api.routes_watchlist import router as watchlist_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger("defi_copilot.requests")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Research and risk analysis API for DeFi Thesis & Risk Copilot.",
    )

    allowed_origins = [
        origin.strip()
        for origin in settings.frontend_origin.split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins or ["http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid4().hex
        request.state.request_id = request_id
        started = perf_counter()
        response = await call_next(request)
        duration_ms = round((perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "API request request_id=%s method=%s path=%s status=%s duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router, prefix="/api")
    app.include_router(demo_router, prefix="/api")
    app.include_router(deployment_router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    app.include_router(analysis_router, prefix="/api")
    app.include_router(reports_router, prefix="/api")
    app.include_router(protocols_router, prefix="/api")
    app.include_router(organizations_router, prefix="/api")
    app.include_router(theses_router, prefix="/api")
    app.include_router(documents_router, prefix="/api")
    app.include_router(discovery_router, prefix="/api")
    app.include_router(market_data_router, prefix="/api")
    app.include_router(monitoring_router, prefix="/api")
    app.include_router(evaluation_router, prefix="/api")
    app.include_router(knowledge_base_router, prefix="/api")
    app.include_router(simulation_router, prefix="/api")
    app.include_router(watchlist_router, prefix="/api")
    app.include_router(options_router, prefix="/api")
    app.include_router(vast_router, prefix="/api")

    return app


app = create_app()
