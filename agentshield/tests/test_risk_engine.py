"""Unit tests for the Risk Scoring Engine."""

import pytest

from agentshield.domain.risk.engine import RiskEngine, RiskLevel


@pytest.mark.asyncio
class TestRiskEngine:
    """Test suite for deterministic risk scoring."""

    async def test_risk_base_score_minimal_context(self) -> None:
        """Test minimal context risk calculation."""
        engine = RiskEngine()
        context = {
            "agent_risk_level": "low",
            "task_priority": "low",
            "action": "GET",
            "resource": "public_data",
            "policy_decision": "allow",
            "task_expires_in": 60,
        }
        score = await engine.calculate(context)
        # Base 10 + 0 + 0 + 2 (GET) + 0 + 0 + 0 = 12
        assert score == 12
        assert engine.get_risk_level(score) == RiskLevel.LOW

    async def test_agent_risk_and_task_priority_impact(self) -> None:
        """Test risk score increments with higher agent risk and task priority."""
        engine = RiskEngine()

        high_risk_context = {
            "agent_risk_level": "high",  # +25
            "task_priority": "high",  # +15
            "action": "GET",  # +2
            "resource": "orders",  # +5
            "policy_decision": "allow",
            "task_expires_in": 30,
        }
        score = await engine.calculate(high_risk_context)
        # 10 + 25 + 15 + 2 + 5 = 57
        assert score == 57
        assert engine.get_risk_level(score) == RiskLevel.MEDIUM

    async def test_sensitive_action_and_resource_impact(self) -> None:
        """Test sensitive HTTP methods and resources like DELETE, admin, and secret."""
        engine = RiskEngine()

        critical_context = {
            "agent_risk_level": "critical",  # +40
            "task_priority": "critical",  # +30
            "action": "DELETE",  # +25
            "resource": "admin_console",  # +40
            "policy_decision": "allow",
            "task_expires_in": 60,
        }
        score = await engine.calculate(critical_context)
        # 10 + 40 + 30 + 25 + 40 = 145 -> Clamped to 100
        assert score == 100
        assert engine.get_risk_level(score) == RiskLevel.CRITICAL

    async def test_policy_decision_and_expiration_impact(self) -> None:
        """Test policy denial and impending task expiration risk additions."""
        engine = RiskEngine()

        expiring_denied_context = {
            "agent_risk_level": "low",  # 0
            "task_priority": "medium",  # +5
            "action": "POST",  # +10
            "resource": "refund_claim",  # +15
            "policy_decision": "deny",  # +30
            "task_expires_in": 3,  # +20 (<5m)
        }
        score = await engine.calculate(expiring_denied_context)
        # 10 + 0 + 5 + 10 + 15 + 30 + 20 = 90
        assert score == 90
        assert engine.get_risk_level(score) == RiskLevel.CRITICAL

    async def test_risk_level_threshold_boundaries(self) -> None:
        """Test risk level boundaries (CRITICAL >= 80, HIGH >= 60, MEDIUM >= 30, LOW < 30)."""
        engine = RiskEngine()
        assert engine.get_risk_level(100) == RiskLevel.CRITICAL
        assert engine.get_risk_level(80) == RiskLevel.CRITICAL
        assert engine.get_risk_level(79) == RiskLevel.HIGH
        assert engine.get_risk_level(60) == RiskLevel.HIGH
        assert engine.get_risk_level(59) == RiskLevel.MEDIUM
        assert engine.get_risk_level(30) == RiskLevel.MEDIUM
        assert engine.get_risk_level(29) == RiskLevel.LOW
        assert engine.get_risk_level(0) == RiskLevel.LOW
