"""Gateway API endpoints."""

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.auth import get_current_user
from ...core.config import settings
from ...domain.gateway.service import GatewayService
from ...infrastructure.database.session import get_db
from ...schemas.gateway import (
    GatewayBatchRequest,
    GatewayBatchResponse,
    GatewayForwardRequest,
    GatewayResponse,
)

router = APIRouter(prefix="/gateway", tags=["Gateway"])


@router.post("/forward", response_model=GatewayResponse)
async def forward_request(
    gateway_request: GatewayForwardRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> GatewayResponse:
    """Forward a request through the gateway."""
    service = await GatewayService.create(session)
    request_id = str(uuid4())
    response = await service.process_request(
        gateway_request,
        request_id,
    )
    return response


@router.post("/batch", response_model=GatewayBatchResponse)
async def forward_batch(
    batch_request: GatewayBatchRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> GatewayBatchResponse:
    """Forward multiple requests through the gateway."""
    service = await GatewayService.create(session)
    responses = []
    allowed = 0
    blocked = 0
    require_approval = 0

    for req in batch_request.requests:
        request_id = str(uuid4())
        response = await service.process_request(req, request_id)
        responses.append(response)

        if response.decision == "ALLOW":
            allowed += 1
        elif response.decision == "BLOCK":
            blocked += 1
        elif response.decision == "REQUIRE_APPROVAL":
            require_approval += 1

    return GatewayBatchResponse(
        responses=responses,
        total=len(responses),
        allowed=allowed,
        blocked=blocked,
        require_approval=require_approval,
    )


@router.get("/health")
async def gateway_health() -> dict[str, Any]:
    """Gateway health check."""
    return {
        "status": "healthy",
        "service": "gateway",
        "version": settings.APP_VERSION,
        "rate_limit_enabled": settings.RATE_LIMIT_ENABLED,
        "max_body_size": settings.GATEWAY_MAX_BODY_SIZE,
        "request_timeout": settings.GATEWAY_REQUEST_TIMEOUT,
    }


@router.get("/stats")
async def gateway_stats(
    session: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Get gateway statistics."""
    return {
        "total_requests": 0,
        "allowed_requests": 0,
        "blocked_requests": 0,
        "approval_requests": 0,
        "average_latency_ms": 0,
    }
