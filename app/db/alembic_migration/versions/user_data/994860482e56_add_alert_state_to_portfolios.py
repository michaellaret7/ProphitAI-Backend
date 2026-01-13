"""add_alert_state_to_portfolios

Revision ID: 994860482e56
Revises: c3abc03c5d8a
Create Date: 2026-01-12 19:02:42.918457

Adds alert_state JSONB column to portfolios table for tracking last sent
alert state per alert type (drift, drawdown, correlation). Used to prevent
duplicate/repetitive notifications when the same risk conditions persist.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '994860482e56'
down_revision: Union[str, None] = 'c3abc03c5d8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('portfolios', sa.Column('alert_state', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('portfolios', 'alert_state')
