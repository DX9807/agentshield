"""Integration tests for Gateway API endpoints."""

import secrets
from uuid import uuid4

import httpx
import pytest


@pytest.mark.asyncio
async def test_gateway_health_and_stats() -> None:
    """Test gateway health and stats endpoints."""
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        # Health
        health_res = await client.get("/api/v1/gateway/health")
        assert health_res.status_code == 200
        health_data = health_res.json()
        assert health_data["status"] == "healthy"
        assert health_data["service"] == "gateway"

        # Stats
        stats_res = await client.get("/api/v1/gateway/stats")
        assert stats_res.status_code == 200
        stats_data = stats_res.json()
        assert "total_requests" in stats_data


@pytest.mark.asyncio
async def test_gateway_forward_lifecycle() -> None:
    """Test gateway request interception, capability check, policy evaluation, and forwarding."""
    random_suffix = secrets.token_hex(4)
    agent_name = f"gw-agent-{random_suffix}"

    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        # 1. Register agent with read_order capability
        reg_res = await client.post(
            "/api/v1/agents/",
            json={
                "name": agent_name,
                "description": "Agent for Gateway Integration Testing",
                "owner": "gateway-team",
                "environment": "development",
                "risk_level": "low",
                "capabilities": ["read_order"],
            },
        )
        assert reg_res.status_code == 201
        agent_data = reg_res.json()
        agent_id = agent_data["id"]
        api_key = agent_data["api_key"]

        # 2. Create task with read_order capability
        task_res = await client.post(
            "/api/v1/tasks/",
            json={
                "agent_id": agent_id,
                "user_id": "operator-gw",
                "external_id": f"TICKET-GW-{random_suffix}",
                "intent_type": "read_order",
                "priority": "low",
                "expires_in_minutes": 60,
                "capabilities": ["read_order"],
            },
        )
        assert task_res.status_code == 201
        task_id = task_res.json()["id"]

        # 3. Test: Invalid API Key -> BLOCK
        bad_key_res = await client.post(
            "/api/v1/gateway/forward",
            json={
                "agent_id": agent_id,
                "api_key": "ak_invalidapikeythatdoesnotexist123",
                "task_id": task_id,
                "target_url": "http://localhost:8000/api/v1/health",
                "method": "GET",
            },
        )
        assert bad_key_res.status_code == 200
        bad_key_data = bad_key_res.json()
        assert bad_key_data["decision"] == "BLOCK"

        # 4. Test: Non-existent Task -> BLOCK
        bad_task_res = await client.post(
            "/api/v1/gateway/forward",
            json={
                "agent_id": agent_id,
                "api_key": api_key,
                "task_id": str(uuid4()),
                "target_url": "http://localhost:8000/api/v1/health",
                "method": "GET",
            },
        )
        assert bad_task_res.status_code == 200
        assert bad_task_res.json()["decision"] == "BLOCK"

        # 5. Test: Capability mismatch -> BLOCK
        # Target URL references /customers/101 which requires read_customer capability, but agent only has read_order
        missing_cap_res = await client.post(
            "/api/v1/gateway/forward",
            json={
                "agent_id": agent_id,
                "api_key": api_key,
                "task_id": task_id,
                "target_url": "http://localhost:8000/api/v1/customers/101",
                "method": "GET",
            },
        )
        assert missing_cap_res.status_code == 200
        missing_cap_data = missing_cap_res.json()
        assert missing_cap_data["decision"] == "BLOCK"
        assert "lacks capability" in missing_cap_data["reason"].lower()

        # 6. Create Policy that requires approval for read_order
        policy_name = f"gw-order-policy-{random_suffix}"
        policy_res = await client.post(
            "/api/v1/policies/",
            json={
                "name": policy_name,
                "agent_id": agent_id,
                "action": "read_order",
                "decision": "require_approval",
                "priority": 10,
                "enabled": True,
            },
        )
        assert policy_res.status_code == 201
        policy_id = policy_res.json()["id"]

        # Forward request matching read_order -> REQUIRE_APPROVAL
        approval_res = await client.post(
            "/api/v1/gateway/forward",
            json={
                "agent_id": agent_id,
                "api_key": api_key,
                "task_id": task_id,
                "target_url": "http://localhost:8000/api/v1/orders/101",
                "method": "GET",
            },
        )
        assert approval_res.status_code == 200
        approval_data = approval_res.json()
        assert approval_data["decision"] == "REQUIRE_APPROVAL"
        assert approval_data["response"] is None

        # 7. Update Policy to ALLOW
        await client.put(
            f"/api/v1/policies/{policy_id}",
            json={"decision": "allow"},
        )

        # Forward request matching read_order -> ALLOW and forwarded to live endpoint
        allow_res = await client.post(
            "/api/v1/gateway/forward",
            json={
                "agent_id": agent_id,
                "api_key": api_key,
                "task_id": task_id,
                "target_url": "http://localhost:8000/api/v1/health",
                "method": "GET",
            },
        )
        assert allow_res.status_code == 200
        allow_data = allow_res.json()
        assert allow_data["decision"] == "ALLOW"
        assert allow_data["response"] is not None
        assert allow_data["response"]["status_code"] == 200

        # 8. Test Batch Forwarding
        batch_res = await client.post(
            "/api/v1/gateway/batch",
            json={
                "requests": [
                    {
                        "agent_id": agent_id,
                        "api_key": api_key,
                        "task_id": task_id,
                        "target_url": "http://localhost:8000/api/v1/health",
                        "method": "GET",
                    },
                    {
                        "agent_id": agent_id,
                        "api_key": "ak_invalidkey1234567890",
                        "task_id": task_id,
                        "target_url": "http://localhost:8000/api/v1/health",
                        "method": "GET",
                    },
                ]
            },
        )
        assert batch_res.status_code == 200
        batch_data = batch_res.json()
        assert batch_data["total"] == 2
        assert batch_data["allowed"] == 1
        assert batch_data["blocked"] == 1
