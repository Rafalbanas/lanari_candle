"""add shipping fields

Revision ID: 7a6bde5fb3f1
Revises: b3c9d6b2c3f0
Create Date: 2026-02-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7a6bde5fb3f1"
down_revision: Union[str, Sequence[str], None] = "b3c9d6b2c3f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    cart_cols = {c["name"] for c in inspector.get_columns("carts")}
    if "shipping_method" not in cart_cols:
        op.add_column("carts", sa.Column("shipping_method", sa.Enum("INPOST_LOCKER", "COURIER", "PICKUP", name="shippingmethod"), nullable=True))
    if "shipping_cost_pln" not in cart_cols:
        op.add_column("carts", sa.Column("shipping_cost_pln", sa.Integer(), nullable=False, server_default="0"))

    order_cols = {c["name"] for c in inspector.get_columns("orders")}
    if "shipping_method" not in order_cols:
        op.add_column("orders", sa.Column("shipping_method", sa.Enum("INPOST_LOCKER", "COURIER", "PICKUP", name="shippingmethod"), nullable=False, server_default="PICKUP"))
    if "shipping_cost_pln" not in order_cols:
        op.add_column("orders", sa.Column("shipping_cost_pln", sa.Integer(), nullable=False, server_default="0"))
    if "shipping_country" not in order_cols:
        op.add_column("orders", sa.Column("shipping_country", sa.String(length=2), nullable=False, server_default="PL"))


def downgrade() -> None:
    op.drop_column("orders", "shipping_country")
    op.drop_column("orders", "shipping_cost_pln")
    op.drop_column("orders", "shipping_method")
    op.drop_column("carts", "shipping_cost_pln")
    op.drop_column("carts", "shipping_method")
