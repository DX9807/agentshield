"""Risk scoring engine."""

from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    """Risk severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskEngine:
    """Deterministic risk scoring engine."""

    def __init__(self) -> None:
        self.base_score = 10

    async def calculate(self, context: dict[str, Any]) -> int:
        """Calculate risk score based on context.

        Args:
            context: Context containing agent risk level, task priority, action,
                     resource, policy decision, etc.

        Returns:
            Calculated risk score clamped between 0 and 100.
        """
        score = self.base_score

        # Agent risk level
        agent_risk = context.get("agent_risk_level", "low")
        agent_risk_scores = {
            "low": 0,
            "medium": 10,
            "high": 25,
            "critical": 40,
        }
        score += agent_risk_scores.get(agent_risk, 0)

        # Task priority
        task_priority = context.get("task_priority", "medium")
        priority_scores = {
            "low": 0,
            "medium": 5,
            "high": 15,
            "critical": 30,
        }
        score += priority_scores.get(task_priority, 0)

        # Action sensitivity
        action = context.get("action", "GET")
        action_scores = {
            "GET": 2,
            "POST": 10,
            "PUT": 15,
            "PATCH": 12,
            "DELETE": 25,
        }
        score += action_scores.get(action.upper(), 5)

        # Resource sensitivity
        resource = context.get("resource") or ""
        sensitive_resources = {
            "customer": 5,
            "order": 5,
            "refund": 15,
            "payroll": 30,
            "iam": 35,
            "admin": 40,
            "secret": 45,
        }
        for key, value in sensitive_resources.items():
            if key in resource.lower():
                score += value
                break

        # Policy decision
        policy_decision = context.get("policy_decision", "allow")
        if policy_decision == "deny":
            score += 30
        elif policy_decision == "require_approval":
            score += 15

        # Policy risk contribution
        score += context.get("policy_risk", 0)

        # Task expiration
        expires_in = context.get("task_expires_in", 60)
        if expires_in < 5:
            score += 20
        elif expires_in < 15:
            score += 10

        # Cap between 0 and 100
        return min(max(score, 0), 100)

    def get_risk_level(self, score: int) -> RiskLevel:
        """Get risk level enum from numeric score."""
        if score >= 80:
            return RiskLevel.CRITICAL
        elif score >= 60:
            return RiskLevel.HIGH
        elif score >= 30:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
