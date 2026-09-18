"""Unit tests for task Pydantic schemas."""

from uuid import uuid4
import pytest
from pydantic import ValidationError

from agentshield.domain.task.models import TaskPriority
from agentshield.schemas.task import (
    TaskCompleteRequest,
    TaskCreate,
    TaskExtendRequest,
    TaskUpdate,
)


class TestTaskSchemas:
    """Test suite for task schemas."""

    def test_task_create_valid(self) -> None:
        """Test valid TaskCreate schema."""
        task = TaskCreate(
            agent_id=uuid4(),
            user_id="alice",
            intent_type="process_refund",
            priority=TaskPriority.HIGH,
            expires_in_minutes=120,
            capabilities=["create_refund"],
            context={"refund_amount": 50},
        )
        assert task.user_id == "alice"
        assert task.intent_type == "process_refund"
        assert task.expires_in_minutes == 120
        assert task.capabilities == ["create_refund"]

    def test_task_create_validation_errors(self) -> None:
        """Test TaskCreate invalid constraints."""
        # Empty user_id
        with pytest.raises(ValidationError):
            TaskCreate(
                agent_id=uuid4(),
                user_id="",
                intent_type="test",
            )

        # Negative / 0 expiration
        with pytest.raises(ValidationError):
            TaskCreate(
                agent_id=uuid4(),
                user_id="user1",
                intent_type="test",
                expires_in_minutes=0,
            )

        # Exceeding 24 hours (1440 minutes)
        with pytest.raises(ValidationError):
            TaskCreate(
                agent_id=uuid4(),
                user_id="user1",
                intent_type="test",
                expires_in_minutes=2000,
            )

    def test_task_update_schema(self) -> None:
        """Test TaskUpdate fields."""
        update = TaskUpdate(
            priority=TaskPriority.CRITICAL,
            context={"updated": True},
            expires_in_minutes=30,
        )
        assert update.priority == TaskPriority.CRITICAL
        assert update.context == {"updated": True}
        assert update.expires_in_minutes == 30

    def test_task_complete_and_extend_schemas(self) -> None:
        """Test TaskCompleteRequest and TaskExtendRequest."""
        comp = TaskCompleteRequest(result_data={"code": 200, "status": "ok"})
        assert comp.result_data == {"code": 200, "status": "ok"}

        extend = TaskExtendRequest(additional_minutes=45, reason="Need more time")
        assert extend.additional_minutes == 45
        assert extend.reason == "Need more time"

        with pytest.raises(ValidationError):
            TaskExtendRequest(additional_minutes=0)

