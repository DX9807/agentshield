from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..domain.policy.models import PolicyDecision


class PolicyCondition(BaseModel):
    """Policy condition model."""

    field: str = Field(..., description="Field path in dot notation (e.g., 'agent.risk_level')")
    operator: str = Field(
        ..., description="Comparison operator: eq, neq, gt, gte, lt, lte, in, contains, regex"
    )
    value: Any | None = Field(default=None, description="Expected value to compare against")
    value_field: str | None = Field(
        default=None,
        description="Field path in context for dynamic comparison (e.g., 'task.context.customer_id')",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "field": "request.amount",
                "operator": "lte",
                "value": 5000,
            }
        }
    )


class PolicyCreate(BaseModel):
    """Schema for creating a policy."""

    name: str = Field(..., min_length=3, max_length=255)
    description: str | None = None
    version: str = "1.0"

    agent_id: UUID | None = None
    agent_name: str | None = None
    action: str = Field(..., min_length=1, max_length=100)
    resource_type: str | None = None

    decision: PolicyDecision
    priority: int = Field(100, ge=1, le=1000)
    order: int | None = Field(None, ge=1, le=100)
    enabled: bool = True

    conditions: list[PolicyCondition] | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate policy name."""
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: PolicyDecision) -> PolicyDecision:
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
                "metadata": {"created_by": "security-team", "version": "1.0"},
            }
        }
    )


class PolicyUpdate(BaseModel):
    """Schema for updating a policy."""

    name: str | None = Field(None, min_length=3, max_length=255)
    description: str | None = None
    version: str | None = None

    agent_id: UUID | None = None
    agent_name: str | None = None
    action: str | None = Field(None, min_length=1, max_length=100)
    resource_type: str | None = None

    decision: PolicyDecision | None = None
    priority: int | None = Field(None, ge=1, le=1000)
    order: int | None = Field(None, ge=1, le=100)
    enabled: bool | None = None

    conditions: list[PolicyCondition] | None = None
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Updated refund policy with lower limit",
                "priority": 5,
                "enabled": True,
                "conditions": [
                    {"field": "request.amount", "operator": "lte", "value": 1000},
                ],
            }
        }
    )


class PolicyResponse(BaseModel):
    """Schema for policy response."""

    id: UUID
    name: str
    description: str | None = None
    version: str = "1.0"

    agent_id: UUID | None = None
    agent_name: str | None = None
    action: str
    resource_type: str | None = None

    decision: PolicyDecision
    priority: int = 100
    order: int | None = None
    enabled: bool = True

    conditions: list[PolicyCondition] | None = None
    metadata: dict[str, Any] | None = None

    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
    updated_by: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PolicyListResponse(BaseModel):
    """Response for listing policies."""

    items: list[PolicyResponse]
    total: int
    page: int = 1
    limit: int = 20

    model_config = ConfigDict(from_attributes=True)


class PolicyEvaluationRequest(BaseModel):
    """Request for evaluating a policy."""

    agent_id: UUID
    task_id: UUID
    action: str
    resource: str | None = None
    method: str | None = None
    path: str | None = None
    request_data: dict[str, Any] | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "agent_id": "550e8400-e29b-41d4-a716-446655440000",
                "task_id": "550e8400-e29b-41d4-a716-446655440001",
                "action": "create_refund",
                "resource": "/api/refunds",
                "method": "POST",
                "path": "/api/refunds",
                "request_data": {"amount": 5000, "customer_id": "CUST-123", "order_id": "ORD-789"},
            }
        }
    )


class PolicyEvaluationResponse(BaseModel):
    """Response for policy evaluation."""

    decision: PolicyDecision
    matched_policy_id: UUID | None = None
    matched_policy_name: str | None = None
    reason: str
    risk_score: int | None = None
    conditions_evaluated: list[dict[str, Any]] | None = None

    model_config = ConfigDict(from_attributes=True)
