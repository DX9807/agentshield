"""Policy engine domain models."""

from enum import Enum
from typing import Any

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from ...infrastructure.database.base import AuditMixin, BaseModel


class PolicyDecision(str, Enum):
    """Policy decision types."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    REDACT = "redact"


class PolicyEffect(str, Enum):
    """Policy effect types."""

    ALLOW = "allow"
    DENY = "deny"


class Policy(BaseModel, AuditMixin):
    """Policy definition model."""

    __tablename__ = "policies"

    # Core fields
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    version = Column(String(20), nullable=False, default="1.0")

    # Target fields
    agent_id = Column(
        PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=True
    )
    agent_name = Column(String(255), nullable=True)  # For agent name-based matching
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=True)

    # Decision
    decision = Column(String(50), nullable=False)  # ALLOW, DENY, REQUIRE_APPROVAL, REDACT
    effect = Column(String(20), nullable=False, default="allow")

    # Priority and ordering
    priority = Column(Integer, nullable=False, default=100)
    order = Column(Integer, nullable=True)  # Explicit ordering within priority

    # Status
    enabled = Column(Boolean, nullable=False, default=True)

    # Conditions (stored as JSON)
    conditions = Column(JSON, nullable=True)

    # Metadata
    metadata_json = Column(JSON, nullable=True)

    # Relationships
    agent = relationship("Agent")
    evaluations = relationship("PolicyEvaluation", back_populates="policy")

    @hybrid_property
    def is_active(self) -> bool:
        """Check if policy is active."""
        return self.enabled

    @hybrid_property
    def decision_type(self) -> PolicyDecision:
        """Get the decision type."""
        return PolicyDecision(self.decision)

    def evaluate_conditions(self, context: dict[str, Any]) -> bool:
        """Evaluate all conditions against the context.

        Args:
            context: Evaluation context with agent, task, request data

        Returns:
            bool: True if all conditions match, False otherwise
        """
        if not self.conditions:
            return True

        # All conditions must match (AND logic)
        return all(self._evaluate_condition(condition, context) for condition in self.conditions)

    def _evaluate_condition(self, condition: dict[str, Any], context: dict[str, Any]) -> bool:
        """Evaluate a single condition.

        Condition format:
        {
            "field": "agent.risk_level",
            "operator": "eq",
            "value": "low"
        }
        """
        field = condition.get("field")
        operator = condition.get("operator")
        if "value_field" in condition and condition["value_field"] is not None:
            expected_value = self._get_nested_value(context, condition["value_field"])
        else:
            expected_value = condition.get("value")

        if not field or not operator:
            return True  # Skip invalid conditions

        # Get actual value from context using dot notation
        actual_value = self._get_nested_value(context, field)

        # Evaluate based on operator
        return self._compare_values(actual_value, operator, expected_value)

    def _get_nested_value(self, context: dict[str, Any], path: str) -> Any:
        """Get a nested value from context using dot notation."""
        keys = path.split(".")
        value = context

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                # Try to get attribute
                if hasattr(value, key):
                    value = getattr(value, key)
                else:
                    return None

            if value is None:
                return None

        return value

    def _compare_values(self, actual: Any, operator: str, expected: Any) -> bool:
        """Compare actual value with expected value using operator."""
        # Handle None values
        if actual is None and expected is not None:
            return False
        if actual is not None and expected is None:
            return False
        if actual is None and expected is None:
            return operator in ("eq", "lte", "gte")

        # Convert types for comparison
        if expected is not None:
            try:
                # Try to convert actual to expected type
                if isinstance(expected, int | float) and not isinstance(expected, bool):
                    actual = float(actual)
                elif isinstance(expected, bool):
                    actual = bool(actual)
                elif isinstance(expected, list):
                    # Keep as is for list comparison
                    pass
            except (ValueError, TypeError):
                pass

        # Operators
        operators = {
            "eq": lambda a, e: a == e,
            "neq": lambda a, e: a != e,
            "gt": lambda a, e: a > e,
            "gte": lambda a, e: a >= e,
            "lt": lambda a, e: a < e,
            "lte": lambda a, e: a <= e,
            "in": lambda a, e: a in e if isinstance(e, list) else False,
            "not_in": lambda a, e: a not in e if isinstance(e, list) else True,
            "contains": lambda a, e: (
                e in a if isinstance(a, str | list) and e is not None else False
            ),
            "startswith": lambda a, e: (
                a.startswith(str(e)) if isinstance(a, str) and e is not None else False
            ),
            "endswith": lambda a, e: (
                a.endswith(str(e)) if isinstance(a, str) and e is not None else False
            ),
            "regex": lambda a, e: self._regex_match(a, e),
        }

        comparator = operators.get(operator)
        if not comparator:
            return False

        return comparator(actual, expected)

    def _regex_match(self, value: str, pattern: str) -> bool:
        """Match value against regex pattern."""
        import re

        try:
            return bool(re.match(pattern, str(value)))
        except re.error:
            return False

    def __repr__(self) -> str:
        return f"<Policy {self.name} ({self.decision})>"

    __table_args__ = (
        Index("idx_policies_agent_action", "agent_id", "action"),
        Index("idx_policies_enabled", "enabled"),
        Index("idx_policies_priority_order", "priority", "order"),
    )


class PolicyEvaluation(BaseModel):
    """Policy evaluation audit log."""

    __tablename__ = "policy_evaluations"

    # Evaluation context
    policy_id = Column(
        PGUUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), nullable=True
    )
    agent_id = Column(
        PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=True
    )
    task_id = Column(
        PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True
    )
    # event_id = Column(PGUUID(as_uuid=True), ForeignKey("security_events.id", ondelete="CASCADE"), nullable=True)

    # Request context
    action = Column(String(100), nullable=False)
    resource = Column(String(255), nullable=True)
    method = Column(String(10), nullable=True)
    path = Column(String(255), nullable=True)

    # Evaluation result
    matched = Column(Boolean, nullable=False, default=False)
    decision = Column(String(50), nullable=False)
    reason = Column(Text, nullable=True)
    risk_score = Column(Integer, nullable=True)

    # Conditions evaluation details
    conditions_evaluated = Column(JSON, nullable=True)
    context_snapshot = Column(JSON, nullable=True)

    # Performance
    evaluation_time_ms = Column(Integer, nullable=True)

    # Relationships
    policy = relationship("Policy", back_populates="evaluations")
    agent = relationship("Agent")
    task = relationship("Task")
    # event = relationship("SecurityEvent")

    __table_args__ = (
        Index("idx_policy_evaluations_policy", "policy_id"),
        Index("idx_policy_evaluations_agent", "agent_id"),
        Index("idx_policy_evaluations_decision", "decision"),
        Index("idx_policy_evaluations_timestamp", "created_at"),
    )


class PolicyViolation(BaseModel):
    """Policy violation tracking for security monitoring."""

    __tablename__ = "policy_violations"

    # Violation context
    policy_id = Column(
        PGUUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), nullable=True
    )
    agent_id = Column(
        PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=True
    )
    task_id = Column(
        PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True
    )
    # event_id = Column(PGUUID(as_uuid=True), ForeignKey("security_events.id", ondelete="CASCADE"), nullable=True)

    # Violation details
    action = Column(String(100), nullable=False)
    resource = Column(String(255), nullable=True)
    violation_type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False, default="medium")
    description = Column(Text, nullable=True)

    # Context
    context_snapshot = Column(JSON, nullable=True)
    risk_score = Column(Integer, nullable=True)

    # Resolution
    resolved = Column(Boolean, nullable=False, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(255), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Relationships
    policy = relationship("Policy")
    agent = relationship("Agent")
    task = relationship("Task")
    # event = relationship("SecurityEvent")

    __table_args__ = (
        Index("idx_policy_violations_agent", "agent_id"),
        Index("idx_policy_violations_severity", "severity"),
        Index("idx_policy_violations_resolved", "resolved"),
        Index("idx_policy_violations_timestamp", "created_at"),
    )
