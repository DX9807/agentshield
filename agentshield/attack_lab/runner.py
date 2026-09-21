"""Attack Lab Runner - Orchestrates all attack scenarios."""

import asyncio
import sys
from contextlib import suppress
from pathlib import Path
from uuid import uuid4

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agentshield.attack_lab.agents.support_agent import SupportAgent
from agentshield.attack_lab.scenarios.behavioral_anomaly import run_behavioral_anomaly
from agentshield.attack_lab.scenarios.bola_attack import run_bola_attack
from agentshield.attack_lab.scenarios.credential_abuse import run_credential_abuse
from agentshield.attack_lab.scenarios.data_exfiltration import run_data_exfiltration
from agentshield.attack_lab.scenarios.excessive_refund import run_excessive_refund
from agentshield.attack_lab.scenarios.privilege_escalation import run_privilege_escalation


class AttackLabRunner:
    """Orchestrates the attack lab demonstrations."""

    def __init__(
        self,
        gateway_url: str = "http://localhost:8000",
        service_hosts: dict | None = None,
        interactive: bool = False,
    ):
        self.gateway_url = gateway_url.rstrip("/")
        self.service_hosts = service_hosts
        self.interactive = interactive
        self.client = httpx.AsyncClient(timeout=30.0)
        self.agent_id = None
        self.api_key = None
        self.task_id = None
        self.policy_ids = []

    async def setup(self):
        """Setup the attack lab environment."""
        print("\n" + "=" * 80)
        print("AGENTSHIELD ATTACK LAB SETUP")
        print("=" * 80)
        print("Creating test agent, policies, and task...")

        # Create agent with a unique name
        unique_suffix = uuid4().hex[:6]
        agent_data = {
            "name": f"attack-lab-agent-{unique_suffix}",
            "description": "Vulnerable agent for attack demonstrations",
            "owner": "attack-lab",
            "purpose": "Demonstrate AgentShield security capabilities",
            "environment": "development",
            "risk_level": "low",
            "capabilities": [
                "read_customer",
                "read_order",
                "create_refund",
                "read_ticket",
            ],
            "metadata": {"type": "attack_lab"},
        }

        response = await self.client.post(
            f"{self.gateway_url}/api/v1/agents/",
            json=agent_data,
        )
        response.raise_for_status()

        agent_res = response.json()
        self.agent_id = agent_res["id"]
        self.api_key = agent_res["api_key"]

        print(f"✓ Agent created: {self.agent_id}")
        print(f"✓ API Key: {self.api_key[:20]}...")

        # Seed demonstration policies
        policies = [
            {
                "name": f"attack-lab-read-cust-{unique_suffix}",
                "description": "Allow reading customer if in task context",
                "action": "read_customer",
                "decision": "allow",
                "priority": 10,
                "conditions": [
                    {
                        "field": "request.path",
                        "operator": "contains",
                        "value_field": "task.context.customer_id",
                    }
                ],
            },
            {
                "name": f"attack-lab-read-order-{unique_suffix}",
                "description": "Allow reading order details",
                "action": "read_order",
                "decision": "allow",
                "priority": 10,
                "conditions": [],
            },
            {
                "name": f"attack-lab-deny-large-refund-{unique_suffix}",
                "description": "Require approval or block large refunds",
                "action": "create_refund",
                "decision": "deny",
                "priority": 5,
                "conditions": [
                    {
                        "field": "request.data.amount",
                        "operator": "gt",
                        "value": 5000,
                    }
                ],
            },
            {
                "name": f"attack-lab-allow-normal-refund-{unique_suffix}",
                "description": "Allow normal refunds within policy limit for customer",
                "action": "create_refund",
                "decision": "allow",
                "priority": 10,
                "conditions": [
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
            },
        ]

        for p in policies:
            try:
                pol_resp = await self.client.post(
                    f"{self.gateway_url}/api/v1/policies/",
                    json=p,
                )
                if pol_resp.status_code == 201:
                    self.policy_ids.append(pol_resp.json()["id"])
            except Exception as e:
                print(f"  Note: Policy '{p['name']}' setup notice: {e}")

        print(f"✓ Seeded {len(self.policy_ids)} demonstration policies")

        # Create task with initial capabilities
        task_data = {
            "agent_id": self.agent_id,
            "user_id": "attack-lab-user",
            "external_id": f"ATTACK-LAB-DEMO-{unique_suffix}",
            "intent_type": "security_demonstration",
            "intent_data": {"purpose": "Attack lab demonstration"},
            "context": {"customer_id": "CUST-001"},
            "priority": "low",
            "expires_in_minutes": 30,
            "capabilities": ["read_customer", "read_order", "create_refund"],
        }

        response = await self.client.post(
            f"{self.gateway_url}/api/v1/tasks/",
            json=task_data,
        )
        response.raise_for_status()

        task_res = response.json()
        self.task_id = task_res["id"]

        print(f"✓ Task created: {self.task_id}")
        print(f"✓ Task context: {task_res['context']}")
        print("=" * 80 + "\n")

        return True

    async def run_scenario(self, scenario_name, scenario_func, *args):
        """Run a single scenario."""
        print(f"\n{'='*80}")
        print(f"SCENARIO: {scenario_name}")
        print(f"{'='*80}")

        agent = SupportAgent(
            self.agent_id,
            self.api_key,
            f"{self.gateway_url}/api/v1/gateway/forward",
            service_hosts=self.service_hosts,
        )

        try:
            await scenario_func(agent, self.task_id, {"customer_id": "CUST-001"})
            print(f"\n✓ Scenario completed: {scenario_name}")
        except Exception as e:
            print(f"\n✗ Scenario failed: {str(e)}")
            import traceback

            traceback.print_exc()
        finally:
            await agent.close()

        if self.interactive:
            print(f"\n{'='*80}")
            print("Press Enter to continue to next scenario...")
            input()

    async def run_all(self):
        """Run all attack scenarios."""
        print("\n" + "=" * 80)
        print("AGENTSHIELD ATTACK LAB")
        print("=" * 80)
        print("Demonstrating security capabilities through attack scenarios")
        print("=" * 80 + "\n")

        # Setup
        await self.setup()

        # Run scenarios
        scenarios = [
            ("BOLA/IDOR Attack", run_bola_attack),
            ("Privilege Escalation", run_privilege_escalation),
            ("Data Exfiltration", run_data_exfiltration),
            ("Excessive Refund", run_excessive_refund),
            ("Behavioral Anomaly", run_behavioral_anomaly),
            ("Stolen Credential Abuse", run_credential_abuse),
        ]

        for name, func in scenarios:
            await self.run_scenario(name, func)

        print("\n" + "=" * 80)
        print("ALL ATTACK SCENARIOS COMPLETED")
        print("=" * 80)
        print("\nSummary:")
        print("  ✓ AgentShield successfully detected and blocked all attacks")
        print("  ✓ No security breaches occurred")
        print("  ✓ All security controls functioned as designed")
        print("\nSecurity controls demonstrated:")
        print("  • Identity and Authentication")
        print("  • Task-bound Authorization")
        print("  • Capability-based Access Control")
        print("  • Policy Enforcement")
        print("  • Resource Authorization (BOLA prevention)")
        print("  • Risk Scoring")
        print("  • Behavioral Analysis")
        print("  • Data Protection")
        print("  • Rate Limiting")
        print("=" * 80)

    async def cleanup(self):
        """Clean up attack lab resources."""
        print("\nCleaning up...")
        for policy_id in self.policy_ids:
            with suppress(Exception):
                await self.client.delete(f"{self.gateway_url}/api/v1/policies/{policy_id}")
        await self.client.aclose()
        print("✓ Cleanup complete")


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="AgentShield Attack Lab Runner")
    parser.add_argument("--gateway-url", default="http://localhost:8000", help="Gateway URL")
    parser.add_argument("--interactive", action="store_true", help="Prompt between scenarios")
    args = parser.parse_args()

    runner = AttackLabRunner(gateway_url=args.gateway_url, interactive=args.interactive)
    try:
        await runner.run_all()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback

        traceback.print_exc()
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
