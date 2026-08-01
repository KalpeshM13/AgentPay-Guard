"""Exception handlers for the FastAPI application.

Maps common exception types to structured JSON error responses.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle standard HTTP exceptions (404, 405, etc.)."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
        },
    )


async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all handler for unhandled exceptions."""
    if settings.DEBUG:
        # In debug mode, return the actual error message for convenience
        detail = str(exc)
    else:
        detail = "Internal server error"

    return JSONResponse(
        status_code=500,
        content={
            "detail": detail,
            "status_code": 500,
        },
    )
