"""Initial schema - users, tasks, task_audit_log

Revision ID: f3378c124740
Revises:
Create Date: 2026-01-03 18:03:02.531881

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'f3378c124740'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('oauth_sub', sa.String(255), unique=True, nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_oauth_sub', 'users', ['oauth_sub'])

    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('priority', sa.String(50), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.CheckConstraint("status IN ('pending', 'in_progress', 'completed')", name='valid_status'),
        sa.CheckConstraint("priority IN ('low', 'medium', 'high')", name='valid_priority'),
    )
    op.create_index('ix_tasks_id', 'tasks', ['id'])
    op.create_index('ix_tasks_user_id', 'tasks', ['user_id'])
    op.create_index('ix_tasks_status', 'tasks', ['status'])
    op.create_index('ix_tasks_priority', 'tasks', ['priority'])
    op.create_index('ix_tasks_due_date', 'tasks', ['due_date'])
    op.create_index('ix_tasks_user_id_status', 'tasks', ['user_id', 'status'])
    op.create_index('ix_tasks_user_id_priority', 'tasks', ['user_id', 'priority'])
    op.create_index('ix_tasks_due_date_status', 'tasks', ['due_date', 'status'])

    # Create task_audit_log table
    op.create_table(
        'task_audit_log',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('task_id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('old_status', sa.String(50), nullable=True),
        sa.Column('new_status', sa.String(50), nullable=True),
        sa.Column('extra_data', sa.Text, nullable=True),  # Renamed from 'metadata' to avoid SQLAlchemy reserved word
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )
    op.create_index('ix_task_audit_log_id', 'task_audit_log', ['id'])
    op.create_index('ix_task_audit_log_task_id', 'task_audit_log', ['task_id'])
    op.create_index('ix_task_audit_log_user_id', 'task_audit_log', ['user_id'])
    op.create_index('ix_task_audit_log_created_at', 'task_audit_log', ['created_at'])
    op.create_index('ix_audit_task_user', 'task_audit_log', ['task_id', 'user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('task_audit_log')
    op.drop_table('tasks')
    op.drop_table('users')
