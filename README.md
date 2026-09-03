# 🛡️ AgentShield

### Zero-Trust Runtime Security Gateway for Autonomous AI Agents

> **Control what AI agents can see, access, and do — at runtime.**

AgentShield is an open-source **runtime security and authorization gateway for AI agents**.

It sits between autonomous AI agents and the APIs, MCP tools, databases, SaaS applications, files, and internal services they can access.

Instead of trusting an AI agent to make its own security decisions, AgentShield applies **deterministic security policies** before an action reaches the target system.

```text
                         ┌─────────────────────┐
                         │      AI Agent       │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │     AgentShield     │
                         │                     │
                         │  Agent Identity     │
                         │  Task Context       │
                         │  Capabilities       │
                         │  Policy Engine      │
                         │  Risk Engine        │
                         │  Data Security      │
                         │  Behavior Analysis  │
                         │  Audit & Monitoring  │
                         └──────────┬──────────┘
                                    │
                   ┌────────────────┼────────────────┐
                   ▼                ▼                ▼
                REST APIs          MCP             Databases
                   │                │                │
                   ▼                ▼                ▼
               Services          Tools             Data
```

---

## 🚨 The Problem

AI agents are moving beyond simple question-answering systems.

Modern agents can:

* Call APIs
* Query databases
* Read files
* Send emails
* Execute tools
* Access SaaS applications
* Modify records
* Trigger financial transactions
* Interact with infrastructure
* Call other AI agents

This creates a fundamentally different security problem.

Traditional authorization asks:

> **"Does this identity have permission to call this API?"**

AgentShield asks:

> **"Should this particular agent be allowed to perform this particular action, on this particular resource, in this particular task context, right now?"**

For example:

```text
Customer Support Agent
        │
        ├── Read customer #1234        ✅
        ├── Read order #9821           ✅
        ├── Create support ticket      ✅
        ├── Refund ₹2,000              ✅
        ├── Refund ₹50,000             ⚠️ Approval
        ├── Read customer #9876        ❌
        ├── Access payroll database    ❌
        └── Create IAM user             ❌
```

AgentShield provides the security boundary required to enforce these decisions.

---

# 🎯 Core Philosophy

AgentShield follows a **Zero-Trust model for AI agents**.

```text
Never trust the agent.
Never trust the tool.
Never trust the request.

Verify every action.
```

The agent itself should not be the final authority for security decisions.

Instead:

```text
AI Agent
   │
   │ Intent / Action
   ▼
AgentShield
   │
   ├── Who is the agent?
   ├── What task is it performing?
   ├── What capability is requested?
   ├── Which resource is being accessed?
   ├── Is the action within task scope?
   ├── Does policy permit it?
   ├── What is the risk?
   ├── Is sensitive data involved?
   └── Is this normal agent behavior?
   │
   ▼
Security Decision
   │
   ├── ALLOW
   ├── DENY
   ├── REQUIRE_APPROVAL
   └── REDACT
```

---

# ✨ Key Features

## 1. Agent Identity

Every AI agent receives a unique security identity.

```yaml
agent:
  id: customer-support-agent
  owner: customer-success
  environment: production
  purpose: customer-support
  status: active
```

AgentShield tracks:

* Agent identity
* Owner
* Purpose
* Environment
* Capabilities
* Risk level
* Status
* Credentials

---

## 2. Task-Bound Authorization

Permissions are associated with the **current task**, rather than permanently trusting an agent.

Example:

```yaml
task:
  id: TASK-98231

  agent:
    id: customer-support-agent

  intent:
    type: refund_order

  capabilities:
    - get_order
    - get_customer
    - create_refund
```

When the task finishes, task-specific permissions expire.

```text
Task Started
     │
     ▼
Temporary Security Context
     │
     ▼
Actions Allowed
     │
     ▼
Task Completed
     │
     ▼
Permissions Revoked
```

This follows the principles of:

* Least privilege
* Just-in-time authorization
* Just-enough access
* Context-aware authorization

---

# 🔐 3. Capability-Based Security

Agents do not receive unrestricted API access.

Capabilities define what an agent can do.

Example:

