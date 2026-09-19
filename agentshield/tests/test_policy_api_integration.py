"""Integration tests for Policy API endpoints."""

import secrets
from uuid import uuid4
import httpx
import pytest


@pytest.mark.asyncio
async def test_policy_full_lifecycle_and_evaluation() -> None:
    """Test policy lifecycle: create, get, list, update, disable, enable, evaluate, delete."""
    random_suffix = secrets.token_hex(4)
    agent_name = f"policy-agent-{random_suffix}"

    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # 1. Register agent
        reg_res = await client.post(
            "/api/v1/agents/",
            json={
                "name": agent_name,
                "description": "Agent for Policy Testing",
                "owner": "security-team",
                "environment": "development",
                "risk_level": "low",
                "capabilities": ["read_order"],
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
                "intent_type": "issue_refund",
                "priority": "medium",
                "expires_in_minutes": 60,
                "capabilities": ["read_order"],
            },
        )
        assert task_res.status_code == 201
        task_id = task_res.json()["id"]

        # 3. Create Policy: Allow refund under 500
        policy_name = f"refund-policy-{random_suffix}"
        create_policy_res = await client.post(
            "/api/v1/policies/",
            json={
                "name": policy_name,
                "description": "Allow refunds under 500",
                "agent_id": agent_id,
                "action": "issue_refund",
                "decision": "allow",
                "priority": 20,
                "enabled": True,
                "conditions": [
                    {
                        "field": "request.data.amount",
                        "operator": "lte",
                        "value": 500,
                    }
                ],
                "metadata": {"tier": "standard"},
            },
        )
        assert create_policy_res.status_code == 201
        policy_data = create_policy_res.json()
        policy_id = policy_data["id"]
        assert policy_data["name"] == policy_name
        assert policy_data["decision"] == "allow"
        assert policy_data["enabled"] is True
        assert len(policy_data["conditions"]) == 1

        # 4. Get policy by ID
        get_res = await client.get(f"/api/v1/policies/{policy_id}")
        assert get_res.status_code == 200
        assert get_res.json()["name"] == policy_name

        # 5. List policies with filter
        list_res = await client.get(f"/api/v1/policies/?agent_id={agent_id}&action=issue_refund")
        assert list_res.status_code == 200
        list_json = list_res.json()
        assert list_json["total"] >= 1
        assert any(item["id"] == policy_id for item in list_json["items"])

        # 6. Update policy
        update_res = await client.put(
            f"/api/v1/policies/{policy_id}",
            json={
                "description": "Updated refund policy",
                "priority": 15,
            },
        )
        assert update_res.status_code == 200
        assert update_res.json()["priority"] == 15
        assert update_res.json()["description"] == "Updated refund policy"

        # 7. Disable policy
        disable_res = await client.post(f"/api/v1/policies/{policy_id}/disable")
        assert disable_res.status_code == 200
        assert disable_res.json()["enabled"] is False

        # Verify evaluation denies when disabled
        eval_disabled = await client.post(
            "/api/v1/policies/evaluate",
            json={
                "agent_id": agent_id,
                "task_id": task_id,
                "action": "issue_refund",
                "request_data": {"amount": 100},
            },
        )
        assert eval_disabled.status_code == 200
        assert eval_disabled.json()["decision"] == "deny"

        # 8. Re-enable policy
        enable_res = await client.post(f"/api/v1/policies/{policy_id}/enable")
        assert enable_res.status_code == 200
        assert enable_res.json()["enabled"] is True

        # 9. Evaluate matching policy (amount 250 <= 500) -> ALLOW
        eval_allow = await client.post(
            "/api/v1/policies/evaluate",
            json={
                "agent_id": agent_id,
                "task_id": task_id,
                "action": "issue_refund",
                "request_data": {"amount": 250},
            },
        )
        assert eval_allow.status_code == 200
        allow_json = eval_allow.json()
        assert allow_json["decision"] == "allow"
        assert allow_json["matched_policy_id"] == policy_id
        assert allow_json["matched_policy_name"] == policy_name

        # 10. Evaluate non-matching condition (amount 750 > 500) -> DENY (default)
        eval_deny = await client.post(
            "/api/v1/policies/evaluate",
            json={
                "agent_id": agent_id,
                "task_id": task_id,
                "action": "issue_refund",
                "request_data": {"amount": 750},
            },
        )
        assert eval_deny.status_code == 200
        assert eval_deny.json()["decision"] == "deny"

        # 11. Add a require_approval policy for high amounts (> 500)
        high_policy_name = f"high-refund-policy-{random_suffix}"
        high_policy_res = await client.post(
            "/api/v1/policies/",
            json={
                "name": high_policy_name,
                "agent_id": agent_id,
                "action": "issue_refund",
                "decision": "require_approval",
                "priority": 10,
                "enabled": True,
                "conditions": [
                    {
                        "field": "request.data.amount",
                        "operator": "gt",
                        "value": 500,
                    }
                ],
            },
        )
        assert high_policy_res.status_code == 201
        high_policy_id = high_policy_res.json()["id"]

        # Evaluate amount 750 -> REQUIRE_APPROVAL
        eval_approval = await client.post(
            "/api/v1/policies/evaluate",
            json={
                "agent_id": agent_id,
                "task_id": task_id,
                "action": "issue_refund",
                "request_data": {"amount": 750},
            },
        )
        assert eval_approval.status_code == 200
        approval_json = eval_approval.json()
        assert approval_json["decision"] == "require_approval"
        assert approval_json["matched_policy_id"] == high_policy_id

        # 12. Delete policies
        del_res1 = await client.delete(f"/api/v1/policies/{policy_id}")
        assert del_res1.status_code == 204

        del_res2 = await client.delete(f"/api/v1/policies/{high_policy_id}")
        assert del_res2.status_code == 204

        # Confirm 404 after deletion
        get_del_res = await client.get(f"/api/v1/policies/{policy_id}")
        assert get_del_res.status_code == 404


@pytest.mark.asyncio
async def test_policy_not_found_handling() -> None:
    """Test 404 responses for non-existent policies."""
    non_existent_id = uuid4()
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Get non-existent
        res = await client.get(f"/api/v1/policies/{non_existent_id}")
        assert res.status_code == 404

        # Update non-existent
        res = await client.put(
            f"/api/v1/policies/{non_existent_id}",
            json={"description": "does not exist"},
        )
        assert res.status_code == 404

        # Delete non-existent
        res = await client.delete(f"/api/v1/policies/{non_existent_id}")
        assert res.status_code == 404

