"""Unit tests for agent domain models."""

from uuid import uuid4

from agentshield.domain.agent.models import (
    Agent,
    AgentCredential,
    AgentEnvironment,
    AgentRiskLevel,
    AgentStatus,
    PredefinedCapabilities,
)


class TestAgentModels:
    """Test suite for agent models."""

    def test_agent_status_enums(self) -> None:
        """Test agent status enum values."""
        assert AgentStatus.ACTIVE == "active"
        assert AgentStatus.INACTIVE == "inactive"
        assert AgentStatus.SUSPENDED == "suspended"
        assert AgentStatus.PENDING_APPROVAL == "pending_approval"

    def test_agent_risk_level_enums(self) -> None:
        """Test agent risk level enum values."""
        assert AgentRiskLevel.LOW == "low"
        assert AgentRiskLevel.MEDIUM == "medium"
        assert AgentRiskLevel.HIGH == "high"
        assert AgentRiskLevel.CRITICAL == "critical"

    def test_agent_environment_enums(self) -> None:
        """Test agent environment enum values."""
        assert AgentEnvironment.DEVELOPMENT == "development"
        assert AgentEnvironment.STAGING == "staging"
        assert AgentEnvironment.PRODUCTION == "production"

    def test_agent_instance_properties(self) -> None:
        """Test agent instance hybrid properties."""
        agent = Agent(
            name="test-agent",
            owner="secops",
            status=AgentStatus.ACTIVE,
            environment=AgentEnvironment.DEVELOPMENT,
            risk_level=AgentRiskLevel.LOW,
        )
        assert agent.is_active is True
        assert agent.is_suspended is False

        agent.status = AgentStatus.SUSPENDED
        assert agent.is_active is False
        assert agent.is_suspended is True

        agent.status = AgentStatus.INACTIVE
        assert agent.is_active is False
        assert agent.is_suspended is False

    def test_credential_generation_and_verification(self) -> None:
        """Test generating and verifying API keys."""
        api_key, hashed_key, prefix = AgentCredential.generate_api_key()

        assert api_key.startswith("ak_")
        assert prefix == "ak_"
        assert len(api_key) > 30

        credential = AgentCredential(
            agent_id=uuid4(),
            credential_type="api_key",
            credential_hash=hashed_key,
            credential_prefix=prefix,
        )

        # Valid verification
        assert credential.verify_api_key(api_key) is True

        # Invalid prefix
        assert credential.verify_api_key("invalid_prefix_key") is False

        # Wrong key
        assert credential.verify_api_key("ak_wrongsecretkey1234567890") is False

    def test_predefined_capabilities(self) -> None:
        """Test predefined capabilities list."""
        all_caps = PredefinedCapabilities.get_all()
        sensitive_caps = PredefinedCapabilities.get_sensitive()

        assert len(all_caps) >= 15
        assert PredefinedCapabilities.READ_CUSTOMER in all_caps
        assert PredefinedCapabilities.WRITE_CUSTOMER in all_caps
        assert PredefinedCapabilities.ACCESS_PAYROLL in sensitive_caps
        assert PredefinedCapabilities.DELETE_CUSTOMER in sensitive_caps
        assert PredefinedCapabilities.READ_CUSTOMER not in sensitive_caps