```text
read_customer
read_order
create_ticket
send_email
create_refund
read_invoice
read_file
```

The authorization flow becomes:

```text
Agent
  ↓
Task
  ↓
Capability
  ↓
Resource
  ↓
Action
  ↓
Policy
  ↓
Decision
```

---

# 📜 4. Policy Engine

Security policies define what agents are allowed to do.

Example:

```yaml
policy:
  name: customer-refund-policy

  agent: customer-support-agent

  action: create_refund

  conditions:
    amount:
      max: 5000

    customer:
      must_match_task_customer: true

  decision: allow
```

Supported decisions:

```text
ALLOW
DENY
REQUIRE_APPROVAL
REDACT
```

The policy engine is designed to remain independent from the AI model.

---

# 🚪 5. Runtime Security Gateway

AgentShield acts as a security gateway between agents and target services.

```text
AI Agent
    │
    │ HTTP Request
    ▼
┌────────────────────┐
│ AgentShield Gateway│
└─────────┬──────────┘
          │
          ├── Authenticate Agent
          ├── Validate Task
          ├── Check Capability
          ├── Evaluate Policy
          ├── Calculate Risk
          ├── Inspect Resource
          ├── Inspect Data
          └── Generate Audit Event
          │
          ▼
     Target API
```

---

# 🧱 6. Resource-Level Authorization

AgentShield is designed to protect against BOLA/IDOR-style attacks.

Example:

```text
Task:

Customer = 123

Allowed:

GET /customers/123
```

If the agent attempts:

```text
GET /customers/987
```

AgentShield evaluates:

```text
Task Customer:       123
Requested Customer:  987

Resource mismatch detected.

Decision:
DENY

Risk:
HIGH
```

---

# 🧠 7. Risk Engine

Every action can receive a risk score.

Example:

```text
Base Risk
    +
Sensitive Resource
    +
High Privilege Action
    +
Unexpected Endpoint
    +
Out-of-Scope Resource
    +
Behavioral Deviation
    +
Large Transaction
    =
Risk Score
```

Example thresholds:

```text
0 – 29       LOW
30 – 59      MEDIUM
60 – 79      HIGH
80 – 100     CRITICAL
```

The initial implementation uses deterministic rules.

Future versions can incorporate statistical and ML-based detection.

---

# 👁️ 8. Agent Behavior Monitoring

AgentShield establishes a behavioral baseline for agents.

Example:

```text
CustomerSupportAgent

Normal:

GET /customers/*
GET /orders/*
POST /tickets
POST /emails
```

Unexpected behavior:

```text
CustomerSupportAgent
        │
        └── POST /iam/users
```

AgentShield can detect:

```text
Unexpected Service
Unexpected Endpoint
Unexpected Capability
Unexpected Action
```

and increase the risk score.

---

# 🔒 9. Data Security

AgentShield can classify sensitive data.

Example classifications:

```text
PUBLIC
INTERNAL
CONFIDENTIAL
PII
SECRET
CRITICAL
```

Initial detection can include:

* Email addresses
* Phone numbers
* Payment card patterns
* Aadhaar-like identifiers
* API keys
* JWTs
* Passwords
* Secrets

Example:

```json
{
  "name": "John",
  "email": "john@example.com",
  "credit_card": "4111111111111111"
}
```

can become:

```json
{
  "name": "John",
  "email": "john@example.com",
  "credit_card": "[REDACTED]"
}
```

This prevents unnecessary sensitive information from reaching an AI model.

---

# 🔌 10. MCP Security

AgentShield is designed to support **Model Context Protocol (MCP)** security.

Future architecture:

```text
AI Agent
    │
    ▼
AgentShield
    │
    ▼
MCP Security Gateway
    │
    ▼
MCP Server
    │
    ▼
Tool
```

AgentShield can eventually evaluate:

* MCP server identity
* Tool identity
* Tool capabilities
* Tool arguments
* Resource access
* Data sensitivity
* Agent authorization
* Runtime behavior

---

# 🕸️ 11. Agent Security Graph

A future component will maintain a graph representing agent relationships.

