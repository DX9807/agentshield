"""Core module for AgentShield."""

from .config import settings
from .logging import get_logger, setup_logging
from .exceptions import (
    AgentShieldError,
    AgentNotFoundError,
    AgentInactiveError,
    InvalidCredentialsError,
    CapabilityNotFoundError,
)
from .auth import (
    create_agent_token,
    decode_token,
    get_current_user,
    require_admin,
    get_agent_from_token,
)

__all__ = [
    "settings",
    "get_logger",
    "setup_logging",
    "AgentShieldError",
    "AgentNotFoundError",
    "AgentInactiveError",
    "InvalidCredentialsError",
    "CapabilityNotFoundError",
    "create_agent_token",
    "decode_token",
    "get_current_user",
    "require_admin",
    "get_agent_from_token",
]

