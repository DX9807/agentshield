"""AgentShield FastAPI application entry point."""

import time
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, Response

from .api.middleware.metrics import MetricsMiddleware
from .api.v1 import agents, capabilities, gateway, health, policies, tasks
from .core.config import settings
from .core.exceptions import AgentShieldError
from .core.logging import get_logger, setup_logging
from .infrastructure.cache.redis_client import redis_client
from .infrastructure.database.session import db_manager
from .infrastructure.metrics.prometheus import (
    get_metrics,
    update_gateway_health,
    update_system_info,
)
from .infrastructure.tracing.opentelemetry import setup_tracing

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    startup_time = time.time()

    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.APP_ENV}")

    # Update system info
    update_system_info(settings.APP_VERSION, settings.APP_ENV)
    update_gateway_health(True)

    # Initialize database
    try:
        await db_manager.create_tables()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        update_gateway_health(False)
        raise

    # Connect to Redis
    try:
        await redis_client.connect()
        logger.info("Redis connected")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        # Continue without Redis (non-critical for startup)

    # Setup OpenTelemetry
    setup_tracing(app)

    yield

    # Shutdown
    logger.info("Shutting down...")
    update_gateway_health(False)

    # Disconnect Redis
    await redis_client.disconnect()

    # Dispose database connections
    await db_manager.dispose()

    # Log uptime
    uptime = time.time() - startup_time
    logger.info(f"Shutdown complete. Uptime: {uptime:.2f} seconds")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Zero-Trust Runtime Security Gateway for Autonomous AI Agents",
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(MetricsMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],  # Configure appropriately in production
)

# Exception handlers
@app.exception_handler(AgentShieldError)
async def agentshield_exception_handler(request: Request, exc: AgentShieldError):
    """Handle AgentShield-specific exceptions."""
    logger.warning(
        f"AgentShield error: {exc.code} - {exc.message}",
        extra={
            "error_code": exc.code,
            "status_code": exc.status_code,
            "details": exc.details,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.code,
            "message": exc.message,
            "details": exc.details,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle generic exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An internal error occurred",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# Include routers
app.include_router(
    health.router,
    prefix=settings.API_PREFIX,
    tags=["Health"],
)

app.include_router(
    agents.router,
    prefix=settings.API_PREFIX,
    tags=["Agents"],
)

app.include_router(
    tasks.router,
    prefix=settings.API_PREFIX,
    tags=["Tasks"],
)

app.include_router(
    policies.router,
    prefix=settings.API_PREFIX,
    tags=["Policies"],
)

app.include_router(
    capabilities.router,
    prefix=settings.API_PREFIX,
    tags=["Capabilities"],
)

app.include_router(
    gateway.router,
    prefix=settings.API_PREFIX,
    tags=["Gateway"],
)


# Health check endpoints at root level for Docker and Kubernetes health checks
@app.get("/health", tags=["Health"])
async def root_health():
    """Root health check."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }


@app.get("/ready", tags=["Health"])
async def root_ready():
    """Root readiness check."""
    return {"status": "ready"}


@app.get("/live", tags=["Health"])
async def root_live():
    """Root liveness check."""
    return {"status": "alive"}


# Metrics endpoint
@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    return Response(
        content=await get_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs": "/docs" if settings.APP_ENV != "production" else None,
    }


def main():
    """Entry point for running the application."""
    uvicorn.run(
        "agentshield.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.APP_ENV == "development",
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
