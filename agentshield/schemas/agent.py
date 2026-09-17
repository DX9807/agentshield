"""Agent schemas for API requests/responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..domain.agent.models import AgentEnvironment, AgentRiskLevel, AgentStatus


class AgentCreate(BaseModel):
    """Schema for creating an agent."""

    name: str = Field(..., min_length=3, max_length=255)
    description: str | None = None
    owner: str = Field(..., min_length=1, max_length=255)
    purpose: str | None = None
    environment: AgentEnvironment = AgentEnvironment.DEVELOPMENT
    risk_level: AgentRiskLevel = AgentRiskLevel.LOW
    capabilities: list[str] | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate agent name."""
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        cleaned = v.strip().lower()
        if not cleaned.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Name can only contain alphanumeric, hyphens, and underscores")
        return cleaned

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "customer-support-agent",
                "description": "AI agent for customer support operations",
                "owner": "customer-success-team",
                "purpose": "Handle customer refunds and order inquiries",
                "environment": "production",
                "risk_level": "medium",
                "capabilities": ["read_customer", "read_order", "create_refund"],
                "metadata": {"version": "1.0.0", "team": "support"},
            }
        }
    )


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""

    name: str | None = Field(None, min_length=3, max_length=255)
    description: str | None = None
    owner: str | None = Field(None, min_length=1, max_length=255)
    purpose: str | None = None
    environment: AgentEnvironment | None = None
    risk_level: AgentRiskLevel | None = None
    status: AgentStatus | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """Validate agent name if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError("Name cannot be empty")
            cleaned = v.strip().lower()
            if not cleaned.replace("-", "").replace("_", "").isalnum():
                raise ValueError("Name can only contain alphanumeric, hyphens, and underscores")
            return cleaned
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "active",
                "risk_level": "medium",
                "description": "Updated description",
            }
        }
    )


class AgentResponse(BaseModel):
    """Schema for agent response."""

    id: UUID
    name: str
    description: str | None = None
    owner: str
    purpose: str | None = None
    environment: AgentEnvironment
    risk_level: AgentRiskLevel
    status: AgentStatus
    metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
    updated_by: str | None = None

    # Relationships
    capabilities: list[str] = Field(default_factory=list)
    credential_prefix: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AgentWithCredentials(AgentResponse):
    """Agent response with credentials (for initial creation only)."""

    api_key: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AgentListResponse(BaseModel):
    """Response for listing agents."""

    items: list[AgentResponse]
    total: int
    page: int = 1
    limit: int = 20

    model_config = ConfigDict(from_attributes=True)


class AgentTokenRequest(BaseModel):
    """Request for agent authentication."""

    agent_id: UUID
    api_key: str = Field(..., min_length=10)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "agent_id": "550e8400-e29b-41d4-a716-446655440000",
                "api_key": "ak_abc123def456...",
            }
        }
    )


class AgentTokenResponse(BaseModel):
    """Response for agent authentication."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    agent_id: UUID
    agent_name: str
    capabilities: list[str]

    model_config = ConfigDict(from_attributes=True)
