"""AgentPay Guard — FastAPI application entry point.

Start the server with::

    uvicorn app.main:app --host 0.0.0.0 --port 8000

Production (Render / Railway)::

    uvicorn app.main:app --host 0.0.0.0 --port $PORT --no-access-log
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.exceptions import generic_exception_handler, http_exception_handler
from app.api.router import api_router
from app.core.config import settings, validate_production_settings
from app.db.init_db import init_db



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan."""

    from app.core.logging import setup_logging
    setup_logging()

    validate_production_settings()

    await init_db()

    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(api_router)  # root level registration for simple clients / test suite compatibility

@app.get("/")
def root():
    return {"message": "API is running!"}

@app.get("/health", tags=["health"])
async def health_check():
    """Liveness probe — returns 200 when the server is running."""
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
