"""Policy evaluation engine."""

from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
import json
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from ...core.exceptions import PolicyEvaluationError
from ...core.logging import get_logger
from ...infrastructure.cache.redis_client import redis_client
from .models import Policy, PolicyDecision, PolicyEvaluation
from ...schemas.policy import PolicyEvaluationRequest, PolicyEvaluationResponse

logger = get_logger(__name__)


class PolicyEngine:
    """Core policy evaluation engine."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache_ttl = 300  # 5 minutes
    
    @classmethod
    async def create(cls, session: AsyncSession) -> "PolicyEngine":
        """Create a new PolicyEngine instance."""
        return cls(session)
    
    async def evaluate(
        self,
        request: PolicyEvaluationRequest,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyEvaluationResponse:
        """Evaluate a request against all applicable policies.
        
        Returns:
            PolicyEvaluationResponse with decision and details
            
        Raises:
            PolicyEvaluationError: If evaluation fails
        """
        start_time = datetime.utcnow()
        
        try:
            # Build evaluation context
            eval_context = await self._build_evaluation_context(request, context)
            
            # Get applicable policies
            policies = await self._get_applicable_policies(
                agent_id=request.agent_id,
                action=request.action,
            )
            
            if not policies:
                # No policies found - deny by default
                logger.warning(
                    "No policies found for action",
                    extra={
                        "agent_id": str(request.agent_id),
                        "action": request.action,
                    }
                )
                return PolicyEvaluationResponse(
                    decision=PolicyDecision.DENY,
                    matched_policy_id=None,
                    matched_policy_name=None,
                    reason="No applicable policy found - deny by default",
                    risk_score=50,
                )
            
            # Evaluate each policy in priority order
            for policy in policies:
                if not policy.enabled:
                    continue
                
                # Evaluate conditions
                conditions_matched = policy.evaluate_conditions(eval_context)
                
                if conditions_matched:
                    # Policy matched
                    decision = PolicyDecision(policy.decision)
                    
                    # Log evaluation
                    await self._log_evaluation(
                        policy=policy,
                        request=request,
                        eval_context=eval_context,
                        matched=True,
                        decision=decision,
                        evaluation_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                    )
                    
                    # Calculate risk score
                    risk_score = await self._calculate_risk_score(
                        policy=policy,
                        request=request,
                        context=eval_context,
                    )
                    
                    return PolicyEvaluationResponse(
                        decision=decision,
                        matched_policy_id=policy.id,
                        matched_policy_name=policy.name,
                        reason=f"Matched policy: {policy.name}",
                        risk_score=risk_score,
                    )
            
            # No policies matched - deny by default
            logger.info(
                "No policies matched",
                extra={
                    "agent_id": str(request.agent_id),
                    "action": request.action,
                    "policies_evaluated": len(policies),
                }
            )
            
            return PolicyEvaluationResponse(
                decision=PolicyDecision.DENY,
                matched_policy_id=None,
                matched_policy_name=None,
                reason="No matching policy found - deny by default",
                risk_score=50,
            )
            
        except Exception as e:
            logger.error(f"Policy evaluation failed: {e}", exc_info=True)
            raise PolicyEvaluationError(
                f"Policy evaluation failed: {str(e)}",
                details={"request": request.model_dump()},
            )
    
    async def evaluate_batch(
        self,
        requests: List[PolicyEvaluationRequest],
        contexts: Optional[List[Dict[str, Any]]] = None,
    ) -> List[PolicyEvaluationResponse]:
        """Evaluate multiple requests in batch."""
        results = []
        for i, request in enumerate(requests):
            context = contexts[i] if contexts else None
            result = await self.evaluate(request, context)
            results.append(result)
        return results
    
    async def _get_applicable_policies(
        self,
        agent_id: UUID,
        action: str,
    ) -> List[Policy]:
        """Get all policies applicable to the agent and action."""
        # Try cache first
        cache_key = f"policies:agent:{agent_id}:action:{action}"
        cached = await redis_client.get(cache_key)
        if cached:
            # TODO: Deserialize policies from cache
            pass
        
        # Query database
        query = select(Policy).where(
            and_(
                Policy.enabled == True,
                or_(
                    Policy.agent_id == agent_id,
                    Policy.agent_name.is_(None),  # Global policies
                ),
                Policy.action == action,
            )
        ).order_by(
            Policy.priority.asc(),
            Policy.order.asc(),
            Policy.created_at.asc(),
        )
        
        result = await self.session.execute(query)
        policies = result.scalars().all()
        
        # Cache results
        if policies:
            # TODO: Cache policies
            pass
        
        return list(policies)
    
    async def _build_evaluation_context(
        self,
        request: PolicyEvaluationRequest,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build the evaluation context."""
        # Base context
        eval_context = {
            "request": {
                "action": request.action,
                "resource": request.resource,
                "method": request.method,
                "path": request.path,
                "data": request.request_data or {},
            },
            "agent": {
                "id": str(request.agent_id),
            },
            "task": {
                "id": str(request.task_id),
            },
        }
        
        # Merge additional context
        if context:
            eval_context.update(context)
        
        return eval_context
    
    async def _calculate_risk_score(
        self,
        policy: Policy,
        request: PolicyEvaluationRequest,
        context: Dict[str, Any],
    ) -> int:
        """Calculate risk score for the evaluation."""
        base_score = 0
        
        # Risk based on policy priority
        if policy.priority < 10:
            base_score += 10
        elif policy.priority < 50:
            base_score += 5
        
        # Risk based on decision
        if policy.decision == "deny":
            base_score += 20
        elif policy.decision == "require_approval":
            base_score += 10
        
        # Risk based on action
        sensitive_actions = [
            "delete", "create", "update", "refund", "transfer",
            "iam", "admin", "access", "payroll", "secret"
        ]
        for sensitive in sensitive_actions:
            if sensitive in request.action.lower():
                base_score += 10
                break
        
        # Risk based on resource
        if request.resource and ("admin" in request.resource.lower() or 
                                 "iam" in request.resource.lower() or
                                 "secret" in request.resource.lower()):
            base_score += 15
        
        # Cap at 100
        return min(base_score, 100)
    
    async def _log_evaluation(
        self,
        policy: Policy,
        request: PolicyEvaluationRequest,
        eval_context: Dict[str, Any],
        matched: bool,
        decision: PolicyDecision,
        evaluation_time_ms: int,
    ) -> None:
        """Log policy evaluation for audit."""
        evaluation = PolicyEvaluation(
            policy_id=policy.id,
            agent_id=request.agent_id,
            task_id=request.task_id,
            action=request.action,
            resource=request.resource,
            method=request.method,
            path=request.path,
            matched=matched,
            decision=decision.value,
            reason=f"Policy matched: {policy.name}" if matched else "No match",
            risk_score=None,  # Calculated separately
            conditions_evaluated=policy.conditions,
            context_snapshot=eval_context,
            evaluation_time_ms=evaluation_time_ms,
        )
        
        self.session.add(evaluation)
        await self.session.commit()
    
    async def reload_policies(self) -> None:
        """Reload policies from database (clear cache)."""
        # Clear policy cache
        # TODO: Implement cache clearing
        logger.info("Policies reloaded")
    
    async def get_policy_statistics(self) -> Dict[str, Any]:
        """Get policy engine statistics."""
        # Count policies by decision
        query = select(Policy.decision, func.count()).group_by(Policy.decision)
        result = await self.session.execute(query)
        decision_counts = {row[0]: row[1] for row in result.all()}
        
        # Count enabled policies
        enabled_query = select(func.count()).where(Policy.enabled == True)
        enabled_result = await self.session.execute(enabled_query)
        enabled_count = enabled_result.scalar() or 0
        
        return {
            "total_policies": sum(decision_counts.values()),
            "enabled_policies": enabled_count,
            "by_decision": decision_counts,
        }