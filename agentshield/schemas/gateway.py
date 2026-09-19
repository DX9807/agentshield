"""Gateway schemas for API requests/responses."""

from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, HttpUrl


class GatewayForwardRequest(BaseModel):
    """Request to forward through gateway."""
    
    agent_id: UUID
    api_key: str = Field(..., min_length=10)
    task_id: UUID
    target_url: str = Field(..., description="Target API URL")
    method: str = Field(..., description="HTTP method")
    headers: Optional[Dict[str, str]] = None
    query_params: Optional[Dict[str, str]] = None
    body: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "agent_id": "550e8400-e29b-41d4-a716-446655440000",
                "api_key": "ak_abc123def456...",
                "task_id": "550e8400-e29b-41d4-a716-446655440001",
                "target_url": "https://api.example.com/customers/123",
                "method": "GET",
                "headers": {"Accept": "application/json"},
                "query_params": {"limit": "10"},
            }
        }
    )


class GatewayResponse(BaseModel):
    """Gateway response."""
    
    request_id: str
    decision: str  # ALLOW, BLOCK, REQUIRE_APPROVAL, REDACT
    reason: str
    risk_score: int
    response: Optional[Dict[str, Any]] = None
    elapsed_ms: int
    error: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class GatewayBatchRequest(BaseModel):
    """Batch request for multiple evaluations."""
    
    requests: List[GatewayForwardRequest]
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "requests": [
                    {
                        "agent_id": "550e8400-e29b-41d4-a716-446655440000",
                        "api_key": "ak_abc123def456...",
                        "task_id": "550e8400-e29b-41d4-a716-446655440001",
                        "target_url": "https://api.example.com/customers/123",
                        "method": "GET",
                    }
                ]
            }
        }
    )


class GatewayBatchResponse(BaseModel):
    """Batch response."""
    
    responses: List[GatewayResponse]
    total: int
    allowed: int
    blocked: int
    
    model_config = ConfigDict(from_attributes=True)