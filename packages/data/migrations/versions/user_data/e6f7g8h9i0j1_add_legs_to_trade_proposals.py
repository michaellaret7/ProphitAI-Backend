"""add_legs_to_trade_proposals

Revision ID: e6f7g8h9i0j1
Revises: d5e6f7g8h9i0
Create Date: 2026-03-05

Adds nullable Text column 'legs' to trade_proposals for storing
JSON-serialized multi-leg options order data.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e6f7g8h9i0j1'
down_revision: Union[str, None] = 'd5e6f7g8h9i0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'trade_proposals',
        sa.Column('legs', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('trade_proposals', 'legs')
