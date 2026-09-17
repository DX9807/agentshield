"""Agent API endpoints."""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions import AgentNotFoundError, AgentInactiveError
from ...infrastructure.database.session import get_db
from ...domain.agent.service import AgentService
from ...domain.agent.models import AgentStatus, AgentEnvironment
from ...schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentWithCredentials,
    AgentListResponse,
    AgentTokenRequest,
    AgentTokenResponse,
)
from ...schemas.capability import AgentCapabilityRequest, AgentCapabilityResponse
from ...core import create_agent_token, get_current_user, require_admin

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("/", response_model=AgentWithCredentials, status_code=status.HTTP_201_CREATED)
async def register_agent(
    agent_data: AgentCreate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),  # Optional auth for v0.1
):
    """Register a new agent.
    
    Creates a new agent with an API key for authentication.
    """
    service = await AgentService.create(session)
    
    # Initialize capabilities if needed
    await service.initialize_predefined_capabilities()
    
    agent, api_key = await service.register_agent(
        agent_data,
        created_by=current_user.get("username", "system") if current_user else "system",
    )
    
    # Get capabilities
    capabilities = await service.get_agent_capabilities(agent.id)
    
    # Build response
    return AgentWithCredentials(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        owner=agent.owner,
        purpose=agent.purpose,
        environment=agent.environment,
        risk_level=agent.risk_level,
        status=agent.status,
        metadata=json.loads(agent.metadata_json) if agent.metadata_json else None,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        created_by=agent.created_by,
        updated_by=agent.updated_by,
        capabilities=[cap["name"] for cap in capabilities],
        credential_prefix="ak_",
        api_key=api_key,
    )


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    status: Optional[AgentStatus] = None,
    environment: Optional[AgentEnvironment] = None,
    owner: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all agents with filtering."""
    service = await AgentService.create(session)
    
    agents, total = await service.list_agents(
        status=status,
        environment=environment,
        owner=owner,
        page=page,
        limit=limit,
    )
    
    # Get capabilities for each agent
    items = []
    for agent in agents:
        capabilities = await service.get_agent_capabilities(agent.id)
        items.append(AgentResponse(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            owner=agent.owner,
            purpose=agent.purpose,
            environment=agent.environment,
            risk_level=agent.risk_level,
            status=agent.status,
            metadata=json.loads(agent.metadata_json) if agent.metadata_json else None,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            created_by=agent.created_by,
            updated_by=agent.updated_by,
            capabilities=[cap["name"] for cap in capabilities],
        ))
    
    return AgentListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get agent by ID."""
    service = await AgentService.create(session)
    
    agent = await service.get_agent_by_id(agent_id)
    if not agent:
        raise AgentNotFoundError(str(agent_id))
    
    capabilities = await service.get_agent_capabilities(agent_id)
    
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        owner=agent.owner,
        purpose=agent.purpose,
        environment=agent.environment,
        risk_level=agent.risk_level,
        status=agent.status,
        metadata=json.loads(agent.metadata_json) if agent.metadata_json else None,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        created_by=agent.created_by,
        updated_by=agent.updated_by,
        capabilities=[cap["name"] for cap in capabilities],
    )


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    update_data: AgentUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update an agent."""
    service = await AgentService.create(session)
    
    agent = await service.update_agent(
        agent_id,
        update_data,
        updated_by=current_user.get("username", "system") if current_user else "system",
    )
    
    capabilities = await service.get_agent_capabilities(agent_id)
    
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        owner=agent.owner,
        purpose=agent.purpose,
        environment=agent.environment,
        risk_level=agent.risk_level,
        status=agent.status,
        metadata=json.loads(agent.metadata_json) if agent.metadata_json else None,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        created_by=agent.created_by,
        updated_by=agent.updated_by,
        capabilities=[cap["name"] for cap in capabilities],
    )


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """Delete (deactivate) an agent."""
    service = await AgentService.create(session)
    await service.delete_agent(agent_id)


@router.post("/{agent_id}/capabilities", response_model=AgentCapabilityResponse)
async def grant_capability_to_agent(
    agent_id: UUID,
    request: AgentCapabilityRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Grant a capability to an agent."""
    service = await AgentService.create(session)
    
    assignment = await service.grant_capability(
        agent_id,
        request.capability_id,
        granted_by=current_user.get("username", "system") if current_user else "system",
        expires_at=request.expires_at,
    )
    
    # Get capability name
    capability = await service._get_capability_by_id(request.capability_id)
    
    return AgentCapabilityResponse(
        id=assignment.id,
        agent_id=assignment.agent_id,
        capability_id=assignment.capability_id,
        capability_name=capability.name if capability else "Unknown",
        granted_at=assignment.granted_at,
        expires_at=assignment.expires_at,
        is_active=assignment.is_active,
        granted_by=assignment.granted_by,
    )


@router.delete("/{agent_id}/capabilities/{capability_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_capability_from_agent(
    agent_id: UUID,
    capability_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Revoke a capability from an agent."""
    service = await AgentService.create(session)
    await service.revoke_capability(agent_id, capability_id)


@router.post("/token", response_model=AgentTokenResponse)
async def authenticate_agent(
    request: AgentTokenRequest,
    session: AsyncSession = Depends(get_db),
):
    """Authenticate an agent and get JWT token."""
    service = await AgentService.create(session)
    
    auth_result = await service.authenticate_agent(
        request.agent_id,
        request.api_key,
    )
    
    agent = auth_result["agent"]
    capabilities = auth_result["capabilities"]
    
    # Create JWT token
    token_data = {
        "agent_id": str(agent.id),
        "agent_name": agent.name,
        "capabilities": [cap["name"] for cap in capabilities],
        "environment": agent.environment.value,
    }
    
    access_token = create_agent_token(token_data)
    
    return AgentTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=60,  # 60 minutes
        agent_id=agent.id,
        agent_name=agent.name,
        capabilities=[cap["name"] for cap in capabilities],
    )