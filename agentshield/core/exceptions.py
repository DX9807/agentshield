"""Custom exceptions for AgentShield."""

from typing import Any


class AgentShieldError(Exception):
    """Base exception for AgentShield."""

    def __init__(
        self,
        message: str = "An error occurred",
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


# Identity errors
class AgentNotFoundError(AgentShieldError):
    """Agent not found."""

    def __init__(self, agent_id: str):
        super().__init__(
            message=f"Agent not found: {agent_id}",
            code="AGENT_NOT_FOUND",
            status_code=404,
            details={"agent_id": agent_id},
        )


class AgentInactiveError(AgentShieldError):
    """Agent is inactive."""

    def __init__(self, agent_id: str):
        super().__init__(
            message=f"Agent is inactive: {agent_id}",
            code="AGENT_INACTIVE",
            status_code=403,
            details={"agent_id": agent_id},
        )


class InvalidCredentialsError(AgentShieldError):
    """Invalid credentials."""

    def __init__(self):
        super().__init__(
            message="Invalid credentials",
            code="INVALID_CREDENTIALS",
            status_code=401,
        )


# Task errors
class TaskNotFoundError(AgentShieldError):
    """Task not found."""

    def __init__(self, task_id: str):
        super().__init__(
            message=f"Task not found: {task_id}",
            code="TASK_NOT_FOUND",
            status_code=404,
            details={"task_id": task_id},
        )


class TaskExpiredError(AgentShieldError):
    """Task has expired."""

    def __init__(self, task_id: str):
        super().__init__(
            message=f"Task has expired: {task_id}",
            code="TASK_EXPIRED",
            status_code=403,
            details={"task_id": task_id},
        )


# Policy errors
class PolicyNotFoundError(AgentShieldError):
    """Policy not found."""

    def __init__(self, policy_id: str):
        super().__init__(
            message=f"Policy not found: {policy_id}",
            code="POLICY_NOT_FOUND",
            status_code=404,
            details={"policy_id": policy_id},
        )


class PolicyEvaluationError(AgentShieldError):
    """Error evaluating policy."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            code="POLICY_EVALUATION_ERROR",
            status_code=500,
            details=details or {},
        )


# Gateway errors
class GatewayError(AgentShieldError):
    """Gateway error."""

    def __init__(self, message: str, status_code: int = 502, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            code="GATEWAY_ERROR",
            status_code=status_code,
            details=details or {},
        )


class BlockedRequestError(AgentShieldError):
    """Request blocked by security policy."""

    def __init__(self, reason: str, risk_score: int, details: dict[str, Any] | None = None):
        self.risk_score = risk_score
        super().__init__(
            message=f"Request blocked: {reason}",
            code="BLOCKED_REQUEST",
            status_code=403,
            details={
                "reason": reason,
                "risk_score": risk_score,
                **(details or {}),
            },
        )


# Capability errors
class CapabilityNotFoundError(AgentShieldError):
    """Capability not found."""

    def __init__(self, capability_id: str):
        super().__init__(
            message=f"Capability not found: {capability_id}",
            code="CAPABILITY_NOT_FOUND",
            status_code=404,
            details={"capability_id": capability_id},
        )


class InsufficientCapabilitiesError(AgentShieldError):
    """Agent lacks required capability."""

    def __init__(self, required_capability: str):
        super().__init__(
            message=f"Agent lacks required capability: {required_capability}",
            code="INSUFFICIENT_CAPABILITIES",
            status_code=403,
            details={"required_capability": required_capability},
        )


# Data security errors
class SensitiveDataError(AgentShieldError):
    """Sensitive data detected."""

    def __init__(self, classification: str, patterns: list):
        super().__init__(
            message=f"Sensitive data detected: {classification}",
            code="SENSITIVE_DATA_DETECTED",
            status_code=403,
            details={"classification": classification, "patterns": patterns},
        )