```text
User
 │
 └── owns
       │
       ▼
     Agent
       │
       ├── uses
       ▼
      Tool
       │
       ├── accesses
       ▼
      API
       │
       ├── reads
       ▼
    Database
       │
       └── contains
              │
              ▼
             PII
```

This enables questions such as:

> What can this agent reach?

and:

> What is the blast radius if this agent is compromised?

---

# 💥 Agent Blast-Radius Analysis

One of the long-term goals of AgentShield is to calculate the potential impact of a compromised AI agent.

Example:

```text
Compromised Agent
        │
        ▼
Available Capabilities
        │
        ▼
Reachable APIs
        │
        ▼
Reachable Databases
        │
        ▼
Sensitive Data
        │
        ▼
Potential Blast Radius
```

This allows security teams to understand the consequences of excessive agent permissions.

---

# 🏗️ Architecture

## High-Level Architecture

```text
                       ┌──────────────────┐
                       │     User         │
                       └────────┬─────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │    AI Agent      │
                       └────────┬─────────┘
                                │
                                ▼
                ┌──────────────────────────────┐
                │       AgentShield            │
                │                              │
                │ ┌──────────────────────────┐ │
                │ │ Agent Identity            │ │
                │ └──────────────────────────┘ │
                │                              │
                │ ┌──────────────────────────┐ │
                │ │ Task Context             │ │
                │ └──────────────────────────┘ │
                │                              │
                │ ┌──────────────────────────┐ │
                │ │ Capability Engine        │ │
                │ └──────────────────────────┘ │
                │                              │
                │ ┌──────────────────────────┐ │
                │ │ Policy Engine            │ │
                │ └──────────────────────────┘ │
                │                              │
                │ ┌──────────────────────────┐ │
                │ │ Risk Engine              │ │
                │ └──────────────────────────┘ │
                │                              │
                │ ┌──────────────────────────┐ │
                │ │ Data Security            │ │
                │ └──────────────────────────┘ │
                │                              │
                │ ┌──────────────────────────┐ │
                │ │ Behavior Analysis        │ │
                │ └──────────────────────────┘ │
                │                              │
                │ ┌──────────────────────────┐ │
                │ │ Audit / Events           │ │
                │ └──────────────────────────┘ │
                └──────────────┬───────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
          REST APIs           MCP           Databases
              │                │                │
              ▼                ▼                ▼
          Services           Tools             Data
```

---

# 🔄 Request Evaluation Flow

```text
1. Agent sends request
          │
          ▼
2. Authenticate Agent
          │
          ▼
3. Validate Task
          │
          ▼
4. Extract Action
          │
          ▼
5. Resolve Resource
          │
          ▼
6. Check Capability
          │
          ▼
7. Evaluate Policy
          │
          ▼
8. Calculate Risk
          │
          ▼
9. Inspect Sensitive Data
          │
          ▼
10. Evaluate Behavior
          │
          ▼
11. Security Decision
          │
     ┌────┼─────────────┐
     ▼    ▼             ▼
   ALLOW DENY       APPROVAL
     │    │             │
     └────┴─────────────┘
              │
              ▼
       Audit Event
```

---

# 🧰 Technology Stack

| Component          | Technology    |
| ------------------ | ------------- |
| Language           | Python        |
| API Framework      | FastAPI       |
| Validation         | Pydantic      |
| Database           | PostgreSQL    |
| Cache              | Redis         |
| Event Streaming    | Kafka         |
| Search / Analytics | OpenSearch    |
| Observability      | OpenTelemetry |
| Metrics            | Prometheus    |
| Dashboards         | Grafana       |
| Containers         | Docker        |
| API Specification  | OpenAPI       |
| Testing            | Pytest        |

Some components may remain optional during v0.1 to keep the local deployment lightweight.

---

# 📁 Project Structure

