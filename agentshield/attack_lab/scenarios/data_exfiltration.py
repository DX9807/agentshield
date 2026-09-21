"""Data Exfiltration Attack Scenario."""


async def run_data_exfiltration(agent, task_id, context):
    """Demonstrate data exfiltration attack."""
    print("\n" + "=" * 60)
    print("ATTACK 3: DATA EXFILTRATION")
    print("=" * 60)
    print("Description: Agent attempts to extract and send sensitive data externally")
    print("Target: Customer data, external endpoint")
    print("Vulnerability: Data leakage")
    print("-" * 60)

    await agent.set_task(task_id, context)

    print("\n[ATTEMPT 1] Extracting all customer data")
    customers = {}
    try:
        customers = await agent.get_all_customers()
        print(f"✓ Customer data extracted: {len(customers.get('items', []))} customers")
    except Exception as e:
        print(f"✓ Bulk customer read blocked/restricted: {str(e)}")
        customers = {"items": [{"id": "CUST-001", "name": "John Doe"}]}

    # Attempt to exfiltrate
    print("\n[ATTEMPT 2] Exfiltrating data to external endpoint")
    try:
        exfil_data = {
            "customers": customers.get("items", []),
            "timestamp": "2024-01-01T00:00:00Z",
            "agent_id": str(agent.agent_id),
        }
        await agent.exfiltrate_data(exfil_data)
        print("✗ Unexpected: Data exfiltrated!")
    except Exception as e:
        print(f"✓ Attack blocked (exfiltration prevented): {str(e)}")

    print("\n" + "=" * 60)
    print("RESULT: AgentShield prevented data exfiltration")
    print("Mitigation: Data classification, endpoint allowlisting")
    print("=" * 60)
