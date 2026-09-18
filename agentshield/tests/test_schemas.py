"""Unit tests for agent and capability Pydantic schemas."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from agentshield.domain.agent.models import AgentEnvironment, AgentRiskLevel, AgentStatus
from agentshield.schemas.agent import (
    AgentCreate,
    AgentTokenRequest,
    AgentUpdate,
)
from agentshield.schemas.capability import CapabilityCreate


class TestSchemas:
    """Test suite for Pydantic schemas."""

    def test_agent_create_valid(self) -> None:
        """Test valid agent creation payload."""
        payload = AgentCreate(
            name="payment-agent",
            owner="finance",
            description="Processes invoices",
            environment=AgentEnvironment.PRODUCTION,
            risk_level=AgentRiskLevel.HIGH,
            capabilities=["read_invoice", "write_invoice"],
            metadata={"version": "1.0"},
        )
        assert payload.name == "payment-agent"
        assert payload.owner == "finance"
        assert payload.risk_level == AgentRiskLevel.HIGH

    def test_agent_create_invalid_name(self) -> None:
        """Test that invalid names (special characters/empty) are rejected."""
        with pytest.raises(ValidationError):
            AgentCreate(name="bad agent!", owner="team")

        with pytest.raises(ValidationError):
            AgentCreate(name="   ", owner="team")

        with pytest.raises(ValidationError):
            AgentCreate(name="ab", owner="team")  # Too short (min_length=3)

    def test_agent_update_validator(self) -> None:
        """Test updating agent fields."""
        update = AgentUpdate(
            description="New description",
            status=AgentStatus.SUSPENDED,
        )
        assert update.description == "New description"
        assert update.status == AgentStatus.SUSPENDED

        with pytest.raises(ValidationError):
            AgentUpdate(name="invalid@name")

    def test_capability_create(self) -> None:
        """Test capability create schema."""
        cap = CapabilityCreate(
            name="export_metrics",
            description="Export system telemetry",
            category="monitoring",
            is_sensitive=False,
            requires_approval=False,
        )
        assert cap.name == "export_metrics"
        assert cap.category == "monitoring"

    def test_agent_token_request(self) -> None:
        """Test agent token request validation."""
        req = AgentTokenRequest(
            agent_id=uuid4(),
            api_key="ak_1234567890abcdef",
        )
        assert req.api_key.startswith("ak_")

        with pytest.raises(ValidationError):
            AgentTokenRequest(
                agent_id=uuid4(),
                api_key="short",  # min_length=10
            )
