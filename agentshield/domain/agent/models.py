"""Agent identity domain models."""

import secrets
from datetime import datetime
from enum import Enum

import bcrypt
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from ...infrastructure.database.base import AuditMixin, BaseModel


class AgentStatus(str, Enum):
    """
    Agent status enum.
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_APPROVAL = "pending_approval"


class AgentRiskLevel(str, Enum):
    """
    Agent risk level enum.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentEnvironment(str, Enum):
    """
    Agent environment enum.
    """

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Agent(BaseModel, AuditMixin):
    """
    Agent identity model.
    """

    __tablename__ = "agents"

    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    owner = Column(String(255), nullable=False)
    purpose = Column(Text, nullable=True)
    environment = Column(
        SQLEnum(AgentEnvironment), nullable=False, default=AgentEnvironment.DEVELOPMENT
    )
    risk_level = Column(SQLEnum(AgentRiskLevel), nullable=False, default=AgentRiskLevel.LOW)
    status = Column(SQLEnum(AgentStatus), nullable=False, default=AgentStatus.PENDING_APPROVAL)

    # Metadata
    metadata_json = Column(Text, nullable=True)  # JSON string for additional metadata

    # Relationships
    credentials = relationship(
        "AgentCredential", back_populates="agent", cascade="all, delete-orphan"
    )
    capabilities = relationship(
        "AgentCapability", back_populates="agent", cascade="all, delete-orphan"
    )
    tasks = relationship("Task", back_populates="agent")

    @hybrid_property
    def is_active(self) -> bool:
        """
        Check if agent is active.
        """
        return self.status == AgentStatus.ACTIVE

    @hybrid_property
    def is_suspended(self) -> bool:
        """
        Check if agent is suspended.
        """
        return self.status == AgentStatus.SUSPENDED

    def __repr__(self) -> str:
        return f"<Agent {self.name} ({self.id})>"


class AgentCredential(BaseModel):
    """
    Agent credential (API key) model.
    """

    __tablename__ = "agent_credentials"

    agent_id = Column(
        PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    credential_type = Column(String(50), nullable=False, default="api_key")
    credential_hash = Column(String(255), nullable=False)
    credential_prefix = Column(String(10), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    agent = relationship("Agent", back_populates="credentials")

    @classmethod
    def generate_api_key(cls) -> tuple[str, str, str]:
        """
        Generate a new API key with prefix.

        Returns:
            tuple: (full_api_key, hashed_key, prefix)
        """
        prefix = "ak_"
        suffix = secrets.token_urlsafe(32)  # 32 bytes = 256 bits
        api_key = f"{prefix}{suffix}"

        # Hash the key (excluding prefix for storage)
        hashed = bcrypt.hashpw(suffix.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        return api_key, hashed, prefix

    def verify_api_key(self, api_key: str) -> bool:
        """Verify an API key against the stored hash.

        Args:
            api_key: Full API key string to verify

        Returns:
            bool: True if valid, False otherwise
        """
        if not api_key.startswith(self.credential_prefix):
            return False

        # Extract the suffix
        suffix = api_key[len(self.credential_prefix) :]
        return bcrypt.checkpw(suffix.encode("utf-8"), self.credential_hash.encode("utf-8"))

    def __repr__(self) -> str:
        return f"<AgentCredential {self.credential_prefix}... for agent {self.agent_id}>"


class Capability(BaseModel):
    """
    Capability model.
    """

    __tablename__ = "capabilities"

    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)
    is_sensitive = Column(Boolean, nullable=False, default=False)
    requires_approval = Column(Boolean, nullable=False, default=False)

    # Relationships
    agent_assignments = relationship("AgentCapability", back_populates="capability")

    def __repr__(self) -> str:
        return f"<Capability {self.name}>"


class AgentCapability(BaseModel):
    """
    Many-to-many relationship between agents and capabilities.
    """

    __tablename__ = "agent_capabilities"

    agent_id = Column(
        PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    capability_id = Column(
        PGUUID(as_uuid=True), ForeignKey("capabilities.id", ondelete="CASCADE"), nullable=False
    )
    granted_by = Column(String(255), nullable=True)
    granted_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    agent = relationship("Agent", back_populates="capabilities")
    capability = relationship("Capability", back_populates="agent_assignments")

    __table_args__ = (UniqueConstraint("agent_id", "capability_id", name="uq_agent_capability"),)

    def __repr__(self) -> str:
        return f"<AgentCapability agent={self.agent_id} capability={self.capability_id}>"


# Predefined capabilities
class PredefinedCapabilities:
    """
    Predefined capabilities for common operations.
    """

    # Customer operations
    READ_CUSTOMER = "read_customer"
    WRITE_CUSTOMER = "write_customer"
    DELETE_CUSTOMER = "delete_customer"

    # Order operations
    READ_ORDER = "read_order"
    WRITE_ORDER = "write_order"
    DELETE_ORDER = "delete_order"
    CREATE_REFUND = "create_refund"

    # Ticket operations
    CREATE_TICKET = "create_ticket"
    READ_TICKET = "read_ticket"
    UPDATE_TICKET = "update_ticket"

    # Communication
    SEND_EMAIL = "send_email"
    SEND_NOTIFICATION = "send_notification"

    # File operations
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    DELETE_FILE = "delete_file"

    # Admin operations
    READ_INVOICE = "read_invoice"
    WRITE_INVOICE = "write_invoice"
    ACCESS_PAYROLL = "access_payroll"
    CREATE_IAM_USER = "create_iam_user"
    ACCESS_ADMIN_API = "access_admin_api"

    @classmethod
    def get_all(cls) -> list[str]:
        """
        Get all predefined capabilities.
        """
        return [
            getattr(cls, attr)
            for attr in dir(cls)
            if not attr.startswith("_") and isinstance(getattr(cls, attr), str)
        ]

    @classmethod
    def get_sensitive(cls) -> list[str]:
        """
        Get sensitive capabilities.
        """
        return [
            cls.DELETE_CUSTOMER,
            cls.DELETE_ORDER,
            cls.ACCESS_PAYROLL,
            cls.CREATE_IAM_USER,
            cls.ACCESS_ADMIN_API,
        ]
