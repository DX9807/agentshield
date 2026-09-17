"""Capability API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions import CapabilityNotFoundError
from ...infrastructure.database.session import get_db
from ...domain.agent.service import AgentService
from ...schemas.capability import (
    CapabilityCreate,
    CapabilityResponse,
    CapabilityListResponse,
)
from ...core.auth import get_current_user

router = APIRouter(prefix="/capabilities", tags=["Capabilities"])


@router.post("/", response_model=CapabilityResponse, status_code=status.HTTP_201_CREATED)
async def create_capability(
    capability_data: CapabilityCreate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a new capability."""
    service = await AgentService.create(session)
    capability = await service.create_capability(capability_data)
    
    return CapabilityResponse(
        id=capability.id,
        name=capability.name,
        description=capability.description,
        category=capability.category,
        is_sensitive=capability.is_sensitive,
        requires_approval=capability.requires_approval,
        created_at=capability.created_at,
    )


@router.get("/", response_model=CapabilityListResponse)
async def list_capabilities(
    category: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all capabilities."""
    service = await AgentService.create(session)
    capabilities, total = await service.list_capabilities(category=category)
    
    items = [
        CapabilityResponse(
            id=cap.id,
            name=cap.name,
            description=cap.description,
            category=cap.category,
            is_sensitive=cap.is_sensitive,
            requires_approval=cap.requires_approval,
            created_at=cap.created_at,
        )
        for cap in capabilities
    ]
    
    return CapabilityListResponse(items=items, total=total)


@router.get("/{capability_id}", response_model=CapabilityResponse)
async def get_capability(
    capability_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get capability by ID."""
    service = await AgentService.create(session)
    capability = await service._get_capability_by_id(capability_id)
    
    if not capability:
        raise CapabilityNotFoundError(str(capability_id))
    
    return CapabilityResponse(
        id=capability.id,
        name=capability.name,
        description=capability.description,
        category=capability.category,
        is_sensitive=capability.is_sensitive,
        requires_approval=capability.requires_approval,
        created_at=capability.created_at,
    )