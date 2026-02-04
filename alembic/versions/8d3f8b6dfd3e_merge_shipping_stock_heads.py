"""merge shipping and stock heads

Revision ID: 8d3f8b6dfd3e
Revises: 6d2f8d1a9c44, 7a6bde5fb3f1
Create Date: 2026-02-03
"""
from typing import Sequence, Union

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "8d3f8b6dfd3e"
down_revision: Union[str, Sequence[str], None] = ("6d2f8d1a9c44", "7a6bde5fb3f1")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
