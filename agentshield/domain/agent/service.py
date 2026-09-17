"""Agent identity service layer."""

import json
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions import (
    AgentInactiveError,
    AgentNotFoundError,
    CapabilityNotFoundError,
    InvalidCredentialsError,
)
from ...core.logging import get_logger
from ...infrastructure.database.session import db_manager
from ...schemas.agent import AgentCreate, AgentUpdate
from ...schemas.capability import CapabilityCreate
from .models import (
    Agent,
    AgentCapability,
    AgentCredential,
    AgentEnvironment,
    AgentRiskLevel,
    AgentStatus,
    Capability,
    PredefinedCapabilities,
)

logger = get_logger(__name__)


class AgentService:
    """Service for agent identity management."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @classmethod
    async def create(cls, session: AsyncSession) -> "AgentService":
        """Create a new AgentService instance."""
        return cls(session)

    async def register_agent(
        self,
        agent_data: AgentCreate,
        created_by: str = "system",
    ) -> tuple[Agent, str]:
        """Register a new agent with API key.

        Args:
            agent_data: Agent creation data
            created_by: User who created the agent

        Returns:
            Tuple[Agent, str]: (Agent instance, API key)

        Raises:
            IntegrityError: If agent name already exists
        """
        # Create agent
        agent = Agent(
            name=agent_data.name,
            description=agent_data.description,
            owner=agent_data.owner,
            purpose=agent_data.purpose,
            environment=agent_data.environment,
            risk_level=agent_data.risk_level,
            status=AgentStatus.PENDING_APPROVAL
            if agent_data.risk_level in [AgentRiskLevel.HIGH, AgentRiskLevel.CRITICAL]
            else AgentStatus.ACTIVE,
            metadata_json=json.dumps(agent_data.metadata) if agent_data.metadata else None,
            created_by=created_by,
            updated_by=created_by,
        )

        self.session.add(agent)
        await self.session.flush()

        # Generate API key
        api_key, hashed_key, prefix = AgentCredential.generate_api_key()

        credential = AgentCredential(
            agent_id=agent.id,
            credential_type="api_key",
            credential_hash=hashed_key,
            credential_prefix=prefix,
            expires_at=datetime.utcnow() + timedelta(days=365),  # 1 year expiration
        )

        self.session.add(credential)
        await self.session.flush()

        # Assign capabilities if provided
        if agent_data.capabilities:
            for cap_name in agent_data.capabilities:
                capability = await self._get_capability_by_name(cap_name)
                if capability:
                    agent_cap = AgentCapability(
                        agent_id=agent.id,
                        capability_id=capability.id,
                        granted_by=created_by,
                    )
                    self.session.add(agent_cap)
            await self.session.flush()

        # Commit transaction
        await self.session.commit()
        await self.session.refresh(agent)

        logger.info(
            f"Agent registered: {agent.name} ({agent.id})",
            extra={"agent_id": str(agent.id), "created_by": created_by},
        )

        return agent, api_key

    async def authenticate_agent(self, agent_id: UUID, api_key: str) -> dict[str, Any]:
        """Authenticate an agent using API key.

        Args:
            agent_id: Agent UUID
            api_key: API key string

        Returns:
            Dict with authentication result

        Raises:
            AgentNotFoundError: If agent not found
            AgentInactiveError: If agent is not active
            InvalidCredentialsError: If API key is invalid
        """
        # Get agent
        agent = await self.get_agent_by_id(agent_id)
        if not agent:
            raise AgentNotFoundError(str(agent_id))

        # Check agent status
        if not agent.is_active:
            raise AgentInactiveError(str(agent_id))

        # Find active credential
        credential = await self._get_active_credential(agent_id)
        if not credential:
            raise InvalidCredentialsError()

        # Verify API key
        if not credential.verify_api_key(api_key):
            raise InvalidCredentialsError()

        # Update last used timestamp
        credential.last_used_at = datetime.utcnow()
        await self.session.commit()

        # Get agent capabilities
        capabilities = await self.get_agent_capabilities(agent_id)

        logger.info(
            f"Agent authenticated: {agent.name} ({agent.id})", extra={"agent_id": str(agent_id)}
        )

        return {
            "agent": agent,
            "capabilities": capabilities,
        }

    async def get_agent_by_id(self, agent_id: UUID) -> Agent | None:
        """Get agent by ID."""
        query = select(Agent).where(Agent.id == agent_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_agent_by_name(self, name: str) -> Agent | None:
        """Get agent by name."""
        query = select(Agent).where(Agent.name == name)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_agents(
        self,
        status: AgentStatus | None = None,
        environment: AgentEnvironment | None = None,
        owner: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Agent], int]:
        """List agents with filters."""
        query = select(Agent)
        count_query = select(func.count()).select_from(Agent)

        # Apply filters
        if status:
            query = query.where(Agent.status == status)
            count_query = count_query.where(Agent.status == status)

        if environment:
            query = query.where(Agent.environment == environment)
            count_query = count_query.where(Agent.environment == environment)

        if owner:
            query = query.where(Agent.owner == owner)
            count_query = count_query.where(Agent.owner == owner)

        # Pagination
        offset = (page - 1) * limit
        query = query.order_by(Agent.created_at.desc()).offset(offset).limit(limit)

        # Execute queries
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.session.execute(query)
        agents = result.scalars().all()

        return list(agents), total

    async def update_agent(
        self,
        agent_id: UUID,
        update_data: AgentUpdate,
        updated_by: str = "system",
    ) -> Agent:
        """Update an agent."""
        agent = await self.get_agent_by_id(agent_id)
        if not agent:
            raise AgentNotFoundError(str(agent_id))

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            if field == "metadata" and value is not None:
                agent.metadata_json = json.dumps(value)
            elif hasattr(agent, field):
                setattr(agent, field, value)

        agent.updated_by = updated_by
        await self.session.commit()
        await self.session.refresh(agent)

        logger.info(
            f"Agent updated: {agent.name} ({agent.id})",
            extra={"agent_id": str(agent_id), "updated_by": updated_by},
        )

        return agent

    async def delete_agent(self, agent_id: UUID) -> bool:
        """Soft delete an agent (set to inactive)."""
        agent = await self.get_agent_by_id(agent_id)
        if not agent:
            raise AgentNotFoundError(str(agent_id))

        agent.status = AgentStatus.INACTIVE
        await self.session.commit()

        logger.info(
            f"Agent deactivated: {agent.name} ({agent.id})", extra={"agent_id": str(agent_id)}
        )

        return True

    async def get_agent_capabilities(self, agent_id: UUID) -> list[dict[str, Any]]:
        """Get all capabilities for an agent."""
        query = (
            select(Capability, AgentCapability)
            .join(AgentCapability, Capability.id == AgentCapability.capability_id)
            .where(
                and_(
                    AgentCapability.agent_id == agent_id,
                    AgentCapability.is_active.is_(True),
                    or_(
                        AgentCapability.expires_at.is_(None),
                        AgentCapability.expires_at > func.now(),
                    ),
                )
            )
        )

        result = await self.session.execute(query)
        rows = result.all()

        capabilities = []
        for capability, assignment in rows:
            capabilities.append(
                {
                    "id": capability.id,
                    "name": capability.name,
                    "description": capability.description,
                    "category": capability.category,
                    "is_sensitive": capability.is_sensitive,
                    "requires_approval": capability.requires_approval,
                    "granted_at": assignment.granted_at,
                    "expires_at": assignment.expires_at,
                    "is_active": assignment.is_active,
                }
            )

        return capabilities

    async def grant_capability(
        self,
        agent_id: UUID,
        capability_id: UUID,
        granted_by: str = "system",
        expires_at: datetime | None = None,
    ) -> AgentCapability:
        """Grant a capability to an agent."""
        # Check if agent exists
        agent = await self.get_agent_by_id(agent_id)
        if not agent:
            raise AgentNotFoundError(str(agent_id))

        # Check if capability exists
        capability = await self._get_capability_by_id(capability_id)
        if not capability:
            raise CapabilityNotFoundError(str(capability_id))

        # Check if already assigned
        existing = await self._get_agent_capability(agent_id, capability_id)
        if existing:
            # Reactivate if expired/inactive
            existing.is_active = True
            existing.expires_at = expires_at
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        # Create new assignment
        assignment = AgentCapability(
            agent_id=agent_id,
            capability_id=capability_id,
            granted_by=granted_by,
            expires_at=expires_at,
        )

        self.session.add(assignment)
        await self.session.commit()
        await self.session.refresh(assignment)

        logger.info(
            f"Capability granted: {capability.name} to agent {agent.name}",
            extra={
                "agent_id": str(agent_id),
                "capability_id": str(capability_id),
                "granted_by": granted_by,
            },
        )

        return assignment

    async def revoke_capability(
        self,
        agent_id: UUID,
        capability_id: UUID,
    ) -> bool:
        """Revoke a capability from an agent."""
        assignment = await self._get_agent_capability(agent_id, capability_id)
        if not assignment:
            return False

        assignment.is_active = False
        await self.session.commit()

        logger.info(
            "Capability revoked from agent",
            extra={
                "agent_id": str(agent_id),
                "capability_id": str(capability_id),
            },
        )

        return True

    async def create_capability(self, capability_data: CapabilityCreate) -> Capability:
        """Create a new capability."""
        capability = Capability(
            name=capability_data.name,
            description=capability_data.description,
            category=capability_data.category,
            is_sensitive=capability_data.is_sensitive,
            requires_approval=capability_data.requires_approval,
        )

        self.session.add(capability)
        await self.session.commit()
        await self.session.refresh(capability)

        logger.info(f"Capability created: {capability.name}")
        return capability

    async def list_capabilities(
        self,
        category: str | None = None,
    ) -> tuple[list[Capability], int]:
        """List capabilities."""
        query = select(Capability)
        count_query = select(func.count()).select_from(Capability)

        if category:
            query = query.where(Capability.category == category)
            count_query = count_query.where(Capability.category == category)

        query = query.order_by(Capability.name)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.session.execute(query)
        capabilities = result.scalars().all()

        return list(capabilities), total

    async def get_capability_by_name(self, name: str) -> Capability | None:
        """Get capability by name."""
        query = select(Capability).where(Capability.name == name)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    _get_capability_by_name = get_capability_by_name

    async def get_capability_by_id(self, capability_id: UUID) -> Capability | None:
        """Get capability by ID."""
        query = select(Capability).where(Capability.id == capability_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    _get_capability_by_id = get_capability_by_id

    async def _get_active_credential(self, agent_id: UUID) -> AgentCredential | None:
        """Get the active credential for an agent."""
        query = (
            select(AgentCredential)
            .where(
                and_(
                    AgentCredential.agent_id == agent_id,
                    AgentCredential.is_active.is_(True),
                    or_(
                        AgentCredential.expires_at.is_(None),
                        AgentCredential.expires_at > func.now(),
                    ),
                )
            )
            .order_by(AgentCredential.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _get_agent_capability(
        self,
        agent_id: UUID,
        capability_id: UUID,
    ) -> AgentCapability | None:
        """Get agent capability assignment."""
        query = select(AgentCapability).where(
            and_(
                AgentCapability.agent_id == agent_id,
                AgentCapability.capability_id == capability_id,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def initialize_predefined_capabilities(self) -> None:
        """Initialize predefined capabilities if they don't exist."""
        for cap_name in PredefinedCapabilities.get_all():
            existing = await self.get_capability_by_name(cap_name)
            if not existing:
                # Determine category
                if cap_name.startswith("read_"):
                    category = "read"
                elif cap_name.startswith("write_"):
                    category = "write"
                elif cap_name.startswith("delete_"):
                    category = "delete"
                elif cap_name.startswith("create_"):
                    category = "create"
                elif cap_name.startswith("access_"):
                    category = "access"
                else:
                    category = "general"

                # Determine if sensitive
                is_sensitive = cap_name in PredefinedCapabilities.get_sensitive()

                capability = Capability(
                    name=cap_name,
                    description=f"Capability to {cap_name.replace('_', ' ')}",
                    category=category,
                    is_sensitive=is_sensitive,
                    requires_approval=is_sensitive,
                )
                self.session.add(capability)

        await self.session.commit()
        logger.info("Predefined capabilities initialized")


# Helper function for dependency injection
async def get_agent_service(
    session: AsyncSession = None,
) -> AgentService:
    """Get an AgentService instance."""
    if session is None:
        async with db_manager.get_session() as db_session:
            return await AgentService.create(db_session)
    return await AgentService.create(session)
