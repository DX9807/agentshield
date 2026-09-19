"""Policy management service layer."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions import PolicyNotFoundError
from ...core.logging import get_logger
from ...infrastructure.cache.redis_client import redis_client
from ...schemas.policy import PolicyCreate, PolicyUpdate
from .models import Policy, PolicyViolation

logger = get_logger(__name__)


class PolicyService:
    """Service for policy management."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @classmethod
    async def create(cls, session: AsyncSession) -> "PolicyService":
        """Create a new PolicyService instance."""
        return cls(session)

    async def create_policy(
        self,
        policy_data: PolicyCreate,
        created_by: str = "system",
    ) -> Policy:
        """Create a new policy."""
        policy = Policy(
            name=policy_data.name,
            description=policy_data.description,
            version=policy_data.version,
            agent_id=policy_data.agent_id,
            agent_name=policy_data.agent_name,
            action=policy_data.action,
            resource_type=policy_data.resource_type,
            decision=policy_data.decision.value,
            priority=policy_data.priority,
            order=policy_data.order,
            enabled=policy_data.enabled,
            conditions=[cond.model_dump() for cond in policy_data.conditions]
            if policy_data.conditions
            else None,
            metadata_json=policy_data.metadata,
            created_by=created_by,
            updated_by=created_by,
        )

        self.session.add(policy)
        await self.session.commit()
        await self.session.refresh(policy)

        # Clear policy cache
        await self._clear_policy_cache(policy)

        logger.info(
            f"Policy created: {policy.name} ({policy.id})",
            extra={"policy_id": str(policy.id), "created_by": created_by},
        )

        return policy

    async def get_policy_by_id(self, policy_id: UUID) -> Policy | None:
        """Get policy by ID."""
        query = select(Policy).where(Policy.id == policy_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_policy_by_name(self, name: str) -> Policy | None:
        """Get policy by name."""
        query = select(Policy).where(Policy.name == name)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_policies(
        self,
        agent_id: UUID | None = None,
        action: str | None = None,
        decision: str | None = None,
        enabled: bool | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Policy], int]:
        """List policies with filters."""
        query = select(Policy)
        count_query = select(func.count()).select_from(Policy)

        # Apply filters
        if agent_id:
            query = query.where(Policy.agent_id == agent_id)
            count_query = count_query.where(Policy.agent_id == agent_id)

        if action:
            query = query.where(Policy.action == action)
            count_query = count_query.where(Policy.action == action)

        if decision:
            query = query.where(Policy.decision == decision)
            count_query = count_query.where(Policy.decision == decision)

        if enabled is not None:
            query = query.where(Policy.enabled == enabled)
            count_query = count_query.where(Policy.enabled == enabled)

        # Pagination
        offset = (page - 1) * limit
        query = (
            query.order_by(Policy.priority.asc(), Policy.order.asc()).offset(offset).limit(limit)
        )

        # Execute
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.session.execute(query)
        policies = result.scalars().all()

        return list(policies), total

    async def update_policy(
        self,
        policy_id: UUID,
        update_data: PolicyUpdate,
        updated_by: str = "system",
    ) -> Policy:
        """Update a policy."""
        policy = await self.get_policy_by_id(policy_id)
        if not policy:
            raise PolicyNotFoundError(str(policy_id))

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            if field == "conditions" and value is not None:
                policy.conditions = [cond.model_dump() for cond in value]
            elif field == "metadata" and value is not None:
                policy.metadata_json = value
            elif field == "decision" and value is not None:
                policy.decision = value.value
            elif hasattr(policy, field):
                setattr(policy, field, value)

        policy.updated_by = updated_by
        await self.session.commit()
        await self.session.refresh(policy)

        # Clear policy cache
        await self._clear_policy_cache(policy)

        logger.info(
            f"Policy updated: {policy.name} ({policy.id})",
            extra={"policy_id": str(policy_id), "updated_by": updated_by},
        )

        return policy

    async def delete_policy(self, policy_id: UUID) -> bool:
        """Delete a policy."""
        policy = await self.get_policy_by_id(policy_id)
        if not policy:
            raise PolicyNotFoundError(str(policy_id))

        await self.session.delete(policy)
        await self.session.commit()

        # Clear policy cache
        await self._clear_policy_cache(policy)

        logger.info(
            f"Policy deleted: {policy.name} ({policy.id})", extra={"policy_id": str(policy_id)}
        )

        return True

    async def enable_policy(self, policy_id: UUID) -> Policy:
        """Enable a policy."""
        policy = await self.get_policy_by_id(policy_id)
        if not policy:
            raise PolicyNotFoundError(str(policy_id))

        policy.enabled = True
        await self.session.commit()
        await self.session.refresh(policy)

        # Clear policy cache
        await self._clear_policy_cache(policy)

        logger.info(
            f"Policy enabled: {policy.name} ({policy.id})", extra={"policy_id": str(policy_id)}
        )

        return policy

    async def disable_policy(self, policy_id: UUID) -> Policy:
        """Disable a policy."""
        policy = await self.get_policy_by_id(policy_id)
        if not policy:
            raise PolicyNotFoundError(str(policy_id))

        policy.enabled = False
        await self.session.commit()
        await self.session.refresh(policy)

        # Clear policy cache
        await self._clear_policy_cache(policy)

        logger.info(
            f"Policy disabled: {policy.name} ({policy.id})", extra={"policy_id": str(policy_id)}
        )

        return policy

    async def _clear_policy_cache(self, policy: Policy) -> None:
        """Clear policy cache entries."""
        try:
            keys_to_delete = [f"policy:{policy.id}"]
            if policy.agent_id:
                keys_to_delete.append(f"policies:agent:{policy.agent_id}:action:{policy.action}")
            await redis_client.delete(*keys_to_delete)
            await redis_client.delete("policies:all")
        except Exception:
            pass

    async def log_violation(
        self,
        agent_id: UUID,
        action: str,
        violation_type: str,
        severity: str = "medium",
        description: str | None = None,
        context: dict | None = None,
    ) -> None:
        """Log a policy violation."""
        violation = PolicyViolation(
            agent_id=agent_id,
            action=action,
            violation_type=violation_type,
            severity=severity,
            description=description,
            context_snapshot=context,
        )

        self.session.add(violation)
        await self.session.commit()

        logger.warning(
            f"Policy violation: {violation_type} by agent {agent_id}",
            extra={
                "agent_id": str(agent_id),
                "action": action,
                "violation_type": violation_type,
                "severity": severity,
            },
        )
