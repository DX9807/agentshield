"""Agent schemas for API requests/responses."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, validator, ConfigDict
from enum import Enum

from ..domain.agent.models import AgentStatus, AgentRiskLevel, AgentEnvironment


class AgentCreate(BaseModel):
    """Schema for creating an agent."""
    
    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    owner: str = Field(..., min_length=1, max_length=255)
    purpose: Optional[str] = None
    environment: AgentEnvironment = AgentEnvironment.DEVELOPMENT
    risk_level: AgentRiskLevel = AgentRiskLevel.LOW
    capabilities: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @validator("name")
    def validate_name(cls, v):
        """Validate agent name."""
        if not v.strip():
            raise ValueError("Name cannot be empty")
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Name can only contain alphanumeric, hyphens, and underscores")
        return v.strip().lower()
    
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
                "metadata": {"version": "1.0.0", "team": "support"}
            }
        }
    )


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""
    
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    owner: Optional[str] = Field(None, min_length=1, max_length=255)
    purpose: Optional[str] = None
    environment: Optional[AgentEnvironment] = None
    risk_level: Optional[AgentRiskLevel] = None
    status: Optional[AgentStatus] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @validator("name")
    def validate_name(cls, v):
        """Validate agent name if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError("Name cannot be empty")
            if not v.replace("-", "").replace("_", "").isalnum():
                raise ValueError("Name can only contain alphanumeric, hyphens, and underscores")
            return v.strip().lower()
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "active",
                "risk_level": "medium",
                "description": "Updated description"
            }
        }
    )


class AgentResponse(BaseModel):
    """Schema for agent response."""
    
    id: UUID
    name: str
    description: Optional[str]
    owner: str
    purpose: Optional[str]
    environment: AgentEnvironment
    risk_level: AgentRiskLevel
    status: AgentStatus
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]
    
    # Relationships
    capabilities: List[str] = Field(default_factory=list)
    credential_prefix: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class AgentWithCredentials(AgentResponse):
    """Agent response with credentials (for initial creation only)."""
    
    api_key: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class AgentListResponse(BaseModel):
    """Response for listing agents."""
    
    items: List[AgentResponse]
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
                "api_key": "ak_abc123def456..."
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
    capabilities: List[str]
    
    model_config = ConfigDict(from_attributes=True)