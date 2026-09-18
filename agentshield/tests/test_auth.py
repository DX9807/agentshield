"""Unit tests for authentication module."""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from agentshield.core.auth import (
    create_agent_token,
    decode_token,
    get_agent_from_token,
    get_current_user,
    require_admin,
)


class TestAuth:
    """Test suite for authentication functions."""

    def test_create_and_decode_agent_token(self) -> None:
        """Test token creation and decoding."""
        agent_id = str(uuid4())
        token_data = {
            "agent_id": agent_id,
            "agent_name": "billing-bot",
            "capabilities": ["read_order", "read_customer"],
            "environment": "development",
        }

        token = create_agent_token(token_data)
        assert isinstance(token, str)
        assert len(token) > 50

        payload = decode_token(token)
        assert payload["agent_id"] == agent_id
        assert payload["agent_name"] == "billing-bot"
        assert payload["type"] == "agent"
        assert "read_order" in payload["capabilities"]

    def test_get_agent_from_token(self) -> None:
        """Test extracting agent data from valid token."""
        agent_id = str(uuid4())
        token_data = {
            "agent_id": agent_id,
            "agent_name": "crawler",
            "capabilities": ["read_file"],
            "environment": "staging",
        }
        token = create_agent_token(token_data)
        agent_info = get_agent_from_token(token)

        assert str(agent_info["agent_id"]) == agent_id
        assert agent_info["agent_name"] == "crawler"
        assert agent_info["capabilities"] == ["read_file"]
        assert agent_info["environment"] == "staging"

    def test_decode_invalid_token(self) -> None:
        """Test that invalid tokens raise HTTPException 401."""
        with pytest.raises(HTTPException) as exc_info:
            decode_token("this.is.invalid")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_dev_fallback(self) -> None:
        """Test unauthenticated development fallback."""
        user = await get_current_user(None)
        assert user["type"] == "user"
        assert "admin" in user.get("roles", [])

    @pytest.mark.asyncio
    async def test_require_admin_success(self) -> None:
        """Test require_admin with admin role."""
        admin_user = {"username": "alice", "type": "user", "roles": ["admin"]}
        result = await require_admin(admin_user)
        assert result == admin_user

    @pytest.mark.asyncio
    async def test_require_admin_forbidden(self) -> None:
        """Test require_admin fails for non-admin."""
        non_admin = {"username": "bob", "type": "user", "roles": ["viewer"]}
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(non_admin)
        assert exc_info.value.status_code == 403
