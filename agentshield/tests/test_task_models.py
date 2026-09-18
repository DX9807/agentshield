"""Unit tests for task domain models."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from agentshield.domain.task.models import (
    Task,
    TaskCapability,
    TaskContextLog,
    TaskPriority,
    TaskStatus,
)


class TestTaskModels:
    """Test suite for task domain models."""

    def test_task_status_enum_values(self) -> None:
        """Test task status enum values."""
        assert TaskStatus.ACTIVE == "active"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.EXPIRED == "expired"
        assert TaskStatus.REVOKED == "revoked"

    def test_task_priority_enum_values(self) -> None:
        """Test task priority enum values."""
        assert TaskPriority.LOW == "low"
        assert TaskPriority.MEDIUM == "medium"
        assert TaskPriority.HIGH == "high"
        assert TaskPriority.CRITICAL == "critical"

    def test_task_lifecycle_properties(self) -> None:
        """Test task is_active and is_expired properties."""
        now = datetime.now(timezone.utc)
        task = Task(
            agent_id=uuid4(),
            user_id="alice",
            intent_type="search_docs",
            status=TaskStatus.ACTIVE,
            priority=TaskPriority.MEDIUM,
            expires_at=now + timedelta(hours=1),
            context={"repo": "agentshield"},
        )
        assert task.is_active is True
        assert task.is_expired is False

        # Expired task
        task.expires_at = now - timedelta(seconds=1)
        assert task.is_active is False
        assert task.is_expired is True

    def test_task_complete(self) -> None:
        """Test completing a task."""
        task = Task(
            agent_id=uuid4(),
            user_id="bob",
            intent_type="execute_query",
            status=TaskStatus.ACTIVE,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        task.complete()
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert task.is_active is False

    def test_task_revoke(self) -> None:
        """Test revoking a task."""
        task = Task(
            agent_id=uuid4(),
            user_id="charlie",
            intent_type="download_file",
            status=TaskStatus.ACTIVE,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
        task.revoke()
        assert task.status == TaskStatus.REVOKED
        assert task.completed_at is not None
        assert task.is_active is False

    def test_task_extend(self) -> None:
        """Test extending an active task."""
        now = datetime.now(timezone.utc)
        initial_exp = now + timedelta(minutes=10)
        task = Task(
            agent_id=uuid4(),
            user_id="dana",
            intent_type="audit_logs",
            status=TaskStatus.ACTIVE,
            expires_at=initial_exp,
        )
        task.extend(20)
        assert task.expires_at > initial_exp
        assert task.is_active is True

    def test_task_context_helpers(self) -> None:
        """Test context retrieval and key presence methods."""
        task = Task(
            agent_id=uuid4(),
            user_id="eve",
            intent_type="generate_report",
            status=TaskStatus.ACTIVE,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            context={"report_format": "pdf", "max_rows": 100},
        )
        assert task.has_context_key("report_format") is True
        assert task.has_context_key("nonexistent") is False
        assert task.get_context_value("report_format") == "pdf"
        assert task.get_context_value("missing", default=42) == 42

    def test_task_capability_and_context_log(self) -> None:
        """Test TaskCapability and TaskContextLog models."""
        task_id = uuid4()
        cap_id = uuid4()

        task_cap = TaskCapability(
            task_id=task_id,
            capability_id=cap_id,
            is_active=True,
        )
        assert task_cap.task_id == task_id
        assert task_cap.capability_id == cap_id
        assert task_cap.is_active is True

        log = TaskContextLog(
            task_id=task_id,
            field="priority",
            old_value="medium",
            new_value="high",
            changed_by="admin",
        )
        assert log.field == "priority"
        assert log.changed_by == "admin"