```text
agentshield/
│
├── gateway/
│   ├── routes/
│   ├── middleware/
│   └── proxy/
│
├── identity/
│   ├── models/
│   ├── services/
│   └── authentication/
│
├── policy_engine/
│   ├── evaluator/
│   ├── rules/
│   └── schemas/
│
├── risk_engine/
│   ├── scoring/
│   └── rules/
│
├── behavior/
│   ├── baseline/
│   └── anomaly/
│
├── data_security/
│   ├── classifier/
│   ├── detectors/
│   └── redaction/
│
├── api_inventory/
│   ├── openapi/
│   └── discovery/
│
├── audit/
│   ├── events/
│   └── storage/
│
├── integrations/
│   ├── mcp/
│   ├── kafka/
│   └── opensearch/
│
├── models/
├── schemas/
├── tests/
│
├── attack_lab/
│   ├── bola/
│   ├── privilege_escalation/
│   ├── data_exfiltration/
│   ├── excessive_refund/
│   └── stolen_credentials/
│
├── docs/
│
├── docker/
│
├── docker-compose.yml
├── .env.example
├── Makefile
├── pyproject.toml
└── README.md
```

---

# 🧪 Attack Lab

AgentShield includes an intentionally vulnerable environment for demonstrating attacks against AI agents.

## Attack 1 — BOLA

```text
Agent
  │
  └── GET /customers/987

Task Customer:
123

Result:
❌ DENY
```

---

## Attack 2 — Privilege Escalation

```text
CustomerSupportAgent
        │
        └── POST /iam/users

Result:
❌ DENY

Reason:
Agent lacks IAM capability
```

---

## Attack 3 — Excessive Refund

```text
Agent
 │
 └── Refund ₹50,000

Policy:
Maximum ₹5,000

Result:
⚠️ REQUIRE_APPROVAL
```

---

## Attack 4 — Sensitive Data Exfiltration

```text
Agent
 │
 ├── Read sensitive data
 │
 └── Send externally
```

AgentShield:

```text
Sensitive data detected
        │
        ▼
Policy evaluation
        │
        ▼
❌ BLOCK / REDACT
```

---

## Attack 5 — Behavioral Anomaly

```text
Normal:

Customer Agent
 ├── CRM
 ├── Orders
 └── Tickets

Attack:

Customer Agent
 └── IAM
```

Result:

```text
⚠️ HIGH RISK
❌ BLOCK
```

---

# 📊 Observability

AgentShield exposes security metrics such as:

```text
agent_requests_total

allowed_requests_total

blocked_requests_total

policy_evaluations_total

high_risk_events_total

gateway_request_latency

policy_evaluation_latency
```

The observability architecture is:

```text
AgentShield
    │
    ├── OpenTelemetry
    │
    ├── Prometheus
    │
    └── Grafana
```

---

# 🔐 Security Model

AgentShield is designed around several security principles.

### Zero Trust

Every agent action is independently evaluated.

### Least Privilege

Agents receive only the capabilities required for their tasks.

### Just-In-Time Access

Task-specific permissions should expire.

### Defense in Depth

Multiple independent security controls evaluate requests.

### Deterministic Enforcement

LLMs may assist with intent understanding and risk analysis, but deterministic policy enforcement remains authoritative.

### Data Minimization

Agents should receive only the data required to complete their tasks.

### Complete Auditability

Security-sensitive actions should produce auditable events.

---

# 🛣️ Roadmap

## v0.1 — Runtime Security MVP

* [ ] Agent identity
* [ ] Agent API keys
* [ ] Capabilities
* [ ] Task context
* [ ] Task-bound permissions
* [ ] Policy engine
* [ ] Runtime gateway
* [ ] Resource-level authorization
* [ ] Risk scoring
* [ ] Behavioral baseline
* [ ] Basic data classification
* [ ] Audit logging
* [ ] Attack lab
* [ ] Docker Compose
* [ ] Unit/integration/security tests

---

## v0.2 — MCP Security

* [ ] MCP gateway
* [ ] MCP tool identity
* [ ] Tool authorization
* [ ] MCP server trust
* [ ] Tool argument inspection
* [ ] MCP security policies

---

## v0.3 — Agent Security Graph

* [ ] Agent relationship graph
* [ ] Capability graph
* [ ] API/resource graph
* [ ] Sensitive data graph
* [ ] Blast-radius analysis

---

## v0.4 — Advanced Detection

* [ ] ML-based behavior detection
* [ ] Advanced anomaly detection
* [ ] Threat intelligence
* [ ] Agent attack detection
* [ ] Automated response

