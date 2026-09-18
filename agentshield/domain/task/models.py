"""Task domain models."""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from enum import Enum
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from ...infrastructure.database.base import BaseModel, AuditMixin
from ..agent.models import Agent


class TaskStatus(str, Enum):
    """Task status enum."""
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    REVOKED = "revoked"


class TaskPriority(str, Enum):
    """Task priority enum."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Task(BaseModel, AuditMixin):
    """Task model representing a specific agent operation context."""
    
    __tablename__ = "tasks"
    
    # Core fields
    agent_id = Column(PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(255), nullable=False)  # Human user who initiated
    external_id = Column(String(255), nullable=True)  # External system reference
    
    # Intent and context
    intent_type = Column(String(100), nullable=False)
    intent_data = Column(JSON, nullable=True)
    context = Column(JSON, nullable=True)
    
    # Status and lifecycle
    status = Column(String(50), nullable=False, default=TaskStatus.ACTIVE)
    priority = Column(String(50), nullable=False, default=TaskPriority.MEDIUM)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="tasks")
    capabilities = relationship("TaskCapability", back_populates="task", cascade="all, delete-orphan")
    events = relationship("SecurityEvent", back_populates="task")
    
    @hybrid_property
    def is_active(self) -> bool:
        """Check if task is active."""
        return self.status == TaskStatus.ACTIVE and self.expires_at > datetime.utcnow()
    
    @hybrid_property
    def is_expired(self) -> bool:
        """Check if task has expired."""
        return self.expires_at <= datetime.utcnow()
    
    def complete(self) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow()
    
    def revoke(self) -> None:
        """Revoke task (immediate termination)."""
        self.status = TaskStatus.REVOKED
        self.completed_at = datetime.utcnow()
    
    def extend(self, additional_minutes: int) -> None:
        """Extend task expiration."""
        if self.is_active:
            self.expires_at = datetime.utcnow() + timedelta(minutes=additional_minutes)
    
    def get_context_value(self, key: str, default: Any = None) -> Any:
        """Get a value from task context."""
        if self.context:
            return self.context.get(key, default)
        return default
    
    def has_context_key(self, key: str) -> bool:
        """Check if context has a specific key."""
        return bool(self.context and key in self.context)
    
    def __repr__(self) -> str:
        return f"<Task {self.id} ({self.intent_type}) for agent {self.agent_id}>"
    
    __table_args__ = (
        Index("idx_tasks_agent_status_expires", "agent_id", "status", "expires_at"),
        Index("idx_tasks_status_expires", "status", "expires_at"),
        Index("idx_tasks_intent_type", "intent_type"),
    )


class TaskCapability(BaseModel):
    """Task-specific capability assignment."""
    
    __tablename__ = "task_capabilities"
    
    task_id = Column(PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    capability_id = Column(PGUUID(as_uuid=True), ForeignKey("capabilities.id", ondelete="CASCADE"), nullable=False)
    granted_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    task = relationship("Task", back_populates="capabilities")
    capability = relationship("Capability")
    
    __table_args__ = (
        Index("idx_task_capabilities_task", "task_id"),
        Index("idx_task_capabilities_active", "is_active"),
    )
    
    def __repr__(self) -> str:
        return f"<TaskCapability task={self.task_id} capability={self.capability_id}>"


class TaskContextLog(BaseModel):
    """Log of task context changes for audit."""
    
    __tablename__ = "task_context_logs"
    
    task_id = Column(PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    field = Column(String(100), nullable=False)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    changed_by = Column(String(255), nullable=False)
    changed_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Relationships
    task = relationship("Task")
    
    __table_args__ = (
        Index("idx_task_context_logs_task", "task_id"),
        Index("idx_task_context_logs_field", "field"),
    )