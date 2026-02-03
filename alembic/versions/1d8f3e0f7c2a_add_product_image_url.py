"""add image_url to products

Revision ID: 1d8f3e0f7c2a
Revises: b3c9d6b2c3f0
Create Date: 2026-02-03
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "1d8f3e0f7c2a"
down_revision = "b3c9d6b2c3f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.add_column(sa.Column("image_url", sa.String(length=512), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.drop_column("image_url")
