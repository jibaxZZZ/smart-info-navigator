"""Database models for Workflow Orchestrator.

These are SQLAlchemy ORM models mapped to PostgreSQL tables.
"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from ..database import Base
from ..utils.logging import get_logger

logger = get_logger(__name__)


def utcnow() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


class User(Base):
    """User model representing authenticated users via OAuth."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    oauth_sub = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("TaskAuditLog", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, oauth_sub={self.oauth_sub})>"


class Task(Base):
    """Task model representing workflow tasks."""

    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        String(50), nullable=False, default="pending", index=True
    )  # pending, in_progress, completed
    priority = Column(
        String(50), nullable=False, default="medium", index=True
    )  # low, medium, high
    due_date = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="tasks")
    audit_logs = relationship("TaskAuditLog", back_populates="task", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed')", name="valid_status"
        ),
        CheckConstraint("priority IN ('low', 'medium', 'high')", name="valid_priority"),
        Index("ix_tasks_user_id_status", "user_id", "status"),
        Index("ix_tasks_user_id_priority", "user_id", "priority"),
        Index("ix_tasks_due_date_status", "due_date", "status"),
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title={self.title}, status={self.status}, priority={self.priority})>"

    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.due_date or self.status == "completed":
            return False
        return self.due_date < utcnow()


class TaskAuditLog(Base):
    """Audit log for task changes."""

    __tablename__ = "task_audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    action = Column(String(50), nullable=False)  # created, status_update, deleted, etc.
    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)
    extra_data = Column(Text, nullable=True)  # JSON string for additional context (renamed from 'metadata' to avoid SQLAlchemy conflict)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    # Relationships
    task = relationship("Task", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")

    # Indexes
    __table_args__ = (
        Index("ix_audit_task_user", "task_id", "user_id"),
        Index("ix_audit_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<TaskAuditLog(id={self.id}, task_id={self.task_id}, action={self.action})>"
