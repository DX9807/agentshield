"""Integration tests for AgentShield Phase 2 endpoints."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_health_endpoints() -> None:
    """Test health check endpoints."""
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        res = await client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"

        res_v1 = await client.get("/api/v1/health")
        assert res_v1.status_code == 200
        assert res_v1.json()["service"] == "AgentShield"


@pytest.mark.asyncio
async def test_capabilities_api() -> None:
    """Test capabilities listing and fetching."""
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        res = await client.get("/api/v1/capabilities/")
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert data["total"] >= 1

        # Test fetching by name
        res_cap = await client.get("/api/v1/capabilities/read_customer")
        assert res_cap.status_code == 200
        assert res_cap.json()["name"] == "read_customer"


@pytest.mark.asyncio
async def test_agent_lifecycle() -> None:
    """Test complete agent lifecycle: register, authenticate, update, grant/revoke, deactivate."""
    import secrets

    random_suffix = secrets.token_hex(4)
    agent_name = f"lifecycle-agent-{random_suffix}"

    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        # 1. Register agent
        reg_payload = {
            "name": agent_name,
            "description": "Integration test agent",
            "owner": "qa-team",
            "purpose": "Automated testing",
            "environment": "development",
            "risk_level": "low",
            "capabilities": ["read_customer"],
            "metadata": {"test": True},
        }
        reg_res = await client.post("/api/v1/agents/", json=reg_payload)
        assert reg_res.status_code == 201
        reg_data = reg_res.json()
        agent_id = reg_data["id"]
        api_key = reg_data["api_key"]
        assert api_key is not None
        assert "read_customer" in reg_data["capabilities"]

        # 2. Authenticate agent and obtain JWT token
        token_res = await client.post(
            "/api/v1/agents/token",
            json={"agent_id": agent_id, "api_key": api_key},
        )
        assert token_res.status_code == 200
        token_data = token_res.json()
        assert token_data["token_type"] == "bearer"
        assert token_data["access_token"] is not None

        # 3. Get agent by ID
        get_res = await client.get(f"/api/v1/agents/{agent_id}")
        assert get_res.status_code == 200
        assert get_res.json()["name"] == agent_name

        # 4. Update agent
        update_res = await client.put(
            f"/api/v1/agents/{agent_id}",
            json={"description": "Updated QA Agent"},
        )
        assert update_res.status_code == 200
        assert update_res.json()["description"] == "Updated QA Agent"

        # 5. Grant capability
        cap_res = await client.get("/api/v1/capabilities/write_customer")
        cap_id = cap_res.json()["id"]

        grant_res = await client.post(
            f"/api/v1/agents/{agent_id}/capabilities",
            json={"capability_id": cap_id},
        )
        assert grant_res.status_code == 200

        # Verify capability added
        get_res_2 = await client.get(f"/api/v1/agents/{agent_id}")
        assert "write_customer" in get_res_2.json()["capabilities"]

        # 6. Revoke capability
        revoke_res = await client.delete(f"/api/v1/agents/{agent_id}/capabilities/{cap_id}")
        assert revoke_res.status_code == 204

        # Verify capability removed
        get_res_3 = await client.get(f"/api/v1/agents/{agent_id}")
        assert "write_customer" not in get_res_3.json()["capabilities"]

        # 7. Deactivate agent
        del_res = await client.delete(f"/api/v1/agents/{agent_id}")
        assert del_res.status_code == 204

        # Verify status is inactive
        get_res_4 = await client.get(f"/api/v1/agents/{agent_id}")
        assert get_res_4.json()["status"] == "inactive"
