"""Core module for AgentShield."""

from .auth import (
    create_agent_token,
    decode_token,
    get_agent_from_token,
    get_current_user,
    require_admin,
)
from .config import settings
from .exceptions import (
    AgentInactiveError,
    AgentNotFoundError,
    AgentShieldError,
    CapabilityNotFoundError,
    InvalidCredentialsError,
    TaskExpiredError,
    TaskNotFoundError,
)
from .logging import get_logger, setup_logging

__all__ = [
    "settings",
    "get_logger",
    "setup_logging",
    "AgentShieldError",
    "AgentNotFoundError",
    "AgentInactiveError",
    "InvalidCredentialsError",
    "CapabilityNotFoundError",
    "TaskNotFoundError",
    "TaskExpiredError",
    "create_agent_token",
    "decode_token",
    "get_current_user",
    "require_admin",
    "get_agent_from_token",
]
