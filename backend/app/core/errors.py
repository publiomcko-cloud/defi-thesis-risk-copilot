import logging
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.observability import safe_log_fields

logger = logging.getLogger("defi_copilot.errors")

_CUSTOMER_REQUEST_CREATE_PATH = "/api/customer-requests"
_CUSTOMER_REQUEST_INPUT_FIELDS = frozenset(
    {"request_type", "subject", "description", "organization_id"}
)
_SAFE_VALIDATION_MESSAGES = {
    "extra_forbidden": "Request contains an unsupported field.",
    "json_invalid": "Request body is not valid JSON.",
    "literal_error": "Field has an unsupported value.",
    "missing": "Required field is missing.",
    "string_too_long": "Field exceeds the allowed length.",
    "string_too_short": "Field is shorter than the allowed length.",
    "string_type": "Field must be a string.",
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        if _is_customer_request_create(request):
            return JSONResponse(
                status_code=422,
                content={"detail": _safe_customer_request_validation_errors(exc.errors())},
            )
        return await request_validation_exception_handler(request, exc)

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled API error",
            extra={
                "event": "api.request.failed",
                "path": str(request.url.path),
                "method": request.method,
                "request_id": getattr(request.state, "request_id", None),
                "exception_type": type(exc).__name__,
                "observability": safe_log_fields(status_code=500),
            },
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "path": str(request.url.path),
                "request_id": getattr(request.state, "request_id", None),
            },
        )


def _is_customer_request_create(request: Request) -> bool:
    return (
        request.method == "POST"
        and request.url.path.rstrip("/") == _CUSTOMER_REQUEST_CREATE_PATH
    )


def _safe_customer_request_validation_errors(errors: list[Mapping[str, Any]]) -> list[dict[str, object]]:
    """Return bounded request-validation metadata without rejected values."""

    sanitized: list[dict[str, object]] = []
    for error in errors:
        code = str(error.get("type", "invalid_request"))
        message = _SAFE_VALIDATION_MESSAGES.get(code, "Invalid request field.")
        sanitized.append(
            {
                "loc": _safe_customer_request_validation_location(error.get("loc")),
                "msg": message,
                "type": code if code in _SAFE_VALIDATION_MESSAGES else "invalid_request",
            }
        )
    return sanitized


def _safe_customer_request_validation_location(location: object) -> list[str]:
    if (
        isinstance(location, tuple)
        and len(location) == 2
        and location[0] == "body"
        and location[1] in _CUSTOMER_REQUEST_INPUT_FIELDS
    ):
        return ["body", str(location[1])]
    return ["body"]
