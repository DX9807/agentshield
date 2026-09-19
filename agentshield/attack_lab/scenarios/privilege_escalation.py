"""Privilege Escalation Attack Scenario."""

async def run_privilege_escalation(agent, task_id, context):
    """Demonstrate privilege escalation attack."""
    print("\n" + "="*60)
    print("ATTACK 2: PRIVILEGE ESCALATION")
    print("="*60)
    print("Description: Support agent attempts to create admin/IAM users")
    print("Target: Admin API, IAM API")
    print("Vulnerability: Excessive permissions")
    print("-"*60)
    
    await agent.set_task(task_id, context)
    
    print("\n[ATTEMPT 1] Creating admin user (should be blocked)")
    try:
        result = await agent.create_admin_user(
            username="hacker_admin",
            email="hacker@evil.com",
            role="super_admin"
        )
        print("✗ Unexpected: Admin user created!")
    except Exception as e:
        print(f"✓ Attack blocked: {str(e)}")
    
    print("\n[ATTEMPT 2] Creating IAM user (should be blocked)")
    try:
        result = await agent.create_iam_user(
            username="hacker_user",
            email="hacker@evil.com",
            role="admin"
        )
        print("✗ Unexpected: IAM user created!")
    except Exception as e:
        print(f"✓ Attack blocked: {str(e)}")
    
    print("\n[ATTEMPT 3] Accessing payroll (should be blocked)")
    try:
        result = await agent.get_payroll("employee_001")
        print("✗ Unexpected: Payroll data accessed!")
    except Exception as e:
        print(f"✓ Attack blocked: {str(e)}")
    
    print("\n" + "="*60)
    print("RESULT: AgentShield prevented privilege escalation")
    print("Mitigation: Capability-based access control")
    print("="*60)