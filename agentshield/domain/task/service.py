"""Task management service layer."""

from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from sqlalchemy.exc import IntegrityError

from ...core.exceptions import (
    TaskNotFoundError,
    TaskExpiredError,
    AgentNotFoundError,
    CapabilityNotFoundError,
)
from ...core.logging import get_logger
from ...infrastructure.cache.redis_client import redis_client
from ..agent.service import AgentService
from ..agent.models import Agent, Capability
from .models import Task, TaskStatus, TaskCapability, TaskPriority
from ...schemas.task import TaskCreate, TaskUpdate
from ...core.config import settings

logger = get_logger(__name__)


class TaskService:
    """Service for task management."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.agent_service = None
    
    @classmethod
    async def create(cls, session: AsyncSession) -> "TaskService":
        """Create a new TaskService instance."""
        service = cls(session)
        service.agent_service = await AgentService.create(session)
        return service
    
    async def create_task(
        self,
        task_data: TaskCreate,
        created_by: str = "system",
    ) -> Task:
        """Create a new task with temporary permissions."""
        
        # Verify agent exists and is active
        agent = await self.agent_service.get_agent_by_id(task_data.agent_id)
        if not agent:
            raise AgentNotFoundError(str(task_data.agent_id))
        
        if not agent.is_active:
            raise AgentInactiveError(str(task_data.agent_id))
        
        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(minutes=task_data.expires_in_minutes)
        
        # Create task
        task = Task(
            agent_id=task_data.agent_id,
            user_id=task_data.user_id,
            external_id=task_data.external_id,
            intent_type=task_data.intent_type,
            intent_data=task_data.intent_data,
            context=task_data.context,
            priority=task_data.priority,
            expires_at=expires_at,
            status=TaskStatus.ACTIVE,
            created_by=created_by,
            updated_by=created_by,
        )
        
        self.session.add(task)
        await self.session.flush()
        
        # Assign capabilities
        if task_data.capabilities:
            for cap_name in task_data.capabilities:
                # Get capability by name
                capability = await self.agent_service.get_capability_by_name(cap_name)
                if not capability:
                    raise CapabilityNotFoundError(f"Capability not found: {cap_name}")
                
                # Check if agent has this capability
                agent_caps = await self.agent_service.get_agent_capabilities(task_data.agent_id)
                agent_cap_names = [cap["name"] for cap in agent_caps]
                
                if cap_name not in agent_cap_names:
                    logger.warning(
                        f"Agent lacks capability {cap_name} but task requesting it",
                        extra={
                            "agent_id": str(task_data.agent_id),
                            "task_id": str(task.id),
                            "capability": cap_name,
                        }
                    )
                    # Still assign it for the task (agent permissions + task permissions)
                
                task_cap = TaskCapability(
                    task_id=task.id,
                    capability_id=capability.id,
                )
                self.session.add(task_cap)
            
            await self.session.flush()
        
        # Cache task context in Redis for fast lookup
        await self._cache_task(task)
        
        await self.session.commit()
        await self.session.refresh(task)
        
        logger.info(
            f"Task created: {task.id} for agent {task.agent_id}",
            extra={
                "task_id": str(task.id),
                "agent_id": str(task.agent_id),
                "intent_type": task.intent_type,
                "created_by": created_by,
            }
        )
        
        return task
    
    async def get_task_by_id(
        self,
        task_id: UUID,
        include_expired: bool = False,
    ) -> Optional[Task]:
        """Get task by ID."""
        query = select(Task).where(Task.id == task_id)
        
        if not include_expired:
            query = query.where(
                and_(
                    Task.status == TaskStatus.ACTIVE,
                    Task.expires_at > datetime.utcnow(),
                )
            )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_task_by_external_id(
        self,
        external_id: str,
        include_expired: bool = False,
    ) -> Optional[Task]:
        """Get task by external ID."""
        query = select(Task).where(Task.external_id == external_id)
        
        if not include_expired:
            query = query.where(
                and_(
                    Task.status == TaskStatus.ACTIVE,
                    Task.expires_at > datetime.utcnow(),
                )
            )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def list_tasks(
        self,
        agent_id: Optional[UUID] = None,
        status: Optional[TaskStatus] = None,
        intent_type: Optional[str] = None,
        user_id: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[Task], int]:
        """List tasks with filters."""
        query = select(Task)
        count_query = select(func.count()).select_from(Task)
        
        # Apply filters
        if agent_id:
            query = query.where(Task.agent_id == agent_id)
            count_query = count_query.where(Task.agent_id == agent_id)
        
        if status:
            query = query.where(Task.status == status)
            count_query = count_query.where(Task.status == status)
        
        if intent_type:
            query = query.where(Task.intent_type == intent_type)
            count_query = count_query.where(Task.intent_type == intent_type)
        
        if user_id:
            query = query.where(Task.user_id == user_id)
            count_query = count_query.where(Task.user_id == user_id)
        
        # Pagination
        offset = (page - 1) * limit
        query = query.order_by(Task.created_at.desc()).offset(offset).limit(limit)
        
        # Execute
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        result = await self.session.execute(query)
        tasks = result.scalars().all()
        
        return list(tasks), total
    
    async def update_task(
        self,
        task_id: UUID,
        update_data: TaskUpdate,
        updated_by: str = "system",
    ) -> Task:
        """Update a task."""
        task = await self.get_task_by_id(task_id, include_expired=True)
        if not task:
            raise TaskNotFoundError(str(task_id))
        
        if not task.is_active:
            raise TaskExpiredError(str(task_id))
        
        # Update fields
        if update_data.priority is not None:
            task.priority = update_data.priority
        
        if update_data.context is not None:
            task.context = update_data.context
        
        if update_data.expires_in_minutes is not None:
            task.expires_at = datetime.utcnow() + timedelta(minutes=update_data.expires_in_minutes)
        
        task.updated_by = updated_by
        await self.session.commit()
        await self.session.refresh(task)
        
        # Update cache
        await self._cache_task(task)
        
        logger.info(
            f"Task updated: {task.id}",
            extra={"task_id": str(task_id), "updated_by": updated_by}
        )
        
        return task
    
    async def complete_task(
        self,
        task_id: UUID,
        result_data: Optional[Dict[str, Any]] = None,
        completed_by: str = "system",
    ) -> Task:
        """Complete a task (revoke permissions)."""
        task = await self.get_task_by_id(task_id, include_expired=True)
        if not task:
            raise TaskNotFoundError(str(task_id))
        
        # Mark as completed
        task.complete()
        task.updated_by = completed_by
        
        # Add result data to context
        if result_data:
            if task.context is None:
                task.context = {}
            task.context["result"] = result_data
        
        await self.session.commit()
        await self.session.refresh(task)
        
        # Remove from cache
        await self._remove_task_cache(task_id)
        
        logger.info(
            f"Task completed: {task.id}",
            extra={
                "task_id": str(task_id),
                "completed_by": completed_by,
                "result": result_data,
            }
        )
        
        return task
    
    async def revoke_task(
        self,
        task_id: UUID,
        reason: str = "Revoked by admin",
        revoked_by: str = "system",
    ) -> Task:
        """Force revoke a task."""
        task = await self.get_task_by_id(task_id, include_expired=True)
        if not task:
            raise TaskNotFoundError(str(task_id))
        
        task.revoke()
        task.updated_by = revoked_by
        
        # Add revocation reason to context
        if task.context is None:
            task.context = {}
        task.context["revocation_reason"] = reason
        
        await self.session.commit()
        await self.session.refresh(task)
        
        # Remove from cache
        await self._remove_task_cache(task_id)
        
        logger.warning(
            f"Task revoked: {task.id} - {reason}",
            extra={
                "task_id": str(task_id),
                "revoked_by": revoked_by,
                "reason": reason,
            }
        )
        
        return task
    
    async def extend_task(
        self,
        task_id: UUID,
        additional_minutes: int,
        reason: Optional[str] = None,
        extended_by: str = "system",
    ) -> Task:
        """Extend task expiration."""
        task = await self.get_task_by_id(task_id, include_expired=True)
        if not task:
            raise TaskNotFoundError(str(task_id))
        
        if task.status == TaskStatus.COMPLETED:
            raise ValueError("Cannot extend completed task")
        
        task.extend(additional_minutes)
        task.updated_by = extended_by
        
        # Record extension reason
        if task.context is None:
            task.context = {}
        extensions = task.context.get("extensions", [])
        extensions.append({
            "extended_at": datetime.utcnow().isoformat(),
            "additional_minutes": additional_minutes,
            "reason": reason,
            "extended_by": extended_by,
        })
        task.context["extensions"] = extensions
        
        await self.session.commit()
        await self.session.refresh(task)
        
        # Update cache
        await self._cache_task(task)
        
        logger.info(
            f"Task extended: {task.id} by {additional_minutes} minutes",
            extra={
                "task_id": str(task_id),
                "additional_minutes": additional_minutes,
                "extended_by": extended_by,
            }
        )
        
        return task
    
    async def get_task_capabilities(self, task_id: UUID) -> List[Dict[str, Any]]:
        """Get all capabilities for a task."""
        query = (
            select(Capability, TaskCapability)
            .join(TaskCapability, Capability.id == TaskCapability.capability_id)
            .where(
                and_(
                    TaskCapability.task_id == task_id,
                    TaskCapability.is_active == True,
                )
            )
        )
        
        result = await self.session.execute(query)
        rows = result.all()
        
        capabilities = []
        for capability, assignment in rows:
            capabilities.append({
                "id": capability.id,
                "name": capability.name,
                "description": capability.description,
                "category": capability.category,
                "is_sensitive": capability.is_sensitive,
                "requires_approval": capability.requires_approval,
                "granted_at": assignment.granted_at,
            })
        
        return capabilities
    
    async def get_task_context(self, task_id: UUID) -> Optional[Dict[str, Any]]:
        """Get task context (with caching)."""
        # Try cache first
        cached = await redis_client.get(f"task:context:{task_id}")
        if cached:
            return cached
        
        # Get from database
        task = await self.get_task_by_id(task_id)
        if not task:
            return None
        
        return task.context
    
    async def validate_task_access(
        self,
        task_id: UUID,
        agent_id: UUID,
        required_capability: Optional[str] = None,
    ) -> Tuple[bool, Optional[Task], Optional[str]]:
        """Validate if an agent can access a task.
        
        Returns:
            Tuple[bool, Optional[Task], Optional[str]]:
                (is_valid, task, error_message)
        """
        task = await self.get_task_by_id(task_id)
        if not task:
            return False, None, "Task not found"
        
        # Check agent ownership
        if task.agent_id != agent_id:
            return False, task, "Agent does not own this task"
        
        # Check if task is active
        if not task.is_active:
            return False, task, "Task is not active"
        
        # Check capability if required
        if required_capability:
            has_cap = await self._task_has_capability(task_id, required_capability)
            if not has_cap:
                return False, task, f"Task lacks required capability: {required_capability}"
        
        return True, task, None
    
    async def cleanup_expired_tasks(self) -> int:
        """Clean up expired tasks."""
        now = datetime.utcnow()
        
        # Find expired active tasks
        query = select(Task).where(
            and_(
                Task.status == TaskStatus.ACTIVE,
                Task.expires_at < now,
            )
        )
        
        result = await self.session.execute(query)
        tasks = result.scalars().all()
        
        count = 0
        for task in tasks:
            task.status = TaskStatus.EXPIRED
            count += 1
        
        if count > 0:
            await self.session.commit()
            logger.info(f"Cleaned up {count} expired tasks")
        
        return count
    
    async def _task_has_capability(self, task_id: UUID, capability_name: str) -> bool:
        """Check if a task has a specific capability."""
        query = (
            select(Capability)
            .join(TaskCapability, Capability.id == TaskCapability.capability_id)
            .where(
                and_(
                    TaskCapability.task_id == task_id,
                    TaskCapability.is_active == True,
                    Capability.name == capability_name,
                )
            )
        )
        
        result = await self.session.execute(query)
        return bool(result.scalar_one_or_none())
    
    async def _cache_task(self, task: Task) -> None:
        """Cache task data in Redis."""
        if not task.is_active:
            return
        
        # Cache task context
        if task.context:
            await redis_client.set(
                f"task:context:{task.id}",
                task.context,
                ttl=int((task.expires_at - datetime.utcnow()).total_seconds()),
            )
        
        # Cache task capabilities
        capabilities = await self.get_task_capabilities(task.id)
        cap_names = [cap["name"] for cap in capabilities]
        await redis_client.set(
            f"task:capabilities:{task.id}",
            cap_names,
            ttl=int((task.expires_at - datetime.utcnow()).total_seconds()),
        )
    
    async def _remove_task_cache(self, task_id: UUID) -> None:
        """Remove task from cache."""
        await redis_client.delete(
            f"task:context:{task_id}",
            f"task:capabilities:{task_id}",
        )