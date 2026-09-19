"""Gateway service for intercepting and forwarding requests."""

from typing import Optional, Dict, Any, Tuple, List
from uuid import UUID
from datetime import datetime
import json
import asyncio
import httpx
from fastapi import Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from ...core.config import settings
from ...core.logging import get_logger
from ...core.exceptions import (
    BlockedRequestError,
    GatewayError,
    TaskNotFoundError,
    TaskExpiredError,
    AgentNotFoundError,
)
from ...infrastructure.cache.redis_client import redis_client
from ...domain.agent.service import AgentService
from ...domain.task.service import TaskService
from ...domain.policy.engine import PolicyEngine
from ...domain.policy.models import PolicyDecision
from ...domain.risk.engine import RiskEngine
from ...schemas.gateway import (
    GatewayRequest,
    GatewayResponse,
    GatewayForwardRequest,
)
from ...schemas.policy import PolicyEvaluationRequest

logger = get_logger(__name__)


class GatewayService:
    """Core gateway service for request interception and forwarding."""
    
    def __init__(self, session):
        self.session = session
        self.agent_service = None
        self.task_service = None
        self.policy_engine = None
        self.risk_engine = None
        self.client = None
        self._cache_ttl = 300  # 5 minutes
    
    async def initialize(self):
        """Initialize gateway service dependencies."""
        if not self.agent_service:
            self.agent_service = await AgentService.create(self.session)
        if not self.task_service:
            self.task_service = await TaskService.create(self.session)
        if not self.policy_engine:
            self.policy_engine = await PolicyEngine.create(self.session)
        if not self.risk_engine:
            self.risk_engine = RiskEngine()
        if not self.client:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.GATEWAY_REQUEST_TIMEOUT),
                limits=httpx.Limits(max_keepalive_connections=10),
                follow_redirects=True,
            )
    
    @classmethod
    async def create(cls, session) -> "GatewayService":
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
        start_time = datetime.utcnow()
        
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
            
            # Step 12: Enforce decision
            if decision["action"] == "BLOCK":
                return self._create_blocked_response(
                    decision=decision,
                    request_id=request_id,
                    elapsed_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
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
                elapsed_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
            )
            
            # Step 16: Update metrics
            await self._update_metrics(decision, risk_score)
            
            return GatewayResponse(
                request_id=request_id,
                decision=decision["action"],
                reason=decision["reason"],
                risk_score=risk_score,
                response=processed_response,
                elapsed_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
            )
            
        except Exception as e:
            logger.error(
                f"Gateway request failed: {str(e)}",
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
                reason=f"Gateway error: {str(e)}",
                risk_score=100,
                response=None,
                elapsed_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
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
            raise ValueError("Task does not belong to agent")
        
        return task
    
    async def _parse_request(self, gateway_request: GatewayForwardRequest) -> Dict[str, Any]:
        """Parse and validate request."""
        # Parse URL
        target_url = gateway_request.target_url
        path = target_url.split("://")[-1].split("/", 1)[1] if "/" in target_url.split("://")[-1] else ""
        
        # Parse method
        method = gateway_request.method.upper()
        
        # Parse body
        body = gateway_request.body
        
        # Extract resource
        resource = path.split("/")[-1] if path else None
        
        return {
            "method": method,
            "path": path,
            "resource": resource,
            "body": body,
            "headers": gateway_request.headers,
            "query_params": gateway_request.query_params,
            "target_url": target_url,
        }
    
    async def _determine_required_capability(
        self,
        method: str,
        path: str,
        resource: Optional[str] = None,
    ) -> Optional[str]:
        """Determine the required capability for a request."""
        # Map methods to capability actions
        method_map = {
            "GET": "read",
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete",
        }
        
        action = method_map.get(method, "access")
        
        # Try to derive from path
        if "customer" in path.lower():
            return f"{action}_customer"
        elif "order" in path.lower():
            return f"{action}_order"
        elif "ticket" in path.lower():
            return f"{action}_ticket"
        elif "refund" in path.lower():
            return "create_refund"
        elif "email" in path.lower():
            return "send_email"
        elif "invoice" in path.lower():
            return "read_invoice"
        elif "payroll" in path.lower():
            return "access_payroll"
        elif "iam" in path.lower() or "user" in path.lower():
            return "create_iam_user"
        elif "admin" in path.lower():
            return "access_admin_api"
        elif "file" in path.lower():
            return f"{action}_file"
        
        return None
    
    async def _validate_capabilities(
        self,
        agent_capabilities: List[str],
        task_capabilities: List[str],
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
        agent,
        task,
        parsed_request: Dict[str, Any],
        gateway_request: GatewayForwardRequest,
    ) -> Dict[str, Any]:
        """Evaluate policies for the request."""
        policy_request = PolicyEvaluationRequest(
            agent_id=agent.id,
            task_id=task.id,
            action=parsed_request["method"].lower(),
            resource=parsed_request["resource"],
            method=parsed_request["method"],
            path=parsed_request["path"],
            request_data=parsed_request["body"],
        )
        
        # Build evaluation context
        context = {
            "agent": {
                "id": str(agent.id),
                "name": agent.name,
                "risk_level": agent.risk_level.value,
                "environment": agent.environment.value,
            },
            "task": {
                "id": str(task.id),
                "intent_type": task.intent_type,
                "context": task.context or {},
            },
            "request": parsed_request,
        }
        
        result = await self.policy_engine.evaluate(policy_request, context)
        
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
        
        # Agent-level rate limiting
        agent_key = f"rate_limit:agent:{agent_id}"
        agent_count = await redis_client.incr(agent_key)
        
        if agent_count == 1:
            await redis_client.expire(agent_key, 60)
        
        if agent_count > settings.RATE_LIMIT_REQUESTS_PER_MINUTE:
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
        
        task_limit = settings.RATE_LIMIT_REQUESTS_PER_MINUTE // 2
        if task_count > task_limit:
            raise BlockedRequestError(
                "Rate limit exceeded for task",
                risk_score=50,
                details={"limit": task_limit},
            )
    
    async def _calculate_risk_score(self, agent, task, parsed_request, policy_result) -> int:
        """Calculate risk score."""
        risk_context = {
            "agent_risk_level": agent.risk_level.value,
            "task_priority": task.priority.value,
            "action": parsed_request["method"],
            "resource": parsed_request["resource"],
            "policy_decision": policy_result["decision"].value,
            "policy_risk": policy_result.get("risk_score", 0),
            "task_expires_in": int((task.expires_at - datetime.utcnow()).total_seconds() / 60),
        }
        
        risk_score = await self.risk_engine.calculate(risk_context)
        return risk_score
    
    def _make_decision(self, policy_result, risk_score, gateway_request) -> Dict[str, Any]:
        """Make final decision."""
        # Check policy decision
        if policy_result["decision"] == PolicyDecision.DENY:
            return {
                "action": "BLOCK",
                "reason": f"Policy denied: {policy_result['reason']}",
                "severity": "HIGH",
            }
        
        if policy_result["decision"] == PolicyDecision.REQUIRE_APPROVAL:
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
    
    def _create_blocked_response(self, decision, request_id, elapsed_ms) -> GatewayResponse:
        """Create a blocked response."""
        return GatewayResponse(
            request_id=request_id,
            decision="BLOCK",
            reason=decision["reason"],
            risk_score=100,
            response=None,
            elapsed_ms=elapsed_ms,
        )
    
    async def _forward_request(self, gateway_request, parsed_request, decision) -> httpx.Response:
        """Forward request to target API."""
        try:
            # Prepare request
            url = gateway_request.target_url
            
            # Build headers
            headers = gateway_request.headers or {}
            # Remove AgentShield specific headers
            headers.pop("X-API-Key", None)
            headers.pop("X-Task-ID", None)
            
            # Forward request
            response = await self.client.request(
                method=gateway_request.method,
                url=url,
                headers=headers,
                params=gateway_request.query_params,
                json=parsed_request["body"] if parsed_request["body"] else None,
                timeout=settings.GATEWAY_REQUEST_TIMEOUT,
            )
            
            return response
            
        except httpx.TimeoutException:
            raise GatewayError("Target API timeout", status_code=504)
        except httpx.ConnectError:
            raise GatewayError("Failed to connect to target API", status_code=502)
        except Exception as e:
            raise GatewayError(f"Request forwarding failed: {str(e)}")
    
    async def _process_response(
        self,
        response: httpx.Response,
        gateway_request: GatewayForwardRequest,
        decision: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process and sanitize response."""
        # Parse response body
        try:
            body = response.json()
        except:
            body = response.text
        
        # Check for sensitive data
        # TODO: Implement data classification
        
        # Build response
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
        agent,
        task,
        gateway_request,
        parsed_request,
        decision,
        response,
        risk_score,
        elapsed_ms,
    ) -> None:
        """Log audit event."""
        event = {
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
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
        
        # Store in database
        # TODO: Implement audit service
        
        # Send to Kafka
        # TODO: Implement Kafka integration
    
    async def _update_metrics(self, decision, risk_score) -> None:
        """Update metrics."""
        # TODO: Implement Prometheus metrics
        pass