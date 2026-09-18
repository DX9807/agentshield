"""Policy API endpoints."""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions import PolicyNotFoundError
from ...infrastructure.database.session import get_db
from ...domain.policy.service import PolicyService
from ...domain.policy.engine import PolicyEngine
from ...schemas.policy import (
    PolicyCreate,
    PolicyUpdate,
    PolicyResponse,
    PolicyListResponse,
    PolicyEvaluationRequest,
    PolicyEvaluationResponse,
)
from ...core.auth import get_current_user, require_admin

router = APIRouter(prefix="/policies", tags=["Policies"])


@router.post("/", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    policy_data: PolicyCreate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """Create a new policy."""
    service = await PolicyService.create(session)
    
    policy = await service.create_policy(
        policy_data,
        created_by=current_user.get("username", "system"),
    )
    
    return PolicyResponse(
        id=policy.id,
        name=policy.name,
        description=policy.description,
        version=policy.version,
        agent_id=policy.agent_id,
        agent_name=policy.agent_name,
        action=policy.action,
        resource_type=policy.resource_type,
        decision=policy.decision,
        priority=policy.priority,
        order=policy.order,
        enabled=policy.enabled,
        conditions=[PolicyCondition(**cond) for cond in policy.conditions] if policy.conditions else None,
        metadata=policy.metadata_json,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
        created_by=policy.created_by,
        updated_by=policy.updated_by,
    )


@router.get("/", response_model=PolicyListResponse)
async def list_policies(
    agent_id: Optional[UUID] = None,
    action: Optional[str] = None,
    decision: Optional[str] = None,
    enabled: Optional[bool] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List policies with filters."""
    service = await PolicyService.create(session)
    
    policies, total = await service.list_policies(
        agent_id=agent_id,
        action=action,
        decision=decision,
        enabled=enabled,
        page=page,
        limit=limit,
    )
    
    items = [
        PolicyResponse(
            id=policy.id,
            name=policy.name,
            description=policy.description,
            version=policy.version,
            agent_id=policy.agent_id,
            agent_name=policy.agent_name,
            action=policy.action,
            resource_type=policy.resource_type,
            decision=policy.decision,
            priority=policy.priority,
            order=policy.order,
            enabled=policy.enabled,
            conditions=[PolicyCondition(**cond) for cond in policy.conditions] if policy.conditions else None,
            metadata=policy.metadata_json,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
            created_by=policy.created_by,
            updated_by=policy.updated_by,
        )
        for policy in policies
    ]
    
    return PolicyListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get policy by ID."""
    service = await PolicyService.create(session)
    
    policy = await service.get_policy_by_id(policy_id)
    if not policy:
        raise PolicyNotFoundError(str(policy_id))
    
    return PolicyResponse(
        id=policy.id,
        name=policy.name,
        description=policy.description,
        version=policy.version,
        agent_id=policy.agent_id,
        agent_name=policy.agent_name,
        action=policy.action,
        resource_type=policy.resource_type,
        decision=policy.decision,
        priority=policy.priority,
        order=policy.order,
        enabled=policy.enabled,
        conditions=[PolicyCondition(**cond) for cond in policy.conditions] if policy.conditions else None,
        metadata=policy.metadata_json,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
        created_by=policy.created_by,
        updated_by=policy.updated_by,
    )


@router.put("/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: UUID,
    update_data: PolicyUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """Update a policy."""
    service = await PolicyService.create(session)
    
    policy = await service.update_policy(
        policy_id,
        update_data,
        updated_by=current_user.get("username", "system"),
    )
    
    return PolicyResponse(
        id=policy.id,
        name=policy.name,
        description=policy.description,
        version=policy.version,
        agent_id=policy.agent_id,
        agent_name=policy.agent_name,
        action=policy.action,
        resource_type=policy.resource_type,
        decision=policy.decision,
        priority=policy.priority,
        order=policy.order,
        enabled=policy.enabled,
        conditions=[PolicyCondition(**cond) for cond in policy.conditions] if policy.conditions else None,
        metadata=policy.metadata_json,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
        created_by=policy.created_by,
        updated_by=policy.updated_by,
    )


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    policy_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """Delete a policy."""
    service = await PolicyService.create(session)
    await service.delete_policy(policy_id)


@router.post("/{policy_id}/enable", response_model=PolicyResponse)
async def enable_policy(
    policy_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """Enable a policy."""
    service = await PolicyService.create(session)
    policy = await service.enable_policy(policy_id)
    
    return PolicyResponse(
        id=policy.id,
        name=policy.name,
        description=policy.description,
        version=policy.version,
        agent_id=policy.agent_id,
        agent_name=policy.agent_name,
        action=policy.action,
        resource_type=policy.resource_type,
        decision=policy.decision,
        priority=policy.priority,
        order=policy.order,
        enabled=policy.enabled,
        conditions=[PolicyCondition(**cond) for cond in policy.conditions] if policy.conditions else None,
        metadata=policy.metadata_json,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
        created_by=policy.created_by,
        updated_by=policy.updated_by,
    )


@router.post("/{policy_id}/disable", response_model=PolicyResponse)
async def disable_policy(
    policy_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """Disable a policy."""
    service = await PolicyService.create(session)
    policy = await service.disable_policy(policy_id)
    
    return PolicyResponse(
        id=policy.id,
        name=policy.name,
        description=policy.description,
        version=policy.version,
        agent_id=policy.agent_id,
        agent_name=policy.agent_name,
        action=policy.action,
        resource_type=policy.resource_type,
        decision=policy.decision,
        priority=policy.priority,
        order=policy.order,
        enabled=policy.enabled,
        conditions=[PolicyCondition(**cond) for cond in policy.conditions] if policy.conditions else None,
        metadata=policy.metadata_json,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
        created_by=policy.created_by,
        updated_by=policy.updated_by,
    )


@router.post("/evaluate", response_model=PolicyEvaluationResponse)
async def evaluate_policy(
    request: PolicyEvaluationRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Evaluate a request against policies."""
    engine = await PolicyEngine.create(session)
    result = await engine.evaluate(request)
    return result