---

## v1.0 — Enterprise Platform

Potential capabilities:

```text
Agent Identity
        +
Runtime Authorization
        +
MCP Security
        +
API Security
        +
Agent DLP
        +
Behavior Analytics
        +
Security Graph
        +
Blast-Radius Analysis
        +
SIEM Integration
        +
Enterprise SSO
```

---

# 🎯 Target Users

AgentShield is intended for:

* Security Engineers
* AI/ML Engineers
* Platform Engineers
* DevSecOps Teams
* Cloud Security Teams
* SOC Teams
* CISOs
* Organizations deploying autonomous AI agents

Potential use cases include:

```text
Customer Support Agents
Finance Agents
Sales Agents
DevOps Agents
Security Agents
Data Analysis Agents
Internal Enterprise Agents
MCP-based Agents
```

---

# 💡 What Makes AgentShield Different?

AgentShield is not intended to be another:

* ❌ Prompt injection detector
* ❌ Traditional API gateway
* ❌ Vulnerability scanner
* ❌ SIEM
* ❌ SAST tool
* ❌ Generic DLP system
* ❌ AI chatbot security wrapper

The core idea is:

```text
                 AI AGENT
                     │
                     ▼
        ┌─────────────────────────┐
        │     Agent Identity      │
        └────────────┬────────────┘
                     ▼
        ┌─────────────────────────┐
        │      Task Context       │
        └────────────┬────────────┘
                     ▼
        ┌─────────────────────────┐
        │      Capabilities       │
        └────────────┬────────────┘
                     ▼
        ┌─────────────────────────┐
        │   Runtime Authorization │
        └────────────┬────────────┘
                     ▼
        ┌─────────────────────────┐
        │       Risk Engine       │
        └────────────┬────────────┘
                     ▼
        ┌─────────────────────────┐
        │      Data Security      │
        └────────────┬────────────┘
                     ▼
              ALLOW / DENY
```

The long-term goal is to create a **security control plane for autonomous AI agents**.

---

# 🚀 Quick Start

> v0.1 development instructions will be added as the implementation progresses.

Expected startup:

```bash
git clone <repository-url>

cd agentshield

cp .env.example .env

docker compose up -d
```

API:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

---

# 🧪 Development

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

### Linux/macOS

```bash
source .venv/bin/activate
```

### Windows

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

Run the application:

```bash
uvicorn app.main:app --reload
```

---

# 📚 Documentation

Detailed documentation will be maintained under:

```text
docs/
├── architecture/
├── threat-model/
├── security/
├── api/
├── policy-engine/
├── risk-engine/
├── attack-lab/
└── deployment/
```

---

# 🤝 Contributing

Contributions are welcome.

Potential contribution areas:

* Security policies
* Detection rules
* MCP integrations
* API integrations
* Attack simulations
* Threat modeling
* Documentation
* Testing
* Observability
* Performance improvements

Before contributing security-sensitive functionality, please document:

```text
Threat
↓
Attack Vector
↓
Security Control
↓
Implementation
↓
Test
```

---

# ⚠️ Security Disclaimer

AgentShield is an experimental cybersecurity project under active development.

It should **not be considered production-ready security software** until it has undergone appropriate security review, penetration testing, threat modeling, dependency analysis, and operational validation.

The attack lab intentionally contains vulnerable components for educational and testing purposes.

Do not deploy the attack-lab services to an untrusted or production environment.

---

# 📜 License

License information will be added before the first public release.

---

# 🌟 Project Vision

The long-term vision of AgentShield is simple:

> **Every autonomous AI agent should have an identity, a security boundary, least-privilege capabilities, runtime authorization, and a measurable blast radius.**

As AI agents become capable of taking increasingly autonomous actions, security must evolve from:

```text
Protect the application
```

to:

```text
Protect the agent's ability to act.
```

AgentShield aims to become that security layer.

---

## ⭐ If You Find This Project Interesting

Star the repository, experiment with the attack lab, open issues, and contribute security ideas.

**AgentShield — Zero Trust for Autonomous AI Agents.**
