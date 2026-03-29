"""snaptrade_trade_proposal_cleanup

Revision ID: d5e6f7g8h9i0
Revises: c4d5e6f7g8h9
Create Date: 2026-03-04

Drops Alpaca-specific columns from trade_proposals (trail_price, trail_percent,
take_profit, stop_loss, stop_loss_limit, order_class) and adds order_type column
for SnapTrade order types (Market, Limit, Stop, StopLimit).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd5e6f7g8h9i0'
down_revision: Union[str, None] = 'c4d5e6f7g8h9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add order_type column with default 'Market'
    op.add_column(
        'trade_proposals',
        sa.Column('order_type', sa.String(), nullable=True, server_default='Market'),
    )

    # Reason: Backfill order_type for existing rows based on price params
    op.execute("""
        UPDATE trade_proposals SET order_type = CASE
            WHEN stop_price IS NOT NULL AND limit_price IS NOT NULL THEN 'StopLimit'
            WHEN stop_price IS NOT NULL THEN 'Stop'
            WHEN limit_price IS NOT NULL THEN 'Limit'
            ELSE 'Market'
        END
    """)

    # Update time_in_force values from Alpaca format to SnapTrade format
    op.execute("UPDATE trade_proposals SET time_in_force = 'Day' WHERE time_in_force = 'day'")
    op.execute("UPDATE trade_proposals SET time_in_force = 'GTC' WHERE time_in_force = 'gtc'")
    op.execute("UPDATE trade_proposals SET time_in_force = 'FOK' WHERE time_in_force = 'fok'")
    op.execute("UPDATE trade_proposals SET time_in_force = 'IOC' WHERE time_in_force = 'ioc'")

    # Drop Alpaca-specific columns
    op.drop_column('trade_proposals', 'trail_price')
    op.drop_column('trade_proposals', 'trail_percent')
    op.drop_column('trade_proposals', 'take_profit')
    op.drop_column('trade_proposals', 'stop_loss')
    op.drop_column('trade_proposals', 'stop_loss_limit')
    op.drop_column('trade_proposals', 'order_class')


def downgrade() -> None:
    # Re-add Alpaca-specific columns
    op.add_column('trade_proposals', sa.Column('order_class', sa.String(), nullable=True))
    op.add_column('trade_proposals', sa.Column('stop_loss_limit', sa.Float(), nullable=True))
    op.add_column('trade_proposals', sa.Column('stop_loss', sa.Float(), nullable=True))
    op.add_column('trade_proposals', sa.Column('take_profit', sa.Float(), nullable=True))
    op.add_column('trade_proposals', sa.Column('trail_percent', sa.Float(), nullable=True))
    op.add_column('trade_proposals', sa.Column('trail_price', sa.Float(), nullable=True))

    # Revert time_in_force values
    op.execute("UPDATE trade_proposals SET time_in_force = 'day' WHERE time_in_force = 'Day'")
    op.execute("UPDATE trade_proposals SET time_in_force = 'gtc' WHERE time_in_force = 'GTC'")
    op.execute("UPDATE trade_proposals SET time_in_force = 'fok' WHERE time_in_force = 'FOK'")
    op.execute("UPDATE trade_proposals SET time_in_force = 'ioc' WHERE time_in_force = 'IOC'")

    # Drop order_type column
    op.drop_column('trade_proposals', 'order_type')
