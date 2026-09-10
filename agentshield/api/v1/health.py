"""Health check endpoints."""

from fastapi import APIRouter, Depends, status
from typing import Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ...infrastructure.database.session import get_db
from ...infrastructure.cache.redis_client import redis_client
from ...core.config import settings

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """Basic health check."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }


@router.get("/health/detailed", tags=["Health"])
async def detailed_health_check(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Detailed health check with component status."""
    statuses = {
        "database": False,
        "redis": False,
        "service": True,
    }
    
    # Check database
    try:
        await db.execute(text("SELECT 1"))
        statuses["database"] = True
    except Exception as e:
        statuses["database_error"] = str(e)
    
    # Check Redis
    try:
        await redis_client.connect()
        await redis_client.ping()
        statuses["redis"] = True
    except Exception as e:
        statuses["redis_error"] = str(e)
    
    # Determine overall status
    all_healthy = all(statuses.get(k) for k in ["database", "redis"])
    
    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "components": statuses,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/ready", tags=["Health"])
async def readiness_check() -> Dict[str, Any]:
    """Readiness check."""
    return {"status": "ready"}


@router.get("/live", tags=["Health"])
async def liveness_check() -> Dict[str, Any]:
    """Liveness check."""
    return {"status": "alive"}