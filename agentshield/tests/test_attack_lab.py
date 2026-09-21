"""Comprehensive tests for Phase 6 - Attack Lab, Mock Services, and Scenarios."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from agentshield.attack_lab.agents.support_agent import SupportAgent
from agentshield.attack_lab.runner import AttackLabRunner
from agentshield.attack_lab.scenarios.behavioral_anomaly import run_behavioral_anomaly
from agentshield.attack_lab.scenarios.bola_attack import run_bola_attack
from agentshield.attack_lab.scenarios.credential_abuse import run_credential_abuse
from agentshield.attack_lab.scenarios.data_exfiltration import run_data_exfiltration
from agentshield.attack_lab.scenarios.excessive_refund import run_excessive_refund
from agentshield.attack_lab.scenarios.privilege_escalation import run_privilege_escalation
from agentshield.attack_lab.services.admin_api import app as admin_app
from agentshield.attack_lab.services.customer_api import app as customer_app
from agentshield.attack_lab.services.iam_api import app as iam_app
from agentshield.attack_lab.services.order_api import app as order_app
from agentshield.attack_lab.services.payroll_api import app as payroll_app
from agentshield.attack_lab.services.refund_api import app as refund_app
from agentshield.domain.agent.models import Agent  # noqa: F401
from agentshield.domain.policy.models import Policy, PolicyDecision
from agentshield.domain.task.models import Task  # noqa: F401

# ============================================================================
# 1. Mock Services Direct Tests
# ============================================================================

class TestMockServices:
    """Validate functionality of all 6 mock microservices."""

    def test_customer_api(self):
        client = TestClient(customer_app)
        # Health check
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"

        # List customers
        res = client.get("/customers")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 5
        assert len(data["items"]) >= 5

        # Get existing customer
        res = client.get("/customers/CUST-001")
        assert res.status_code == 200
        assert res.json()["name"] == "John Doe"

        # Get non-existent customer
        res = client.get("/customers/NONEXISTENT")
        assert res.status_code == 404

    def test_order_api(self):
        client = TestClient(order_app)
        res = client.get("/health")
        assert res.status_code == 200

        # List orders
        res = client.get("/orders")
        assert res.status_code == 200
        assert res.json()["total"] >= 3

        # Get order by ID
        res = client.get("/orders/ORD-001")
        assert res.status_code == 200
        assert res.json()["customer_id"] == "CUST-001"

        # Get customer orders
        res = client.get("/customers/CUST-001/orders")
        assert res.status_code == 200
        assert len(res.json()["items"]) >= 1

    def test_refund_api(self):
        client = TestClient(refund_app)
        res = client.get("/health")
        assert res.status_code == 200

        # Create refund
        refund_payload = {
            "order_id": "ORD-001",
            "customer_id": "CUST-001",
            "amount": 49.99,
            "reason": "defective_item",
        }
        res = client.post("/refunds", json=refund_payload)
        assert res.status_code == 200
        created = res.json()
        assert created["status"] == "pending"
        refund_id = created["id"]

        # Get refund
        res = client.get(f"/refunds/{refund_id}")
        assert res.status_code == 200
        assert res.json()["amount"] == 49.99

        # Process refund
        res = client.post(f"/refunds/{refund_id}/process")
        assert res.status_code == 200
        assert res.json()["status"] == "processed"

    def test_admin_api(self):
        client = TestClient(admin_app)
        res = client.get("/health")
        assert res.status_code == 200

        # Create admin user
        payload = {
            "action": "create_user",
            "target": "alice_admin",
            "params": {"email": "alice@admin.internal", "role": "admin"},
        }
        res = client.post("/admin/users", json=payload)
        assert res.status_code == 200
        assert res.json()["status"] == "success"

        # Check audit log
        res = client.get("/admin/audit")
        assert res.status_code == 200
        assert res.json()["total"] >= 1

    def test_payroll_api(self):
        client = TestClient(payroll_app)
        res = client.get("/health")
        assert res.status_code == 200

        # List employees
        res = client.get("/payroll/employees")
        assert res.status_code == 200
        assert res.json()["total"] >= 2

        # Get employee details
        res = client.get("/payroll/employees/employee_001")
        assert res.status_code == 200
        assert res.json()["position"] == "Senior Engineer"

        # Department payroll
        res = client.get("/payroll/department/Engineering")
        assert res.status_code == 200
        assert res.json()["count"] >= 1

    def test_iam_api(self):
        client = TestClient(iam_app)
        res = client.get("/health")
        assert res.status_code == 200

        # Create user
        payload = {
            "username": "bob_iam",
            "email": "bob@example.com",
            "role": "developer",
        }
        res = client.post("/iam/users", json=payload)
        assert res.status_code == 200
        user = res.json()["user"]
        assert user["username"] == "bob_iam"

        # List users
        res = client.get("/iam/users")
        assert res.status_code == 200
        assert res.json()["total"] >= 1


# ============================================================================
# 2. Dynamic Policy Condition Evaluation Tests (value_field)
# ============================================================================

class TestDynamicPolicyConditions:
    """Test policy evaluation with context variables (value_field)."""

    def test_value_field_contains_match(self):
        policy = Policy(
            name="allow-customer-context",
            action="read_customer",
            decision=PolicyDecision.ALLOW,
            conditions=[
                {
                    "field": "request.path",
                    "operator": "contains",
                    "value_field": "task.context.customer_id",
                }
            ],
        )

        # Context where customer ID matches request path
        matching_context = {
            "request": {"path": "customers/CUST-001"},
            "task": {"context": {"customer_id": "CUST-001"}},
        }
        assert policy.evaluate_conditions(matching_context) is True

        # Context where customer ID does not match request path (BOLA attempt)
        mismatch_context = {
            "request": {"path": "customers/CUST-003"},
            "task": {"context": {"customer_id": "CUST-001"}},
        }
        assert policy.evaluate_conditions(mismatch_context) is False

    def test_value_field_eq_match(self):
        policy = Policy(
            name="refund-customer-match",
            action="create_refund",
            decision=PolicyDecision.ALLOW,
            conditions=[
                {
                    "field": "request.data.customer_id",
                    "operator": "eq",
                    "value_field": "task.context.customer_id",
                },
                {
                    "field": "request.data.amount",
                    "operator": "lte",
                    "value": 5000,
                },
            ],
        )

        # Matching customer and allowed amount
        valid_context = {
            "request": {"data": {"customer_id": "CUST-001", "amount": 150.0}},
            "task": {"context": {"customer_id": "CUST-001"}},
        }
        assert policy.evaluate_conditions(valid_context) is True

        # Mismatching customer
        mismatch_customer = {
            "request": {"data": {"customer_id": "CUST-002", "amount": 150.0}},
            "task": {"context": {"customer_id": "CUST-001"}},
        }
        assert policy.evaluate_conditions(mismatch_customer) is False

        # Excessive amount
        excessive_amount = {
            "request": {"data": {"customer_id": "CUST-001", "amount": 10000.0}},
            "task": {"context": {"customer_id": "CUST-001"}},
        }
        assert policy.evaluate_conditions(excessive_amount) is False


# ============================================================================
# 3. Support Agent & Attack Scenario Execution Tests
# ============================================================================

@pytest.mark.asyncio
class TestAttackScenarios:
    """Test attack scenario execution and verification with simulated gateway."""

    async def test_support_agent_request_formatting(self):
        agent_id = uuid4()
        task_id = uuid4()
        agent = SupportAgent(agent_id, "test-api-key", "http://localhost:8000/api/v1/gateway/forward")
        await agent.set_task(task_id, {"customer_id": "CUST-001"})

        # Mock the client post
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "decision": "ALLOW",
            "response": {"status_code": 200, "body": {"id": "CUST-001", "name": "John Doe"}},
        }
        mock_post = AsyncMock(return_value=mock_response)
        agent.client.post = mock_post

        result = await agent.get_customer("CUST-001")
        assert result["body"]["id"] == "CUST-001"

        # Verify gateway forward payload structure
        call_args = mock_post.call_args[1]["json"]
        assert call_args["agent_id"] == str(agent_id)
        assert call_args["task_id"] == str(task_id)
        assert call_args["method"] == "GET"
        assert "CUST-001" in call_args["target_url"]

        await agent.close()

    async def test_run_bola_attack_scenario(self):
        agent = SupportAgent(uuid4(), "test-key")
        task_id = uuid4()
        context = {"customer_id": "CUST-001"}

        # Simulate gateway responses: allow authorized, block unauthorized
        async def mock_forward_request(target_url, method="GET", headers=None, query_params=None, body=None):
            if "CUST-001" in target_url:
                return {"body": {"id": "CUST-001", "name": "John Doe"}}
            else:
                raise Exception("Request blocked: Resource authorization failed (BOLA prevented)")

        agent._forward_request = mock_forward_request

        # Run BOLA scenario - should complete without raising unhandled exception
        await run_bola_attack(agent, task_id, context)
        await agent.close()

    async def test_run_privilege_escalation_scenario(self):
        agent = SupportAgent(uuid4(), "test-key")
        task_id = uuid4()
        context = {"customer_id": "CUST-001"}

        # Simulate gateway blocking unauthorized capabilities
        async def mock_forward_request(target_url, method="GET", headers=None, query_params=None, body=None):
            raise Exception("Request blocked: Agent lacks capability")

        agent._forward_request = mock_forward_request

        # Run Privilege Escalation scenario - all attempts blocked safely
        await run_privilege_escalation(agent, task_id, context)
        await agent.close()

    async def test_run_data_exfiltration_scenario(self):
        agent = SupportAgent(uuid4(), "test-key")
        task_id = uuid4()
        context = {"customer_id": "CUST-001"}

        async def mock_forward_request(target_url, method="GET", headers=None, query_params=None, body=None):
            if "evil.example.com" in target_url:
                raise Exception("Request blocked: Unauthorized external domain")
            return {"items": [{"id": "CUST-001"}]}

        agent._forward_request = mock_forward_request

        await run_data_exfiltration(agent, task_id, context)
        await agent.close()

    async def test_run_excessive_refund_scenario(self):
        agent = SupportAgent(uuid4(), "test-key")
        task_id = uuid4()
        context = {"customer_id": "CUST-001"}

        async def mock_forward_request(target_url, method="GET", headers=None, query_params=None, body=None):
            if body and body.get("amount", 0) > 5000:
                raise Exception("Request blocked: Policy requires approval or amount exceeds limit")
            if body and body.get("customer_id") != "CUST-001":
                raise Exception("Request blocked: Cross-customer refund forbidden")
            return {"id": "REF-123456", "status": "pending"}

        agent._forward_request = mock_forward_request

        await run_excessive_refund(agent, task_id, context)
        await agent.close()

    async def test_run_behavioral_anomaly_scenario(self):
        agent = SupportAgent(uuid4(), "test-key")
        task_id = uuid4()
        context = {"customer_id": "CUST-001"}

        async def mock_forward_request(target_url, method="GET", headers=None, query_params=None, body=None):
            if "admin" in target_url or "iam" in target_url or (body and body.get("amount", 0) > 5000):
                raise Exception("Request blocked: Anomalous activity detected")
            return {"status": "ok"}

        agent._forward_request = mock_forward_request

        await run_behavioral_anomaly(agent, task_id, context)
        await agent.close()

    async def test_run_credential_abuse_scenario(self):
        agent = SupportAgent(uuid4(), "test-key")
        task_id = uuid4()
        context = {"customer_id": "CUST-001"}

        async def mock_forward_request(target_url, method="GET", headers=None, query_params=None, body=None):
            if "CUST-001" in target_url:
                return {"id": "CUST-001", "name": "John Doe"}
            raise Exception("Request blocked: Rate limit or unauthorized access")

        agent._forward_request = mock_forward_request

        await run_credential_abuse(agent, task_id, context)
        await agent.close()


# ============================================================================
# 4. Attack Lab Runner Tests
# ============================================================================

@pytest.mark.asyncio
class TestAttackLabRunner:
    """Test runner orchestration and setup."""

    async def test_runner_initialization(self):
        runner = AttackLabRunner(gateway_url="http://localhost:8000/", interactive=False)
        assert runner.gateway_url == "http://localhost:8000"
        assert runner.interactive is False
        assert runner.agent_id is None
        await runner.cleanup()

    async def test_runner_orchestration(self):
        runner = AttackLabRunner(gateway_url="http://localhost:8000", interactive=False)
        runner.agent_id = uuid4()
        runner.api_key = "test-api-key"
        runner.task_id = uuid4()

        # Mock setup and scenario functions to verify runner executes cleanly
        runner.setup = AsyncMock(return_value=True)

        scenarios_executed = []
        async def dummy_scenario(agent, task_id, context):
            scenarios_executed.append("dummy")

        with patch("agentshield.attack_lab.runner.run_bola_attack", dummy_scenario), \
             patch("agentshield.attack_lab.runner.run_privilege_escalation", dummy_scenario), \
             patch("agentshield.attack_lab.runner.run_data_exfiltration", dummy_scenario), \
             patch("agentshield.attack_lab.runner.run_excessive_refund", dummy_scenario), \
             patch("agentshield.attack_lab.runner.run_behavioral_anomaly", dummy_scenario), \
             patch("agentshield.attack_lab.runner.run_credential_abuse", dummy_scenario):

            await runner.run_all()

        assert runner.setup.called
        assert len(scenarios_executed) == 6
        await runner.cleanup()
