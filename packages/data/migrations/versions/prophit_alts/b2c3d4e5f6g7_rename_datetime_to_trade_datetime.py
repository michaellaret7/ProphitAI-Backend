"""Rename trades.datetime column to trade_datetime

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-02

Renames the 'datetime' column to 'trade_datetime' in the trades table
to avoid naming conflict with Python's datetime module.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename 'datetime' column to 'trade_datetime' in trades table
    op.alter_column(
        'trades',
        'datetime',
        new_column_name='trade_datetime',
        schema='prophit_alts_funds'
    )


def downgrade() -> None:
    # Rename 'trade_datetime' column back to 'datetime' in trades table
    op.alter_column(
        'trades',
        'trade_datetime',
        new_column_name='datetime',
        schema='prophit_alts_funds'
    )
