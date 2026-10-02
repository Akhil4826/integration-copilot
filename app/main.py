"""FastAPI application entrypoint for Integration Copilot."""

import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    agent_router,
    analytics_router,
    customers_router,
    health_router,
    metrics_router,
    orders_router,
    tickets_router,
)
from app.core.config import get_settings
from app.core.errors import AppException, ErrorDetail, ErrorResponse
from app.core.logging import current_request_id, logger, setup_logging
from app.core.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
)
from app.db.database import Base, engine

settings = get_settings()
setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle hooks: initialize database and warm up resources."""
    logger.info("Initializing Integration Copilot backend service...")
    Base.metadata.create_all(bind=engine)
    logger.info(
        f"Integration Copilot started successfully [Env: {settings.app_env}, LLM: {settings.llm_provider}:{settings.llm_model}]"
    )
    yield
    logger.info("Shutting down Integration Copilot...")


app = FastAPI(
    title="Integration Copilot — AI-Powered Business API Assistant",
    description=(
        "Production-style backend service integrating LLM tool calling, Model Context Protocol (MCP), "
        "relational data access, confirmation-gated write operations, and enterprise observability."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Enable CORS for local web development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_observability_middleware(request: Request, call_next):
    """Assigns unique request_id, propagates context, and records latency metrics."""
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    token = current_request_id.set(req_id)
    start_time = time.perf_counter()

    try:
        response: Response = await call_next(request)
        duration_sec = time.perf_counter() - start_time

        # Record HTTP metrics
        endpoint = request.url.path
        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=str(response.status_code),
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(duration_sec)

        response.headers["X-Request-ID"] = req_id
        return response
    finally:
        current_request_id.reset(token)


# Centralized Structured Error Handlers (Section 12)
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    req_id = current_request_id.get(str(uuid.uuid4()))
    logger.warning(f"Application error [{exc.code}]: {exc.message}")
    payload = ErrorResponse(
        error=ErrorDetail(
            code=exc.code,
            message=exc.message,
            request_id=req_id,
            details=exc.details,
        )
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = current_request_id.get(str(uuid.uuid4()))
    logger.warning(f"Request validation failure: {exc.errors()}")
    payload = ErrorResponse(
        error=ErrorDetail(
            code="VALIDATION_ERROR",
            message="Invalid request parameters or payload",
            request_id=req_id,
            details=exc.errors(),
        )
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=payload.model_dump()
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    req_id = current_request_id.get(str(uuid.uuid4()))
    payload = ErrorResponse(
        error=ErrorDetail(
            code="HTTP_ERROR",
            message=str(exc.detail),
            request_id=req_id,
        )
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    req_id = current_request_id.get(str(uuid.uuid4()))
    logger.error(f"Unhandled server error: {exc}", exc_info=True)
    payload = ErrorResponse(
        error=ErrorDetail(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal server error occurred.",
            request_id=req_id,
        )
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload.model_dump()
    )


# Register Core & API Routers
app.include_router(health_router)
app.include_router(metrics_router)

# Versioned API routes
api_v1_prefix = "/api/v1"
app.include_router(customers_router, prefix=api_v1_prefix)
app.include_router(orders_router, prefix=api_v1_prefix)
app.include_router(tickets_router, prefix=api_v1_prefix)
app.include_router(analytics_router, prefix=api_v1_prefix)
app.include_router(agent_router, prefix=api_v1_prefix)

# Static Frontend mounting
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "Integration Copilot API is running. Visit /docs for Swagger UI."}
