"""Task API endpoints."""

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions import TaskNotFoundError, TaskExpiredError
from ...infrastructure.database.session import get_db
from ...domain.task.service import TaskService
from ...domain.task.models import TaskStatus
from ...schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse,
    TaskCompleteRequest,
    TaskExtendRequest,
)
from ...core.auth import get_current_user, get_agent_from_token

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a new task."""
    service = await TaskService.create(session)
    
    task = await service.create_task(
        task_data,
        created_by=current_user.get("username", "system") if current_user else "system",
    )
    
    # Get capabilities
    capabilities = await service.get_task_capabilities(task.id)
    
    return TaskResponse(
        id=task.id,
        agent_id=task.agent_id,
        user_id=task.user_id,
        external_id=task.external_id,
        intent_type=task.intent_type,
        intent_data=task.intent_data,
        context=task.context,
        status=task.status,
        priority=task.priority,
        expires_at=task.expires_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
        created_by=task.created_by,
        updated_by=task.updated_by,
        capabilities=[cap["name"] for cap in capabilities],
        is_active=task.is_active,
    )


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    agent_id: Optional[UUID] = None,
    status: Optional[TaskStatus] = None,
    intent_type: Optional[str] = None,
    user_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List tasks with filters."""
    service = await TaskService.create(session)
    
    tasks, total = await service.list_tasks(
        agent_id=agent_id,
        status=status,
        intent_type=intent_type,
        user_id=user_id,
        page=page,
        limit=limit,
    )
    
    items = []
    for task in tasks:
        capabilities = await service.get_task_capabilities(task.id)
        items.append(TaskResponse(
            id=task.id,
            agent_id=task.agent_id,
            user_id=task.user_id,
            external_id=task.external_id,
            intent_type=task.intent_type,
            intent_data=task.intent_data,
            context=task.context,
            status=task.status,
            priority=task.priority,
            expires_at=task.expires_at,
            created_at=task.created_at,
            updated_at=task.updated_at,
            completed_at=task.completed_at,
            created_by=task.created_by,
            updated_by=task.updated_by,
            capabilities=[cap["name"] for cap in capabilities],
            is_active=task.is_active,
        ))
    
    return TaskListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    include_expired: bool = False,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get task by ID."""
    service = await TaskService.create(session)
    
    task = await service.get_task_by_id(task_id, include_expired=include_expired)
    if not task:
        raise TaskNotFoundError(str(task_id))
    
    capabilities = await service.get_task_capabilities(task_id)
    
    return TaskResponse(
        id=task.id,
        agent_id=task.agent_id,
        user_id=task.user_id,
        external_id=task.external_id,
        intent_type=task.intent_type,
        intent_data=task.intent_data,
        context=task.context,
        status=task.status,
        priority=task.priority,
        expires_at=task.expires_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
        created_by=task.created_by,
        updated_by=task.updated_by,
        capabilities=[cap["name"] for cap in capabilities],
        is_active=task.is_active,
    )


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    update_data: TaskUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update a task."""
    service = await TaskService.create(session)
    
    task = await service.update_task(
        task_id,
        update_data,
        updated_by=current_user.get("username", "system") if current_user else "system",
    )
    
    capabilities = await service.get_task_capabilities(task_id)
    
    return TaskResponse(
        id=task.id,
        agent_id=task.agent_id,
        user_id=task.user_id,
        external_id=task.external_id,
        intent_type=task.intent_type,
        intent_data=task.intent_data,
        context=task.context,
        status=task.status,
        priority=task.priority,
        expires_at=task.expires_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
        created_by=task.created_by,
        updated_by=task.updated_by,
        capabilities=[cap["name"] for cap in capabilities],
        is_active=task.is_active,
    )


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: UUID,
    request: TaskCompleteRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Complete a task (revoke permissions)."""
    service = await TaskService.create(session)
    
    task = await service.complete_task(
        task_id,
        result_data=request.result_data,
        completed_by=current_user.get("username", "system") if current_user else "system",
    )
    
    capabilities = await service.get_task_capabilities(task_id)
    
    return TaskResponse(
        id=task.id,
        agent_id=task.agent_id,
        user_id=task.user_id,
        external_id=task.external_id,
        intent_type=task.intent_type,
        intent_data=task.intent_data,
        context=task.context,
        status=task.status,
        priority=task.priority,
        expires_at=task.expires_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
        created_by=task.created_by,
        updated_by=task.updated_by,
        capabilities=[cap["name"] for cap in capabilities],
        is_active=task.is_active,
    )


@router.post("/{task_id}/extend", response_model=TaskResponse)
async def extend_task(
    task_id: UUID,
    request: TaskExtendRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Extend a task's expiration."""
    service = await TaskService.create(session)
    
    task = await service.extend_task(
        task_id,
        request.additional_minutes,
        reason=request.reason,
        extended_by=current_user.get("username", "system") if current_user else "system",
    )
    
    capabilities = await service.get_task_capabilities(task_id)
    
    return TaskResponse(
        id=task.id,
        agent_id=task.agent_id,
        user_id=task.user_id,
        external_id=task.external_id,
        intent_type=task.intent_type,
        intent_data=task.intent_data,
        context=task.context,
        status=task.status,
        priority=task.priority,
        expires_at=task.expires_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
        created_by=task.created_by,
        updated_by=task.updated_by,
        capabilities=[cap["name"] for cap in capabilities],
        is_active=task.is_active,
    )


@router.post("/{task_id}/revoke", response_model=TaskResponse)
async def revoke_task(
    task_id: UUID,
    reason: Optional[str] = "Revoked by admin",
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Force revoke a task."""
    service = await TaskService.create(session)
    
    task = await service.revoke_task(
        task_id,
        reason=reason,
        revoked_by=current_user.get("username", "system") if current_user else "system",
    )
    
    capabilities = await service.get_task_capabilities(task_id)
    
    return TaskResponse(
        id=task.id,
        agent_id=task.agent_id,
        user_id=task.user_id,
        external_id=task.external_id,
        intent_type=task.intent_type,
        intent_data=task.intent_data,
        context=task.context,
        status=task.status,
        priority=task.priority,
        expires_at=task.expires_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
        created_by=task.created_by,
        updated_by=task.updated_by,
        capabilities=[cap["name"] for cap in capabilities],
        is_active=task.is_active,
    )


@router.get("/{task_id}/capabilities")
async def get_task_capabilities(
    task_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get capabilities for a task."""
    service = await TaskService.create(session)
    
    # Verify task exists
    task = await service.get_task_by_id(task_id)
    if not task:
        raise TaskNotFoundError(str(task_id))
    
    capabilities = await service.get_task_capabilities(task_id)
    return {"capabilities": capabilities}