"""add is_public to media

Revision ID: 3c7b2f9e4d21
Revises: 1d8f3e0f7c2a
Create Date: 2026-02-03
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "3c7b2f9e4d21"
down_revision = "1d8f3e0f7c2a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("media", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()))
    # remove server_default after backfill
    with op.batch_alter_table("media", schema=None) as batch_op:
        batch_op.alter_column("is_public", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("media", schema=None) as batch_op:
        batch_op.drop_column("is_public")
