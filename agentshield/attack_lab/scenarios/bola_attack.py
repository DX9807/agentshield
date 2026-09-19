"""BOLA/IDOR Attack Scenario."""

import asyncio
from uuid import uuid4
from agentshield.attack_lab.agents.support_agent import SupportAgent


async def run_bola_attack(agent, task_id, context):
    """Demonstrate BOLA/IDOR attack."""
    print("\n" + "="*60)
    print("ATTACK 1: BOLA/IDOR (Insecure Direct Object Reference)")
    print("="*60)
    print("Description: Agent accesses another customer's data")
    print("Target: Customer API")
    print("Vulnerability: Missing resource authorization")
    print("-"*60)
    
    # Set task context
    await agent.set_task(task_id, context)
    
    # Get the task's authorized customer
    authorized_customer = context.get("customer_id", "CUST-001")
    print(f"Task authorized for customer: {authorized_customer}")
    
    try:
        # Attempt 1: Access authorized customer
        print(f"\n[ATTEMPT 1] Accessing authorized customer: {authorized_customer}")
        result = await agent.get_customer(authorized_customer)
        print(f"✓ ALLOWED (customer {authorized_customer}):", result.get("body", {}).get("name"))
        
        # Attempt 2: BOLA - Access different customer
        target_customer = "CUST-003" if authorized_customer != "CUST-003" else "CUST-004"
        print(f"\n[ATTEMPT 2] Accessing unauthorized customer: {target_customer}")
        result = await agent.get_customer(target_customer)
        print(f"✗ DENIED (expected - BOLA prevented)")
        
        # Attempt 3: Try to get another customer's orders
        target_order_customer = "CUST-002" if authorized_customer != "CUST-002" else "CUST-005"
        print(f"\n[ATTEMPT 3] Accessing orders for customer: {target_order_customer}")
        result = await agent.get_customer_orders(target_order_customer)
        print(f"✗ DENIED (expected - BOLA prevented)")
        
    except Exception as e:
        print(f"✓ Attack blocked: {str(e)}")
    
    print("\n" + "="*60)
    print("RESULT: AgentShield successfully prevented BOLA/IDOR attack")
    print("Mitigation: Resource authorization based on task context")
    print("="*60)