"""add stock_qty to products

Revision ID: 6d2f8d1a9c44
Revises: 3c7b2f9e4d21
Create Date: 2026-02-03
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "6d2f8d1a9c44"
down_revision = "3c7b2f9e4d21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.add_column(sa.Column("stock_qty", sa.Integer(), nullable=False, server_default="0"))
    # drop server_default after backfill
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.alter_column("stock_qty", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.drop_column("stock_qty")
