"""Integration tests for Task API endpoints."""

import secrets
from uuid import uuid4

import httpx
import pytest


@pytest.mark.asyncio
async def test_task_full_lifecycle() -> None:
    """Test full task lifecycle: creation, fetch, update, extend, complete, revoke."""
    random_suffix = secrets.token_hex(4)
    agent_name = f"task-agent-{random_suffix}"

    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        # 1. Register agent
        reg_res = await client.post(
            "/api/v1/agents/",
            json={
                "name": agent_name,
                "description": "Agent for Task Integration Testing",
                "owner": "test-team",
                "environment": "development",
                "risk_level": "low",
                "capabilities": ["read_order", "write_order"],
            },
        )
        assert reg_res.status_code == 201
        agent_id = reg_res.json()["id"]

        # 2. Create task
        task_res = await client.post(
            "/api/v1/tasks/",
            json={
                "agent_id": agent_id,
                "user_id": "operator-01",
                "external_id": f"TICKET-{random_suffix}",
                "intent_type": "read_order",
                "intent_data": {"order_num": 1001},
                "context": {"priority": "normal"},
                "priority": "medium",
                "expires_in_minutes": 60,
                "capabilities": ["read_order"],
            },
        )
        assert task_res.status_code == 201
        task_data = task_res.json()
        task_id = task_data["id"]
        assert task_data["status"] == "active"
        assert "read_order" in task_data["capabilities"]

        # 3. Get task by ID
        get_res = await client.get(f"/api/v1/tasks/{task_id}")
        assert get_res.status_code == 200
        assert get_res.json()["intent_type"] == "read_order"

        # 4. List tasks filter by agent_id
        list_res = await client.get(f"/api/v1/tasks/?agent_id={agent_id}")
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert list_data["total"] >= 1
        assert any(t["id"] == task_id for t in list_data["items"])

        # 5. Get task capabilities
        caps_res = await client.get(f"/api/v1/tasks/{task_id}/capabilities")
        assert caps_res.status_code == 200
        caps_data = caps_res.json()
        assert "capabilities" in caps_data
        assert any(c["name"] == "read_order" for c in caps_data["capabilities"])

        # 6. Update task
        update_res = await client.put(
            f"/api/v1/tasks/{task_id}",
            json={"priority": "high", "context": {"priority": "urgent"}},
        )
        assert update_res.status_code == 200
        assert update_res.json()["priority"] == "high"

        # 7. Extend task
        extend_res = await client.post(
            f"/api/v1/tasks/{task_id}/extend",
            json={"additional_minutes": 30, "reason": "Processing delay"},
        )
        assert extend_res.status_code == 200
        assert extend_res.json()["status"] == "active"

        # 8. Complete task
        comp_res = await client.post(
            f"/api/v1/tasks/{task_id}/complete",
            json={"result_data": {"order_status": "fulfilled"}},
        )
        assert comp_res.status_code == 200
        assert comp_res.json()["status"] == "completed"
        assert comp_res.json()["is_active"] is False


@pytest.mark.asyncio
async def test_task_revoke_flow() -> None:
    """Test task revocation endpoint."""
    random_suffix = secrets.token_hex(4)
    agent_name = f"revoke-agent-{random_suffix}"

    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        # Register agent
        reg_res = await client.post(
            "/api/v1/agents/",
            json={
                "name": agent_name,
                "owner": "security",
                "capabilities": ["read_customer"],
            },
        )
        agent_id = reg_res.json()["id"]

        # Create task
        task_res = await client.post(
            "/api/v1/tasks/",
            json={
                "agent_id": agent_id,
                "user_id": "operator-02",
                "intent_type": "read_customer",
                "expires_in_minutes": 30,
            },
        )
        task_id = task_res.json()["id"]

        # Revoke task
        revoke_res = await client.post(
            f"/api/v1/tasks/{task_id}/revoke",
            json={"reason": "Manual cancellation"},
        )
        assert revoke_res.status_code == 200
        assert revoke_res.json()["status"] == "revoked"
        assert revoke_res.json()["is_active"] is False


@pytest.mark.asyncio
async def test_task_not_found_handling() -> None:
    """Test 404 response for nonexistent tasks and agents."""
    fake_id = uuid4()
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        # Get nonexistent task
        get_res = await client.get(f"/api/v1/tasks/{fake_id}")
        assert get_res.status_code == 404

        # Create task with nonexistent agent
        post_res = await client.post(
            "/api/v1/tasks/",
            json={
                "agent_id": str(fake_id),
                "user_id": "user",
                "intent_type": "test",
            },
        )
        assert post_res.status_code == 404
