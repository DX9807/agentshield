"""Unit tests for policy domain models."""

from agentshield.domain.policy.models import (
    Policy,
    PolicyDecision,
    PolicyEffect,
    PolicyEvaluation,
    PolicyViolation,
)


class TestPolicyModels:
    """Test suite for policy domain models."""

    def test_policy_decision_enum_values(self) -> None:
        """Test policy decision enum values."""
        assert PolicyDecision.ALLOW == "allow"
        assert PolicyDecision.DENY == "deny"
        assert PolicyDecision.REQUIRE_APPROVAL == "require_approval"
        assert PolicyDecision.REDACT == "redact"

    def test_policy_effect_enum_values(self) -> None:
        """Test policy effect enum values."""
        assert PolicyEffect.ALLOW == "allow"
        assert PolicyEffect.DENY == "deny"

    def test_policy_properties_and_repr(self) -> None:
        """Test policy active state, decision type, and string representation."""
        policy = Policy(
            name="test-policy",
            action="transfer_funds",
            decision="allow",
            enabled=True,
            priority=10,
        )
        assert policy.is_active is True
        assert policy.decision_type == PolicyDecision.ALLOW
        assert "test-policy" in repr(policy)
        assert "allow" in repr(policy)

        policy.enabled = False
        assert policy.is_active is False

    def test_evaluate_conditions_empty(self) -> None:
        """Test evaluation when no conditions are defined."""
        policy = Policy(
            name="no-conditions-policy",
            action="read",
            decision="allow",
            conditions=None,
        )
        assert policy.evaluate_conditions({"any": "context"}) is True

        policy.conditions = []
        assert policy.evaluate_conditions({"any": "context"}) is True

    def test_evaluate_conditions_equality_operators(self) -> None:
        """Test eq and neq condition operators."""
        policy = Policy(
            name="equality-policy",
            action="execute",
            decision="allow",
            conditions=[
                {"field": "agent.role", "operator": "eq", "value": "finance"},
                {"field": "agent.status", "operator": "neq", "value": "suspended"},
            ],
        )

        matching_context = {
            "agent": {"role": "finance", "status": "active"},
        }
        assert policy.evaluate_conditions(matching_context) is True

        non_matching_role = {
            "agent": {"role": "hr", "status": "active"},
        }
        assert policy.evaluate_conditions(non_matching_role) is False

        suspended_agent = {
            "agent": {"role": "finance", "status": "suspended"},
        }
        assert policy.evaluate_conditions(suspended_agent) is False

    def test_evaluate_conditions_numeric_comparison(self) -> None:
        """Test gt, gte, lt, and lte condition operators."""
        policy = Policy(
            name="numeric-policy",
            action="spend",
            decision="allow",
            conditions=[
                {"field": "request.amount", "operator": "gte", "value": 100},
                {"field": "request.amount", "operator": "lte", "value": 5000},
            ],
        )

        assert policy.evaluate_conditions({"request": {"amount": 100}}) is True
        assert policy.evaluate_conditions({"request": {"amount": 2500}}) is True
        assert policy.evaluate_conditions({"request": {"amount": 5000}}) is True
        assert policy.evaluate_conditions({"request": {"amount": 99}}) is False
        assert policy.evaluate_conditions({"request": {"amount": 5001}}) is False

    def test_evaluate_conditions_list_operators(self) -> None:
        """Test in and not_in list operators."""
        policy = Policy(
            name="list-operators-policy",
            action="access",
            decision="allow",
            conditions=[
                {"field": "environment", "operator": "in", "value": ["dev", "staging"]},
                {"field": "ip_address", "operator": "not_in", "value": ["10.0.0.1", "10.0.0.2"]},
            ],
        )

        assert policy.evaluate_conditions({"environment": "dev", "ip_address": "192.168.1.5"}) is True
        assert policy.evaluate_conditions({"environment": "prod", "ip_address": "192.168.1.5"}) is False
        assert policy.evaluate_conditions({"environment": "dev", "ip_address": "10.0.0.1"}) is False

    def test_evaluate_conditions_string_operators(self) -> None:
        """Test contains, startswith, endswith, and regex operators."""
        policy = Policy(
            name="string-policy",
            action="query",
            decision="allow",
            conditions=[
                {"field": "path", "operator": "startswith", "value": "/api/v1"},
                {"field": "path", "operator": "endswith", "value": "/data"},
                {"field": "resource", "operator": "contains", "value": "metrics"},
                {"field": "header.user_agent", "operator": "regex", "value": r"^Agent/\d+\.\d+$"},
            ],
        )

        valid_context = {
            "path": "/api/v1/user/data",
            "resource": "system_metrics_live",
            "header": {"user_agent": "Agent/2.1"},
        }
        assert policy.evaluate_conditions(valid_context) is True

        invalid_regex = {
            "path": "/api/v1/user/data",
            "resource": "system_metrics_live",
            "header": {"user_agent": "InvalidAgent"},
        }
        assert policy.evaluate_conditions(invalid_regex) is False

    def test_evaluate_conditions_missing_field_and_invalid_condition(self) -> None:
        """Test handling of missing nested fields and malformed conditions."""
        policy = Policy(
            name="robustness-policy",
            action="test",
            decision="allow",
            conditions=[
                {"field": "non.existent.path", "operator": "eq", "value": "anything"},
            ],
        )
        assert policy.evaluate_conditions({"other": "field"}) is False

        # Malformed condition missing operator should be safely skipped
        policy.conditions = [{"field": "some.field"}]
        assert policy.evaluate_conditions({"some": {"field": 123}}) is True

    def test_policy_evaluation_model_instantiation(self) -> None:
        """Test PolicyEvaluation audit model instantiation."""
        evaluation = PolicyEvaluation(
            action="read_file",
            resource="/etc/config",
            matched=True,
            decision="allow",
            reason="Matched default read policy",
            risk_score=15,
            evaluation_time_ms=4,
        )
        assert evaluation.action == "read_file"
        assert evaluation.matched is True
        assert evaluation.decision == "allow"
        assert evaluation.risk_score == 15

    def test_policy_violation_model_instantiation(self) -> None:
        """Test PolicyViolation monitoring model instantiation."""
        violation = PolicyViolation(
            action="delete_db",
            resource="production_cluster",
            violation_type="unauthorized_action",
            severity="critical",
            description="Agent attempted dropping production database",
            risk_score=95,
            resolved=False,
        )
        assert violation.action == "delete_db"
        assert violation.severity == "critical"
        assert violation.resolved is False

