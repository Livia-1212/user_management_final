"""Add invited_by_user_id and is_converted to users

Revision ID: 48f8fe797358
Revises: 25d814bc83ed
Create Date: 2024-12-16 18:48:19.560627

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '48f8fe797358'
down_revision: Union[str, None] = '25d814bc83ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### Create the retention_analytics table ###
    op.create_table(
        'retention_analytics',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('total_anonymous_users', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_authenticated_users', sa.Integer(), server_default='0', nullable=False),
        sa.Column('conversion_rate', sa.String(length=10), nullable=False),
        sa.Column('inactive_users_24hr', sa.Integer(), server_default='0', nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # ### Add new columns to users table ###
    # Only add 'is_converted' if it doesn't already exist
    if not column_exists("users", "is_converted"):
        op.add_column('users', sa.Column(
            'is_converted', sa.Boolean(), server_default=sa.sql.expression.false(), nullable=False
        ))

    # Add invited_by_user_id
    op.add_column('users', sa.Column(
        'invited_by_user_id', sa.UUID(), nullable=True
    ))

    # Add foreign key for invited_by_user_id
    op.create_foreign_key('fk_users_invited_by', 'users', 'users', ['invited_by_user_id'], ['id'])


def downgrade() -> None:
    # ### Drop added foreign keys and columns ###
    op.drop_constraint('fk_users_invited_by', 'users', type_='foreignkey')
    op.drop_column('users', 'invited_by_user_id')

    # Drop 'is_converted' column
    op.drop_column('users', 'is_converted')

    # Drop the retention_analytics table
    op.drop_table('retention_analytics')


# Utility Function: Check for column existence
def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns
