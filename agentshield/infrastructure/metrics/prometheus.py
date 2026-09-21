"""Prometheus metrics for AgentShield."""

from datetime import datetime

from prometheus_client import (
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

# ============================================================================
# Request Metrics
# ============================================================================

# Total requests by decision
agent_requests_total = Counter(
    'agentshield_requests_total',
    'Total agent requests processed',
    ['agent_id', 'decision', 'action', 'environment']
)

# Request latency
request_latency_seconds = Histogram(
    'agentshield_request_latency_seconds',
    'Request latency in seconds',
    ['agent_id', 'decision'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# Request rate by agent
request_rate = Gauge(
    'agentshield_request_rate',
    'Request rate per minute',
    ['agent_id']
)

# ============================================================================
# Security Metrics
# ============================================================================

# Blocked requests by reason
blocked_requests_total = Counter(
    'agentshield_blocked_requests_total',
    'Total blocked requests by reason',
    ['agent_id', 'reason', 'severity']
)

# High-risk events
high_risk_events_total = Counter(
    'agentshield_high_risk_events_total',
    'Total high-risk events',
    ['agent_id', 'risk_level', 'action']
)

# Policy violations
policy_violations_total = Counter(
    'agentshield_policy_violations_total',
    'Total policy violations',
    ['agent_id', 'policy_name', 'violation_type']
)

# ============================================================================
# Policy Engine Metrics
# ============================================================================

# Policy evaluations
policy_evaluations_total = Counter(
    'agentshield_policy_evaluations_total',
    'Total policy evaluations',
    ['policy_id', 'decision']
)

# Policy evaluation latency
policy_evaluation_latency_seconds = Histogram(
    'agentshield_policy_evaluation_latency_seconds',
    'Policy evaluation latency in seconds',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)

# Active policies
active_policies = Gauge(
    'agentshield_active_policies',
    'Number of active policies',
    ['type']
)

# ============================================================================
# Risk Metrics
# ============================================================================

# Risk scores
risk_score_histogram = Histogram(
    'agentshield_risk_scores',
    'Risk score distribution',
    ['agent_id', 'decision'],
    buckets=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
)

# Risk score average
risk_score_average = Gauge(
    'agentshield_risk_score_average',
    'Average risk score',
    ['agent_id', 'environment']
)

# ============================================================================
# Gateway Metrics
# ============================================================================

# Gateway health
gateway_health = Gauge(
    'agentshield_gateway_health',
    'Gateway health status (1=healthy, 0=unhealthy)'
)

# Active tasks
active_tasks = Gauge(
    'agentshield_active_tasks',
    'Number of active tasks',
    ['agent_id']
)

# Rate limit hits
rate_limit_hits_total = Counter(
    'agentshield_rate_limit_hits_total',
    'Total rate limit hits',
    ['agent_id', 'limit_type']
)

# ============================================================================
# Data Security Metrics
# ============================================================================

# Sensitive data detections
sensitive_data_detected_total = Counter(
    'agentshield_sensitive_data_detected_total',
    'Total sensitive data detections',
    ['agent_id', 'classification', 'action']
)

# Redacted responses
redacted_responses_total = Counter(
    'agentshield_redacted_responses_total',
    'Total redacted responses',
    ['agent_id', 'classification']
)

# ============================================================================
# System Metrics
# ============================================================================

# System information
system_info = Info(
    'agentshield_system_info',
    'System information'
)

# Service uptime
service_uptime = Gauge(
    'agentshield_service_uptime_seconds',
    'Service uptime in seconds'
)

# Database connection pool
db_pool_size = Gauge(
    'agentshield_db_pool_size',
    'Database connection pool size'
)

db_pool_overflow = Gauge(
    'agentshield_db_pool_overflow',
    'Database connection pool overflow'
)

# Cache metrics
cache_hit_rate = Gauge(
    'agentshield_cache_hit_rate',
    'Cache hit rate',
    ['cache_type']
)

# ============================================================================
# Helper Functions
# ============================================================================

def record_request(
    agent_id: str,
    decision: str,
    action: str,
    environment: str = "development",
    latency: float = 0.0
) -> None:
    """Record a request metric."""
    agent_requests_total.labels(
        agent_id=agent_id,
        decision=decision,
        action=action,
        environment=environment
    ).inc()

    request_latency_seconds.labels(
        agent_id=agent_id,
        decision=decision
    ).observe(latency)


def record_blocked_request(
    agent_id: str,
    reason: str,
    severity: str = "medium"
) -> None:
    """Record a blocked request metric."""
    blocked_requests_total.labels(
        agent_id=agent_id,
        reason=reason,
        severity=severity
    ).inc()


def record_policy_evaluation(
    policy_id: str,
    decision: str,
    latency: float = 0.0
) -> None:
    """Record a policy evaluation metric."""
    policy_evaluations_total.labels(
        policy_id=policy_id,
        decision=decision
    ).inc()

    policy_evaluation_latency_seconds.observe(latency)


def record_risk_score(
    agent_id: str,
    score: int,
    decision: str = "allow"
) -> None:
    """Record a risk score metric."""
    risk_score_histogram.labels(
        agent_id=agent_id,
        decision=decision
    ).observe(score)


def record_sensitive_data(
    agent_id: str,
    classification: str,
    action: str = "detect"
) -> None:
    """Record sensitive data detection metric."""
    sensitive_data_detected_total.labels(
        agent_id=agent_id,
        classification=classification,
        action=action
    ).inc()


def record_high_risk_event(
    agent_id: str,
    risk_level: str,
    action: str
) -> None:
    """Record a high-risk event."""
    high_risk_events_total.labels(
        agent_id=agent_id,
        risk_level=risk_level,
        action=action
    ).inc()


def record_policy_violation(
    agent_id: str,
    policy_name: str,
    violation_type: str
) -> None:
    """Record a policy violation."""
    policy_violations_total.labels(
        agent_id=agent_id,
        policy_name=policy_name,
        violation_type=violation_type
    ).inc()


def record_rate_limit_hit(
    agent_id: str,
    limit_type: str = "agent"
) -> None:
    """Record a rate limit hit."""
    rate_limit_hits_total.labels(
        agent_id=agent_id,
        limit_type=limit_type
    ).inc()


def update_active_tasks(agent_id: str, count: int) -> None:
    """Update active tasks count."""
    active_tasks.labels(agent_id=agent_id).set(count)


def update_risk_score_average(agent_id: str, environment: str, score: float) -> None:
    """Update average risk score."""
    risk_score_average.labels(
        agent_id=agent_id,
        environment=environment
    ).set(score)


def update_gateway_health(status: bool) -> None:
    """Update gateway health status."""
    gateway_health.set(1 if status else 0)


def update_system_info(version: str, environment: str) -> None:
    """Update system information."""
    system_info.info({
        'version': version,
        'environment': environment,
        'started_at': datetime.utcnow().isoformat()
    })


async def get_metrics() -> str:
    """Get current metrics in Prometheus format."""
    return generate_latest(REGISTRY)
