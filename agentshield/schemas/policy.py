"""Policy schemas for API requests/responses."""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, validator

from ..domain.policy.models import PolicyDecision


class PolicyCondition(BaseModel):
    """Policy condition model."""
    
    field: str = Field(..., description="Field path in dot notation (e.g., 'agent.risk_level')")
    operator: str = Field(..., description="Comparison operator: eq, neq, gt, gte, lt, lte, in, contains, regex")
    value: Any = Field(..., description="Expected value to compare against")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "field": "request.amount",
                "operator": "lte",
                "value": 5000
            }
        }
    )


class PolicyCreate(BaseModel):
    """Schema for creating a policy."""
    
    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    version: str = "1.0"
    
    agent_id: Optional[UUID] = None
    agent_name: Optional[str] = None
    action: str = Field(..., min_length=1, max_length=100)
    resource_type: Optional[str] = None
    
    decision: PolicyDecision
    priority: int = Field(100, ge=1, le=1000)
    order: Optional[int] = Field(None, ge=1, le=100)
    enabled: bool = True
    
    conditions: Optional[List[PolicyCondition]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @validator("name")
    def validate_name(cls, v):
        """Validate policy name."""
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()
    
    @validator("decision")
    def validate_decision(cls, v):
        """Validate decision."""
        if v not in PolicyDecision:
            raise ValueError(f"Invalid decision: {v}")
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "customer-refund-policy",
                "description": "Controls refund operations for customer support",
                "agent_name": "customer-support-agent",
                "action": "create_refund",
                "decision": "allow",
                "priority": 10,
                "enabled": True,
                "conditions": [
                    {"field": "request.amount", "operator": "lte", "value": 5000},
                    {"field": "context.customer_id", "operator": "eq", "value": "CUST-123"},
                ],
                "metadata": {"created_by": "security-team", "version": "1.0"}
            }
        }
    )


class PolicyUpdate(BaseModel):
    """Schema for updating a policy."""
    
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    version: Optional[str] = None
    
    agent_id: Optional[UUID] = None
    agent_name: Optional[str] = None
    action: Optional[str] = Field(None, min_length=1, max_length=100)
    resource_type: Optional[str] = None
    
    decision: Optional[PolicyDecision] = None
    priority: Optional[int] = Field(None, ge=1, le=1000)
    order: Optional[int] = Field(None, ge=1, le=100)
    enabled: Optional[bool] = None
    
    conditions: Optional[List[PolicyCondition]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Updated refund policy with lower limit",
                "priority": 5,
                "enabled": True,
                "conditions": [
                    {"field": "request.amount", "operator": "lte", "value": 1000},
                ]
            }
        }
    )


class PolicyResponse(BaseModel):
    """Schema for policy response."""
    
    id: UUID
    name: str
    description: Optional[str]
    version: str
    
    agent_id: Optional[UUID]
    agent_name: Optional[str]
    action: str
    resource_type: Optional[str]
    
    decision: PolicyDecision
    priority: int
    order: Optional[int]
    enabled: bool
    
    conditions: Optional[List[PolicyCondition]]
    metadata: Optional[Dict[str, Any]]
    
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)


class PolicyListResponse(BaseModel):
    """Response for listing policies."""
    
    items: List[PolicyResponse]
    total: int
    page: int = 1
    limit: int = 20
    
    model_config = ConfigDict(from_attributes=True)


class PolicyEvaluationRequest(BaseModel):
    """Request for evaluating a policy."""
    
    agent_id: UUID
    task_id: UUID
    action: str
    resource: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    request_data: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "agent_id": "550e8400-e29b-41d4-a716-446655440000",
                "task_id": "550e8400-e29b-41d4-a716-446655440001",
                "action": "create_refund",
                "resource": "/api/refunds",
                "method": "POST",
                "path": "/api/refunds",
                "request_data": {
                    "amount": 5000,
                    "customer_id": "CUST-123",
                    "order_id": "ORD-789"
                }
            }
        }
    )


class PolicyEvaluationResponse(BaseModel):
    """Response for policy evaluation."""
    
    decision: PolicyDecision
    matched_policy_id: Optional[UUID]
    matched_policy_name: Optional[str]
    reason: str
    risk_score: Optional[int] = None
    conditions_evaluated: Optional[List[Dict[str, Any]]] = None
    
    model_config = ConfigDict(from_attributes=True)