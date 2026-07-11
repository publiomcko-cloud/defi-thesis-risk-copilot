from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_analysis import router as analysis_router
from app.api.routes_documents import router as documents_router
from app.api.routes_evaluation import router as evaluation_router
from app.api.routes_health import router as health_router
from app.api.routes_market_data import router as market_data_router
from app.api.routes_monitoring import router as monitoring_router
from app.api.routes_protocols import router as protocols_router
from app.api.routes_reports import router as reports_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Research and risk analysis API for DeFi Thesis & Risk Copilot.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(analysis_router, prefix="/api")
    app.include_router(reports_router, prefix="/api")
    app.include_router(protocols_router, prefix="/api")
    app.include_router(documents_router, prefix="/api")
    app.include_router(market_data_router, prefix="/api")
    app.include_router(monitoring_router, prefix="/api")
    app.include_router(evaluation_router, prefix="/api")

    return app


app = create_app()
