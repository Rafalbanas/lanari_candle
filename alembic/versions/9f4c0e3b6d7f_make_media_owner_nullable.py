"""make media.owner_id nullable

Revision ID: 9f4c0e3b6d7f
Revises: 50cfc08ab455
Create Date: 2026-02-03
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "9f4c0e3b6d7f"
down_revision = "50cfc08ab455"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("media", schema=None) as batch_op:
        batch_op.alter_column("owner_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("media", schema=None) as batch_op:
        batch_op.alter_column("owner_id", existing_type=sa.Integer(), nullable=False)
