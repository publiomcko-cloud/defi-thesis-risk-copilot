import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("defi_copilot.errors")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled API error",
            extra={
                "path": str(request.url.path),
                "method": request.method,
                "request_id": getattr(request.state, "request_id", None),
                "exception_type": type(exc).__name__,
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
