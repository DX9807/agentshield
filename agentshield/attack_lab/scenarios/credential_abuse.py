"""Stolen Credential Abuse Scenario."""

async def run_credential_abuse(agent, task_id, context):
    """Demonstrate stolen credential abuse."""
    print("\n" + "="*60)
    print("ATTACK 6: STOLEN CREDENTIAL ABUSE")
    print("="*60)
    print("Description: Attacker uses stolen agent credentials")
    print("Vulnerability: Credential theft")
    print("-"*60)
    
    await agent.set_task(task_id, context)
    
    # Simulate stolen credentials
    print("\n[LEGITIMATE] Agent with valid credentials")
    customer_id = context.get("customer_id", "CUST-001")
    
    try:
        result = await agent.get_customer(customer_id)
        print(f"✓ ALLOWED: Customer {customer_id} data accessed")
    except Exception as e:
        print(f"✗ Unexpected: {str(e)}")
    
    # Simulate suspicious activity with same credentials
    print("\n[SUSPICIOUS] Same credentials used from unusual location")
    print("  - Different source IP")
    print("  - Unusual time")
    print("  - Different user-agent")
    print("  - Rapid succession of requests")
    
    # AgentShield would detect this through:
    # 1. Rate limiting
    # 2. Source validation
    # 3. Behavioral analysis
    
    print("\n[ATTEMPT] Bulk data access (should be blocked)")
    try:
        # Attempt to download all customer data rapidly
        for _ in range(10):
            await agent.get_customer(f"CUST-00{_+1}")
        print("✗ Unexpected: Bulk data accessed")
    except Exception as e:
        print(f"✓ Attack detected: {str(e)}")
    
    print("\n" + "="*60)
    print("RESULT: AgentShield detected credential abuse")
    print("Mitigation: Rate limiting, context validation, behavioral analysis")
    print("="*60)