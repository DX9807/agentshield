"""Capability schemas for API requests/responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CapabilityCreate(BaseModel):
    """Schema for creating a capability."""

    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = None
    category: str = Field(..., min_length=2, max_length=50)
    is_sensitive: bool = False
    requires_approval: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "create_refund",
                "description": "Create a refund for an order",
                "category": "financial",
                "is_sensitive": True,
                "requires_approval": True,
            }
        }
    )


class CapabilityResponse(BaseModel):
    """Schema for capability response."""

    id: UUID
    name: str
    description: str | None
    category: str
    is_sensitive: bool
    requires_approval: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CapabilityListResponse(BaseModel):
    """Response for listing capabilities."""

    items: list[CapabilityResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)


class AgentCapabilityRequest(BaseModel):
    """Schema for granting capability to agent."""

    capability_id: UUID
    expires_at: datetime | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "capability_id": "550e8400-e29b-41d4-a716-446655440000",
                "expires_at": "2024-12-31T23:59:59Z",
            }
        }
    )


class AgentCapabilityResponse(BaseModel):
    """Schema for agent capability assignment response."""

    id: UUID
    agent_id: UUID
    capability_id: UUID
    capability_name: str
    granted_at: datetime
    expires_at: datetime | None = None
    is_active: bool = True
    granted_by: str | None = None

    model_config = ConfigDict(from_attributes=True)
