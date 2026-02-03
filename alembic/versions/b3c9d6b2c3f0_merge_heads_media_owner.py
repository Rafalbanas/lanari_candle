"""Merge heads after media owner nullable

Revision ID: b3c9d6b2c3f0
Revises: 0b2fad2e3715, 9f4c0e3b6d7f
Create Date: 2026-02-03
"""

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

# revision identifiers, used by Alembic.
revision = "b3c9d6b2c3f0"
down_revision = ("0b2fad2e3715", "9f4c0e3b6d7f")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
