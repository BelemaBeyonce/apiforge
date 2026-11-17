import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from app.api.routes import router
from app.config import settings
from app.logging import configure_logging
from app.schemas import ErrorResponse

configure_logging(settings.log_level)
logger = logging.getLogger("apiforge")
app = FastAPI(
    title="APIForge — Python Backend & AI Evaluation Lab",
    version="0.1.0",
    description="Deterministic reference evaluation. Submitted text is never executed.",
    responses={
        status: {"model": ErrorResponse, "description": description}
        for status, description in {
            404: "Resource not found",
            405: "Method not allowed",
            422: "Validation failed",
            500: "Unexpected failure",
            503: "Database unavailable",
        }.items()
    },
)


def error(request, status, code, message, details=None):
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return error(request, exc.status_code, "http_error", str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    details = [
        {"location": list(e["loc"]), "message": e["msg"], "type": e["type"]} for e in exc.errors()
    ]
    return error(request, 422, "validation_error", "Request validation failed", details)


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    logger.error("Database operation failed", extra={"request_id": request.state.request_id})
    return error(request, 503, "database_unavailable", "Database temporarily unavailable")


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = str(uuid4())
    start = perf_counter()
    try:
        response = await call_next(request)
    except Exception:  # noqa: BLE001 - sanitize unexpected failures at the HTTP boundary
        logger.error("Unhandled request failure", extra={"request_id": request.state.request_id})
        response = error(request, 500, "internal_error", "An unexpected error occurred")
    response.headers["X-Request-ID"] = request.state.request_id
    logger.info(
        "request_completed",
        extra={
            "request_id": request.state.request_id,
            "method": request.method,
            "status": response.status_code,
            "duration_ms": round((perf_counter() - start) * 1000, 2),
        },
    )
    return response


app.include_router(router, prefix="/api/v1")
