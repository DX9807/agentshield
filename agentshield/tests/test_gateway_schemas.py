"""Unit tests for Gateway schemas."""

from uuid import uuid4
import pytest
from pydantic import ValidationError

from agentshield.schemas.gateway import (
    GatewayBatchRequest,
    GatewayBatchResponse,
    GatewayForwardRequest,
    GatewayResponse,
)


class TestGatewaySchemas:
    """Test suite for gateway Pydantic schemas."""

    def test_gateway_forward_request_valid(self) -> None:
        """Test valid GatewayForwardRequest instantiation."""
        agent_id = uuid4()
        task_id = uuid4()
        req = GatewayForwardRequest(
            agent_id=agent_id,
            api_key="ak_1234567890abcdef",
            task_id=task_id,
            target_url="https://api.example.com/customers/101",
            method="GET",
            headers={"Accept": "application/json"},
            query_params={"detail": "true"},
            body={"key": "val"},
        )
        assert req.agent_id == agent_id
        assert req.method == "GET"
        assert req.headers["Accept"] == "application/json"
        assert req.query_params["detail"] == "true"
        assert req.body["key"] == "val"

    def test_gateway_forward_request_validation(self) -> None:
        """Test validation error for short api_key."""
        with pytest.raises(ValidationError):
            GatewayForwardRequest(
                agent_id=uuid4(),
                api_key="short",  # min_length is 10
                task_id=uuid4(),
                target_url="https://api.example.com",
                method="POST",
            )

    def test_gateway_response_schema(self) -> None:
        """Test GatewayResponse schema."""
        res = GatewayResponse(
            request_id="req-12345",
            decision="ALLOW",
            reason="Risk score acceptable",
            risk_score=20,
            response={"status_code": 200, "body": {"ok": True}},
            elapsed_ms=15,
        )
        assert res.request_id == "req-12345"
        assert res.decision == "ALLOW"
        assert res.response["status_code"] == 200
        assert res.error is None

    def test_gateway_batch_schemas(self) -> None:
        """Test GatewayBatchRequest and GatewayBatchResponse."""
        req1 = GatewayForwardRequest(
            agent_id=uuid4(),
            api_key="ak_1234567890abcdef",
            task_id=uuid4(),
            target_url="https://api.example.com/orders",
            method="GET",
        )
        batch_req = GatewayBatchRequest(requests=[req1])
        assert len(batch_req.requests) == 1

        batch_res = GatewayBatchResponse(
            responses=[
                GatewayResponse(
                    request_id="req-1",
                    decision="ALLOW",
                    reason="ok",
                    risk_score=15,
                    elapsed_ms=5,
                )
            ],
            total=1,
            allowed=1,
            blocked=0,
            require_approval=0,
        )
        assert batch_res.total == 1
        assert batch_res.allowed == 1
        assert batch_res.blocked == 0

