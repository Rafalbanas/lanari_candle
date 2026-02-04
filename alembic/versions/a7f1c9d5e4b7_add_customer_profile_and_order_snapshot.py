"""add customer profile and buyer snapshot fields

Revision ID: a7f1c9d5e4b7
Revises: 8d3f8b6dfd3e, 9f4c0e3b6d7f
Create Date: 2026-02-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a7f1c9d5e4b7"
down_revision: Union[str, Sequence[str], None] = ("8d3f8b6dfd3e", "9f4c0e3b6d7f")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Customer profile (1:1 with user)
    op.create_table(
        "customer_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("first_name", sa.String(length=60), nullable=False),
        sa.Column("last_name", sa.String(length=80), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("address_line1", sa.String(length=120), nullable=False),
        sa.Column("address_line2", sa.String(length=120), nullable=True),
        sa.Column("city", sa.String(length=80), nullable=False),
        sa.Column("postal_code", sa.String(length=10), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=False, server_default="PL"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", name="uq_customer_profiles_user_id"),
    )

    # Snapshot fields on orders (idempotent if already present)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    order_cols = {c["name"] for c in inspector.get_columns("orders")}

    def add_column_if_missing(name: str, column: sa.Column):
        if name not in order_cols:
            op.add_column("orders", column)

    add_column_if_missing(
        "buyer_first_name",
        sa.Column("buyer_first_name", sa.String(length=60), nullable=False, server_default=""),
    )
    add_column_if_missing(
        "buyer_last_name",
        sa.Column("buyer_last_name", sa.String(length=80), nullable=False, server_default=""),
    )
    add_column_if_missing(
        "buyer_phone",
        sa.Column("buyer_phone", sa.String(length=20), nullable=False, server_default=""),
    )
    add_column_if_missing(
        "buyer_email",
        sa.Column("buyer_email", sa.String(length=255), nullable=False, server_default=""),
    )
    add_column_if_missing(
        "shipping_address_line1",
        sa.Column("shipping_address_line1", sa.String(length=120), nullable=False, server_default=""),
    )
    add_column_if_missing(
        "shipping_address_line2",
        sa.Column("shipping_address_line2", sa.String(length=120), nullable=True),
    )
    add_column_if_missing(
        "shipping_city",
        sa.Column("shipping_city", sa.String(length=80), nullable=False, server_default=""),
    )
    add_column_if_missing(
        "shipping_postal_code",
        sa.Column("shipping_postal_code", sa.String(length=10), nullable=False, server_default=""),
    )


def downgrade() -> None:
    for col in [
        "shipping_postal_code",
        "shipping_city",
        "shipping_address_line2",
        "shipping_address_line1",
        "buyer_email",
        "buyer_phone",
        "buyer_last_name",
        "buyer_first_name",
    ]:
        try:
            op.drop_column("orders", col)
        except Exception:
            pass

    op.drop_table("customer_profiles")
