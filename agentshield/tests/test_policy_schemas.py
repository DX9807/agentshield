"""Unit tests for policy schemas."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from agentshield.domain.policy.models import PolicyDecision
from agentshield.schemas.policy import (
    PolicyCondition,
    PolicyCreate,
    PolicyEvaluationRequest,
    PolicyEvaluationResponse,
    PolicyUpdate,
)


class TestPolicySchemas:
    """Test suite for policy Pydantic schemas."""

    def test_policy_condition_valid(self) -> None:
        """Test valid PolicyCondition creation."""
        condition = PolicyCondition(
            field="request.amount",
            operator="lte",
            value=5000,
        )
        assert condition.field == "request.amount"
        assert condition.operator == "lte"
        assert condition.value == 5000

    def test_policy_create_valid(self) -> None:
        """Test valid PolicyCreate schema."""
        agent_id = uuid4()
        policy_in = PolicyCreate(
            name="  financial-transfer-policy  ",
            description="Policy controlling financial fund transfers",
            agent_id=agent_id,
            action="transfer_funds",
            decision=PolicyDecision.REQUIRE_APPROVAL,
            priority=25,
            order=1,
            enabled=True,
            conditions=[PolicyCondition(field="request.amount", operator="gt", value=10000)],
            metadata={"department": "finance"},
        )
        assert policy_in.name == "financial-transfer-policy"  # Stripped
        assert policy_in.decision == PolicyDecision.REQUIRE_APPROVAL
        assert policy_in.priority == 25
        assert len(policy_in.conditions) == 1

    def test_policy_create_validation_errors(self) -> None:
        """Test validation constraints on PolicyCreate."""
        # Empty name
        with pytest.raises(ValidationError):
            PolicyCreate(
                name="   ",
                action="test",
                decision=PolicyDecision.ALLOW,
            )

        # Invalid priority (< 1 or > 1000)
        with pytest.raises(ValidationError):
            PolicyCreate(
                name="invalid-priority",
                action="test",
                decision=PolicyDecision.ALLOW,
                priority=0,
            )

        with pytest.raises(ValidationError):
            PolicyCreate(
                name="invalid-priority",
                action="test",
                decision=PolicyDecision.ALLOW,
                priority=1001,
            )

    def test_policy_update_schema(self) -> None:
        """Test PolicyUpdate schema."""
        update = PolicyUpdate(
            description="Updated description",
            priority=50,
            enabled=False,
            decision=PolicyDecision.DENY,
        )
        data = update.model_dump(exclude_unset=True)
        assert data["priority"] == 50
        assert data["enabled"] is False
        assert data["decision"] == PolicyDecision.DENY
        assert "name" not in data

    def test_policy_evaluation_request_schema(self) -> None:
        """Test PolicyEvaluationRequest schema."""
        agent_id = uuid4()
        task_id = uuid4()
        eval_req = PolicyEvaluationRequest(
            agent_id=agent_id,
            task_id=task_id,
            action="refund_order",
            resource="/api/v1/orders/123",
            method="POST",
            path="/api/v1/orders/123/refund",
            request_data={"amount": 49.99, "reason": "damaged"},
        )
        assert eval_req.agent_id == agent_id
        assert eval_req.action == "refund_order"
        assert eval_req.request_data["amount"] == 49.99

    def test_policy_evaluation_response_schema(self) -> None:
        """Test PolicyEvaluationResponse schema."""
        policy_id = uuid4()
        eval_res = PolicyEvaluationResponse(
            decision=PolicyDecision.ALLOW,
            matched_policy_id=policy_id,
            matched_policy_name="auto-refund-under-50",
            reason="Matched policy: auto-refund-under-50",
            risk_score=20,
        )
        assert eval_res.decision == PolicyDecision.ALLOW
        assert eval_res.matched_policy_id == policy_id
        assert eval_res.matched_policy_name == "auto-refund-under-50"
        assert eval_res.risk_score == 20
