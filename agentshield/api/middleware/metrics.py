"""
Metrics middleware for collecting request metrics.
"""

import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ...core.logging import get_logger
from ...infrastructure.metrics.prometheus import record_blocked_request, record_request

logger = get_logger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting request metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""
        start_time = time.time()

        # Get agent_id from headers or request state
        agent_id = request.headers.get("X-Agent-ID", "unknown")
        if hasattr(request.state, "agent_id"):
            agent_id = request.state.agent_id

        # Process request
        try:
            response = await call_next(request)

            # Record metrics
            latency = time.time() - start_time
            decision = "allow" if response.status_code < 400 else "deny"

            # Determine action from path
            action = request.url.path.split("/")[-1] if request.url.path else "unknown"

            record_request(
                agent_id=agent_id,
                decision=decision,
                action=action,
                latency=latency
            )

            # Record blocked requests
            if response.status_code == 403:
                record_blocked_request(
                    agent_id=agent_id,
                    reason="access_denied",
                    severity="high"
                )

            return response

        except Exception:
            # Record error
            latency = time.time() - start_time
            record_request(
                agent_id=agent_id,
                decision="error",
                action="unknown",
                latency=latency
            )
            raise
