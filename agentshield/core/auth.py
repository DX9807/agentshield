"""Authentication utilities."""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from uuid import UUID
import jwt
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import settings
from .exceptions import InvalidCredentialsError

security = HTTPBearer(auto_error=False)


def create_agent_token(data: Dict[str, Any]) -> str:
    """Create a JWT token for an agent."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.AGENT_TOKEN_EXPIRATION_MINUTES)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "agent",
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """Get current authenticated user/agent from JWT token."""
    if not credentials:
        # For development, allow unauthenticated requests
        # In production, this should be required
        return {"username": "system", "type": "system"}
    
    token = credentials.credentials
    payload = decode_token(token)
    
    # Check token type
    if payload.get("type") == "agent":
        return {
            "agent_id": payload.get("agent_id"),
            "agent_name": payload.get("agent_name"),
            "capabilities": payload.get("capabilities", []),
            "type": "agent",
        }
    elif payload.get("type") == "user":
        return {
            "username": payload.get("sub"),
            "type": "user",
            "roles": payload.get("roles", []),
        }
    else:
        raise InvalidCredentialsError()


async def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Require admin role."""
    if current_user.get("type") != "user" or "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def get_agent_from_token(token: str) -> Dict[str, Any]:
    """Get agent data from JWT token."""
    payload = decode_token(token)
    if payload.get("type") != "agent":
        raise InvalidCredentialsError()
    
    return {
        "agent_id": UUID(payload.get("agent_id")),
        "agent_name": payload.get("agent_name"),
        "capabilities": payload.get("capabilities", []),
        "environment": payload.get("environment"),
    }