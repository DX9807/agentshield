"""Gateway service for intercepting and forwarding requests."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx

from ...core.config import settings
from ...core.exceptions import (
    AgentInactiveError,
    AgentNotFoundError,
    BlockedRequestError,
    GatewayError,
    InvalidCredentialsError,
    TaskExpiredError,
    TaskNotFoundError,
)
from ...core.logging import get_logger
from ...domain.agent.models import PredefinedCapabilities
from ...domain.agent.service import AgentService
from ...domain.policy.engine import PolicyEngine
from ...domain.policy.models import PolicyDecision
from ...domain.risk.engine import RiskEngine
from ...domain.task.service import TaskService
from ...infrastructure.cache.redis_client import redis_client
from ...schemas.gateway import (
    GatewayForwardRequest,
    GatewayResponse,
)
from ...schemas.policy import PolicyEvaluationRequest

logger = get_logger(__name__)


class GatewayService:
    """Core gateway service for request interception and forwarding."""

    def __init__(self, session: Any) -> None:
        self.session = session
        self.agent_service: AgentService | None = None
        self.task_service: TaskService | None = None
        self.policy_engine: PolicyEngine | None = None
        self.risk_engine: RiskEngine | None = None

    async def initialize(self) -> None:
        """Initialize gateway service dependencies."""
        if not self.agent_service:
            self.agent_service = await AgentService.create(self.session)
        if not self.task_service:
            self.task_service = await TaskService.create(self.session)
        if not self.policy_engine:
            self.policy_engine = await PolicyEngine.create(self.session)
        if not self.risk_engine:
            self.risk_engine = RiskEngine()

    @classmethod
    async def create(cls, session: Any) -> "GatewayService":
        """Create a new GatewayService instance."""
        service = cls(session)
        await service.initialize()
        return service

    async def process_request(
        self,
        gateway_request: GatewayForwardRequest,
        request_id: str,
    ) -> GatewayResponse:
        """Process a request through the gateway.

        Args:
            gateway_request: The request to process
            request_id: Unique request ID for tracking

        Returns:
            GatewayResponse: The gateway decision and response
        """
        start_time = datetime.now(UTC)

        try:
            # Step 1: Validate identity
            agent = await self._validate_agent(
                gateway_request.agent_id,
                gateway_request.api_key,
            )

            # Step 2: Validate task
            task = await self._validate_task(
                gateway_request.task_id,
                gateway_request.agent_id,
            )

            # Step 3: Parse and validate request
            parsed_request = await self._parse_request(gateway_request)

            # Step 4: Get agent capabilities
            agent_capabilities = await self.agent_service.get_agent_capabilities(agent.id)
            agent_cap_names = [cap["name"] for cap in agent_capabilities]

            # Step 5: Get task capabilities
            task_capabilities = await self.task_service.get_task_capabilities(task.id)
            task_cap_names = [cap["name"] for cap in task_capabilities]

            # Step 6: Determine required capability
            required_capability = await self._determine_required_capability(
                parsed_request["method"],
                parsed_request["path"],
                parsed_request["resource"],
            )

            # Step 7: Check capabilities
            if required_capability:
                await self._validate_capabilities(
                    agent_cap_names,
                    task_cap_names,
                    required_capability,
                )

            # Step 8: Evaluate policies
            policy_result = await self._evaluate_policies(
                agent=agent,
                task=task,
                parsed_request=parsed_request,
                gateway_request=gateway_request,
                required_capability=required_capability,
            )

            # Step 9: Check rate limits
            await self._check_rate_limit(
                agent_id=agent.id,
                task_id=task.id,
            )

            # Step 10: Calculate risk score
            risk_score = await self._calculate_risk_score(
                agent=agent,
                task=task,
                parsed_request=parsed_request,
                policy_result=policy_result,
            )

            # Step 11: Make final decision
            decision = self._make_decision(
                policy_result=policy_result,
                risk_score=risk_score,
                gateway_request=gateway_request,
            )

            elapsed_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

            # Step 12: Enforce decision (BLOCK or REQUIRE_APPROVAL do not forward)
            if decision["action"] in ("BLOCK", "REQUIRE_APPROVAL"):
                return GatewayResponse(
                    request_id=request_id,
                    decision=decision["action"],
                    reason=decision["reason"],
                    risk_score=risk_score,
                    response=None,
                    elapsed_ms=elapsed_ms,
                )

            # Step 13: Forward request
            response = await self._forward_request(
                gateway_request=gateway_request,
                parsed_request=parsed_request,
                decision=decision,
            )

            # Step 14: Process response
            processed_response = await self._process_response(
                response=response,
                gateway_request=gateway_request,
                decision=decision,
            )

            # Step 15: Log audit event
            await self._log_audit_event(
                request_id=request_id,
                agent=agent,
                task=task,
                gateway_request=gateway_request,
                parsed_request=parsed_request,
                decision=decision,
                response=processed_response,
                risk_score=risk_score,
                elapsed_ms=int((datetime.now(UTC) - start_time).total_seconds() * 1000),
            )

            # Step 16: Update metrics
            elapsed_sec = (datetime.now(UTC) - start_time).total_seconds()
            req_action = getattr(gateway_request, "action", None) or getattr(gateway_request, "method", "UNKNOWN")
            await self._update_metrics(
                decision=decision,
                risk_score=risk_score,
                agent_id=str(agent.id) if agent else "unknown",
                action=req_action,
                latency=elapsed_sec,
            )

            return GatewayResponse(
                request_id=request_id,
                decision=decision["action"],
                reason=decision["reason"],
                risk_score=risk_score,
                response=processed_response,
                elapsed_ms=int(elapsed_sec * 1000),
            )

        except BlockedRequestError as e:
            extracted_risk = getattr(e, "risk_score", None)
            if extracted_risk is None and hasattr(e, "details") and isinstance(e.details, dict):
                extracted_risk = e.details.get("risk_score")
            final_risk = extracted_risk or 80
            elapsed_sec = (datetime.now(UTC) - start_time).total_seconds()
            req_action = getattr(gateway_request, "action", None) or getattr(gateway_request, "method", "UNKNOWN")
            await self._update_metrics(
                decision={"action": "block", "reason": e.message},
                risk_score=final_risk,
                agent_id=str(gateway_request.agent_id),
                action=req_action,
                latency=elapsed_sec,
            )
            return GatewayResponse(
                request_id=request_id,
                decision="BLOCK",
                reason=e.message,
                risk_score=final_risk,
                response=None,
                elapsed_ms=int(elapsed_sec * 1000),
                error=e.message,
            )
        except (
            TaskNotFoundError,
            TaskExpiredError,
            AgentNotFoundError,
            AgentInactiveError,
            InvalidCredentialsError,
        ) as e:
            msg = getattr(e, "message", str(e))
            return GatewayResponse(
                request_id=request_id,
                decision="BLOCK",
                reason=msg,
                risk_score=90,
                response=None,
                elapsed_ms=int((datetime.now(UTC) - start_time).total_seconds() * 1000),
                error=msg,
            )
        except Exception as e:
            logger.error(
                f"Gateway request failed: {e}",
                extra={
                    "request_id": request_id,
                    "agent_id": str(gateway_request.agent_id),
                    "task_id": str(gateway_request.task_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            return GatewayResponse(
                request_id=request_id,
                decision="BLOCK",
                reason=f"Gateway error: {e}",
                risk_score=100,
                response=None,
                elapsed_ms=int((datetime.now(UTC) - start_time).total_seconds() * 1000),
                error=str(e),
            )

    async def _validate_agent(self, agent_id: UUID, api_key: str) -> Any:
        """Validate agent identity."""
        auth_result = await self.agent_service.authenticate_agent(agent_id, api_key)
        return auth_result["agent"]

    async def _validate_task(self, task_id: UUID, agent_id: UUID) -> Any:
        """Validate task."""
        task = await self.task_service.get_task_by_id(task_id)
        if not task:
            raise TaskNotFoundError(str(task_id))

        if not task.is_active:
            raise TaskExpiredError(str(task_id))

        if task.agent_id != agent_id:
            raise BlockedRequestError(
                "Task does not belong to agent",
                risk_score=85,
            )

        return task

    async def _parse_request(self, gateway_request: GatewayForwardRequest) -> dict[str, Any]:
        """Parse and validate request."""
        target_url = gateway_request.target_url
        path = (
            target_url.split("://")[-1].split("/", 1)[1]
            if "/" in target_url.split("://")[-1]
            else ""
        )
        method = gateway_request.method.upper()
        body = gateway_request.body
        resource = path.split("/")[-1] if path else None

        return {
            "method": method,
            "path": path,
            "resource": resource,
            "body": body,
            "data": body,
            "headers": gateway_request.headers,
            "query_params": gateway_request.query_params,
            "target_url": target_url,
        }

    async def _determine_required_capability(
        self,
        method: str,
        path: str,
        resource: str | None = None,
    ) -> str | None:
        """Determine the required predefined capability for a request."""
        path_lower = path.lower()
        method_upper = method.upper()

        if "refund" in path_lower:
            return PredefinedCapabilities.CREATE_REFUND
        elif "payroll" in path_lower:
            return PredefinedCapabilities.ACCESS_PAYROLL
        elif "admin" in path_lower:
            return PredefinedCapabilities.ACCESS_ADMIN_API
        elif "iam" in path_lower or "user" in path_lower:
            return PredefinedCapabilities.CREATE_IAM_USER
        elif "email" in path_lower:
            return PredefinedCapabilities.SEND_EMAIL
        elif "notification" in path_lower:
            return PredefinedCapabilities.SEND_NOTIFICATION
        elif "customer" in path_lower:
            if method_upper == "GET":
                return PredefinedCapabilities.READ_CUSTOMER
            elif method_upper == "DELETE":
                return PredefinedCapabilities.DELETE_CUSTOMER
            else:
                return PredefinedCapabilities.WRITE_CUSTOMER
        elif "order" in path_lower:
            if method_upper == "GET":
                return PredefinedCapabilities.READ_ORDER
            elif method_upper == "DELETE":
                return PredefinedCapabilities.DELETE_ORDER
            else:
                return PredefinedCapabilities.WRITE_ORDER
        elif "ticket" in path_lower:
            if method_upper == "GET":
                return PredefinedCapabilities.READ_TICKET
            elif method_upper == "POST":
                return PredefinedCapabilities.CREATE_TICKET
            else:
                return PredefinedCapabilities.UPDATE_TICKET
        elif "invoice" in path_lower:
            if method_upper == "GET":
                return PredefinedCapabilities.READ_INVOICE
            else:
                return PredefinedCapabilities.WRITE_INVOICE
        elif "file" in path_lower:
            if method_upper == "GET":
                return PredefinedCapabilities.READ_FILE
            elif method_upper == "DELETE":
                return PredefinedCapabilities.DELETE_FILE
            else:
                return PredefinedCapabilities.WRITE_FILE

        return None

    async def _validate_capabilities(
        self,
        agent_capabilities: list[str],
        task_capabilities: list[str],
        required_capability: str,
    ) -> None:
        """Validate that agent and task have the required capability."""
        if required_capability not in agent_capabilities:
            raise BlockedRequestError(
                f"Agent lacks capability: {required_capability}",
                risk_score=80,
                details={"required_capability": required_capability},
            )

        if required_capability not in task_capabilities:
            raise BlockedRequestError(
                f"Task lacks capability: {required_capability}",
                risk_score=75,
                details={"required_capability": required_capability},
            )

    async def _evaluate_policies(
        self,
        agent: Any,
        task: Any,
        parsed_request: dict[str, Any],
        gateway_request: GatewayForwardRequest,
        required_capability: str | None = None,
    ) -> dict[str, Any]:
        """Evaluate policies for the request."""
        # Evaluation context
        context = {
            "agent": {
                "id": str(agent.id),
                "name": agent.name,
                "risk_level": (
                    agent.risk_level.value
                    if hasattr(agent.risk_level, "value")
                    else str(agent.risk_level)
                ),
                "environment": (
                    agent.environment.value
                    if hasattr(agent.environment, "value")
                    else str(agent.environment)
                ),
            },
            "task": {
                "id": str(task.id),
                "intent_type": task.intent_type,
                "context": task.context or {},
            },
            "request": parsed_request,
        }

        # Build candidate actions in priority order: required_capability, task.intent_type, method
        candidate_actions: list[str] = []
        if required_capability:
            candidate_actions.append(required_capability)
        if (
            task
            and getattr(task, "intent_type", None)
            and task.intent_type not in candidate_actions
        ):
            candidate_actions.append(task.intent_type)
        method_action = parsed_request["method"].lower()
        if method_action not in candidate_actions:
            candidate_actions.append(method_action)

        best_result = None
        for action in candidate_actions:
            policy_request = PolicyEvaluationRequest(
                agent_id=agent.id,
                task_id=task.id,
                action=action,
                resource=parsed_request["resource"],
                method=parsed_request["method"],
                path=parsed_request["path"],
                request_data=parsed_request["body"],
            )
            eval_result = await self.policy_engine.evaluate(policy_request, context)
            if eval_result.matched_policy_id is not None:
                best_result = eval_result
                break
            if best_result is None:
                best_result = eval_result

        result = best_result

        return {
            "decision": result.decision,
            "matched_policy_id": result.matched_policy_id,
            "matched_policy_name": result.matched_policy_name,
            "reason": result.reason,
            "risk_score": result.risk_score,
        }

    async def _check_rate_limit(self, agent_id: UUID, task_id: UUID) -> None:
        """Check rate limits."""
        if not settings.RATE_LIMIT_ENABLED:
            return

        try:
            # Agent-level rate limiting
            agent_key = f"rate_limit:agent:{agent_id}"
            agent_count = await redis_client.incr(agent_key)

            if agent_count == 1:
                await redis_client.expire(agent_key, 60)

            if agent_count and agent_count > settings.RATE_LIMIT_REQUESTS_PER_MINUTE:
                raise BlockedRequestError(
                    "Rate limit exceeded for agent",
                    risk_score=40,
                    details={"limit": settings.RATE_LIMIT_REQUESTS_PER_MINUTE},
                )

            # Task-level rate limiting (stricter)
            task_key = f"rate_limit:task:{task_id}"
            task_count = await redis_client.incr(task_key)

            if task_count == 1:
                await redis_client.expire(task_key, 60)

            task_limit = max(settings.RATE_LIMIT_REQUESTS_PER_MINUTE // 2, 1)
            if task_count and task_count > task_limit:
                raise BlockedRequestError(
                    "Rate limit exceeded for task",
                    risk_score=50,
                    details={"limit": task_limit},
                )
        except BlockedRequestError:
            raise
        except Exception as e:
            logger.warning(f"Rate limiting check skipped due to Redis error: {e}")

    async def _calculate_risk_score(
        self, agent: Any, task: Any, parsed_request: dict[str, Any], policy_result: dict[str, Any]
    ) -> int:
        """Calculate risk score."""
        expires_at = task.expires_at
        now = datetime.now(UTC)
        if expires_at.tzinfo is None:
            task_expires_in = int((expires_at - datetime.utcnow()).total_seconds() / 60)
        else:
            task_expires_in = int((expires_at - now).total_seconds() / 60)

        decision_val = policy_result["decision"]
        decision_str = decision_val.value if hasattr(decision_val, "value") else str(decision_val)

        agent_risk = (
            agent.risk_level.value if hasattr(agent.risk_level, "value") else str(agent.risk_level)
        )
        task_prio = task.priority.value if hasattr(task.priority, "value") else str(task.priority)

        risk_context = {
            "agent_risk_level": agent_risk,
            "task_priority": task_prio,
            "action": parsed_request["method"],
            "resource": parsed_request["resource"],
            "policy_decision": decision_str,
            "policy_risk": policy_result.get("risk_score", 0),
            "task_expires_in": task_expires_in,
        }

        risk_score = await self.risk_engine.calculate(risk_context)
        return risk_score

    def _make_decision(
        self, policy_result: dict[str, Any], risk_score: int, gateway_request: GatewayForwardRequest
    ) -> dict[str, Any]:
        """Make final decision."""
        decision_val = policy_result["decision"]
        decision_str = (
            decision_val.value if hasattr(decision_val, "value") else str(decision_val).lower()
        )

        # Check policy decision
        if decision_str == PolicyDecision.DENY.value:
            return {
                "action": "BLOCK",
                "reason": f"Policy denied: {policy_result['reason']}",
                "severity": "HIGH",
            }

        if decision_str == PolicyDecision.REQUIRE_APPROVAL.value:
            return {
                "action": "REQUIRE_APPROVAL",
                "reason": f"Policy requires approval: {policy_result['reason']}",
                "severity": "MEDIUM",
            }

        # Check risk score
        if risk_score >= 80:
            return {
                "action": "BLOCK",
                "reason": f"Risk score too high: {risk_score}",
                "severity": "CRITICAL",
            }
        elif risk_score >= 60:
            return {
                "action": "REQUIRE_APPROVAL",
                "reason": f"Risk score requires approval: {risk_score}",
                "severity": "HIGH",
            }
        elif risk_score >= 30:
            return {
                "action": "ALLOW",
                "reason": f"Risk score acceptable with monitoring: {risk_score}",
                "severity": "LOW",
                "require_logging": True,
            }
        else:
            return {
                "action": "ALLOW",
                "reason": f"Risk score acceptable: {risk_score}",
                "severity": "LOW",
                "require_logging": False,
            }

    async def _forward_request(
        self,
        gateway_request: GatewayForwardRequest,
        parsed_request: dict[str, Any],
        decision: dict[str, Any],
    ) -> httpx.Response:
        """Forward request to target API."""
        try:
            url = gateway_request.target_url
            headers = dict(gateway_request.headers or {})
            headers.pop("X-API-Key", None)
            headers.pop("X-Task-ID", None)

            async with httpx.AsyncClient(
                timeout=httpx.Timeout(settings.GATEWAY_REQUEST_TIMEOUT),
                follow_redirects=True,
            ) as client:
                response = await client.request(
                    method=gateway_request.method,
                    url=url,
                    headers=headers,
                    params=gateway_request.query_params,
                    json=parsed_request["body"] if parsed_request["body"] else None,
                )
                return response
        except httpx.TimeoutException:
            raise GatewayError("Target API timeout", status_code=504)
        except httpx.ConnectError:
            raise GatewayError("Failed to connect to target API", status_code=502)
        except Exception as e:
            raise GatewayError(f"Request forwarding failed: {e}")

    async def _process_response(
        self,
        response: httpx.Response,
        gateway_request: GatewayForwardRequest,
        decision: dict[str, Any],
    ) -> dict[str, Any]:
        """Process and sanitize response."""
        try:
            body = response.json()
        except Exception:
            body = response.text

        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": body,
            "content_type": response.headers.get("content-type"),
            "size": len(response.content),
        }

    async def _log_audit_event(
        self,
        request_id: str,
        agent: Any,
        task: Any,
        gateway_request: GatewayForwardRequest,
        parsed_request: dict[str, Any],
        decision: dict[str, Any],
        response: dict[str, Any] | None,
        risk_score: int,
        elapsed_ms: int,
    ) -> None:
        """Log audit event."""
        event = {
            "request_id": request_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "agent_id": str(agent.id),
            "agent_name": agent.name,
            "task_id": str(task.id),
            "task_intent": task.intent_type,
            "user_id": task.user_id,
            "method": parsed_request["method"],
            "path": parsed_request["path"],
            "target_url": gateway_request.target_url,
            "decision": decision["action"],
            "decision_reason": decision["reason"],
            "risk_score": risk_score,
            "response_status_code": response.get("status_code") if response else None,
            "elapsed_ms": elapsed_ms,
            "policy_matched": decision.get("matched_policy_name"),
        }

        logger.info(
            f"Gateway audit event: {event}",
            extra=event,
        )

    async def _update_metrics(
        self,
        decision: dict[str, Any],
        risk_score: int,
        agent_id: str = "unknown",
        action: str = "unknown",
        latency: float = 0.0,
    ) -> None:
        """Update metrics."""
        try:
            from ...infrastructure.metrics.prometheus import (
                record_blocked_request,
                record_request,
                record_risk_score,
            )

            dec_action = str(decision.get("action", "allow")).lower()
            env = getattr(settings, "APP_ENV", "development")
            record_request(
                agent_id=agent_id,
                decision=dec_action,
                action=action,
                environment=env,
                latency=latency,
            )
            record_risk_score(
                agent_id=agent_id,
                score=risk_score,
                decision=dec_action,
            )
            if dec_action == "block":
                record_blocked_request(
                    agent_id=agent_id,
                    reason=str(decision.get("reason", "unknown")),
                    severity="high" if risk_score >= 80 else "medium",
                )
        except Exception as e:
            logger.debug(f"Failed to update metrics: {e}")

