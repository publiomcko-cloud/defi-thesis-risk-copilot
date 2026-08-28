import logging
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes_admin import router as admin_router
from app.api.routes_analysis import router as analysis_router
from app.api.routes_auth import router as auth_router
from app.api.routes_customer_requests import router as customer_requests_router
from app.api.routes_demo import router as demo_router
from app.api.routes_deployment import router as deployment_router
from app.api.routes_discovery import router as discovery_router
from app.api.routes_documents import router as documents_router
from app.api.routes_evaluation import router as evaluation_router
from app.api.routes_health import router as health_router
from app.api.routes_internal_workers import router as internal_workers_router
from app.api.routes_jobs import router as jobs_router
from app.api.routes_knowledge_base import router as knowledge_base_router
from app.api.routes_knowledge import router as knowledge_router
from app.api.routes_market_data import router as market_data_router
from app.api.routes_monitoring import router as monitoring_router
from app.api.routes_notifications import router as notifications_router
from app.api.routes_options import router as options_router
from app.api.routes_organizations import router as organizations_router
from app.api.routes_protocols import router as protocols_router
from app.api.routes_product_analytics import router as product_analytics_router
from app.api.routes_reports import router as reports_router
from app.api.routes_schedules import router as schedules_router
from app.api.routes_simulation import router as simulation_router
from app.api.routes_theses import router as theses_router
from app.api.routes_vast import router as vast_router
from app.api.routes_watchlist import router as watchlist_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.observability import (
    CORRELATION_HEADER,
    REQUEST_ID_HEADER,
    correlation_context,
    normalize_correlation_id,
    safe_log_fields,
)

configure_logging()
logger = logging.getLogger("defi_copilot.requests")


class _RequestBodyTooLarge(Exception):
    pass


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
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Idempotency-Key",
            CORRELATION_HEADER,
            REQUEST_ID_HEADER,
        ],
        expose_headers=[CORRELATION_HEADER, REQUEST_ID_HEADER, "Retry-After"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        body_limit = _request_size_limit(request, settings)
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                declared_length = int(content_length)
            except ValueError:
                return _secured_json_response(
                    {"detail": "Invalid Content-Length header."}, status_code=400, settings=settings
                )
            if declared_length < 0:
                return _secured_json_response(
                    {"detail": "Invalid Content-Length header."}, status_code=400, settings=settings
                )
            if declared_length > body_limit:
                return _secured_json_response(
                    {"detail": "Request body exceeds the allowed size."}, status_code=413, settings=settings
                )
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            try:
                await _cache_limited_request_body(request, body_limit)
            except _RequestBodyTooLarge:
                return _secured_json_response(
                    {"detail": "Request body exceeds the allowed size."}, status_code=413, settings=settings
                )
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not _is_allowed_browser_origin(
            request.headers.get("origin"), allowed_origins
        ):
            return _secured_json_response(
                {"detail": "Browser origin is not allowed."}, status_code=403, settings=settings
            )
        request_id = normalize_correlation_id(
            request.headers.get(CORRELATION_HEADER) or request.headers.get(REQUEST_ID_HEADER),
            prefix="req",
        )
        request.state.request_id = request_id
        request.state.correlation_id = request_id
        started = perf_counter()
        with correlation_context(request_id, operation="api.request"):
            response = await call_next(request)
            duration_ms = round((perf_counter() - started) * 1000, 2)
            response.headers[REQUEST_ID_HEADER] = request_id
            response.headers[CORRELATION_HEADER] = request_id
            _apply_security_headers(response, settings)
            logger.info(
                "API request completed",
                extra={
                    "event": "api.request.completed",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "observability": safe_log_fields(
                        app_env=settings.app_env,
                        public_demo_mode=settings.public_demo_mode,
                    ),
                },
            )
            return response

    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router, prefix="/api")
    app.include_router(customer_requests_router, prefix="/api")
    app.include_router(demo_router, prefix="/api")
    app.include_router(deployment_router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    app.include_router(analysis_router, prefix="/api")
    app.include_router(jobs_router, prefix="/api")
    app.include_router(reports_router, prefix="/api")
    app.include_router(schedules_router, prefix="/api")
    app.include_router(protocols_router, prefix="/api")
    app.include_router(product_analytics_router, prefix="/api")
    app.include_router(organizations_router, prefix="/api")
    app.include_router(theses_router, prefix="/api")
    app.include_router(documents_router, prefix="/api")
    app.include_router(discovery_router, prefix="/api")
    app.include_router(market_data_router, prefix="/api")
    app.include_router(monitoring_router, prefix="/api")
    app.include_router(notifications_router, prefix="/api")
    app.include_router(evaluation_router, prefix="/api")
    app.include_router(knowledge_base_router, prefix="/api")
    app.include_router(knowledge_router, prefix="/api")
    app.include_router(simulation_router, prefix="/api")
    app.include_router(watchlist_router, prefix="/api")
    app.include_router(options_router, prefix="/api")
    app.include_router(vast_router, prefix="/api")
    app.include_router(internal_workers_router)

    return app


app = create_app()


def _request_size_limit(request: Request, settings) -> int:
    if request.url.path.startswith("/api/knowledge/"):
        # Multipart framing is small relative to the bounded document bytes.
        return settings.knowledge_upload_max_bytes + 128 * 1024
    return settings.api_max_request_bytes


async def _cache_limited_request_body(request: Request, limit: int) -> None:
    """Bound streamed bodies even when Content-Length is missing or dishonest."""

    if hasattr(request, "_body"):
        return
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise _RequestBodyTooLarge()
        chunks.append(chunk)
    # Starlette reuses this cache for FastAPI body and multipart parsing.
    request._body = b"".join(chunks)


def _is_allowed_browser_origin(origin: str | None, allowed_origins: list[str]) -> bool:
    # Non-browser clients do not send Origin. Browser mutations must use an exact
    # configured frontend origin; CORS alone would not block a forged POST.
    return origin is None or origin in allowed_origins


def _secured_json_response(content: dict[str, str], *, status_code: int, settings) -> JSONResponse:
    response = JSONResponse(content, status_code=status_code)
    _apply_security_headers(response, settings)
    return response


def _apply_security_headers(response, settings) -> None:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(), geolocation=(), microphone=(), payment=(), usb=()"
    )
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    if settings.security_hsts_enabled:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
