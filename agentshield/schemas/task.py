"""Task schemas for API requests/responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ..domain.task.models import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    """Schema for creating a task."""

    agent_id: UUID
    user_id: str = Field(..., min_length=1, max_length=255)
    external_id: str | None = None
    intent_type: str = Field(..., min_length=1, max_length=100)
    intent_data: dict[str, Any] | None = None
    context: dict[str, Any] | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    expires_in_minutes: int = Field(60, ge=1, le=1440)  # 1 minute to 24 hours
    capabilities: list[str] | None = None  # Capability names to assign

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "agent_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user-123",
                "external_id": "ticket-456",
                "intent_type": "refund_order",
                "intent_data": {"order_id": "ORD-123", "reason": "damaged"},
                "context": {"customer_id": "CUST-456", "region": "US"},
                "priority": "high",
                "expires_in_minutes": 120,
                "capabilities": ["read_customer", "read_order", "create_refund"],
            }
        }
    )


class TaskUpdate(BaseModel):
    """Schema for updating a task."""

    priority: TaskPriority | None = None
    context: dict[str, Any] | None = None
    expires_in_minutes: int | None = Field(None, ge=1, le=1440)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "priority": "critical",
                "context": {"customer_id": "CUST-789"},
                "expires_in_minutes": 180,
            }
        }
    )


class TaskResponse(BaseModel):
    """Schema for task response."""

    id: UUID
    agent_id: UUID
    user_id: str
    external_id: str | None = None
    intent_type: str
    intent_data: dict[str, Any] | None = None
    context: dict[str, Any] | None = None
    status: TaskStatus
    priority: TaskPriority
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    created_by: str | None = None
    updated_by: str | None = None

    # Relationships
    capabilities: list[str] = Field(default_factory=list)
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(BaseModel):
    """Response for listing tasks."""

    items: list[TaskResponse]
    total: int
    page: int = 1
    limit: int = 20

    model_config = ConfigDict(from_attributes=True)


class TaskCompleteRequest(BaseModel):
    """Schema for completing a task."""

    result_data: dict[str, Any] | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "result_data": {"refund_id": "REF-789", "amount": 50.00},
            }
        }
    )


class TaskExtendRequest(BaseModel):
    """Schema for extending a task."""

    additional_minutes: int = Field(..., ge=1, le=1440)
    reason: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "additional_minutes": 60,
                "reason": "Need more time for investigation",
            }
        }
    )
