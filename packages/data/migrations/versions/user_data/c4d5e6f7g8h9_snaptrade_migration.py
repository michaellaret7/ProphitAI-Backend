"""snaptrade_migration

Revision ID: c4d5e6f7g8h9
Revises: a2b3c4d5e6f7
Create Date: 2026-03-04

Replaces Alpaca broker columns with SnapTrade credentials on User model.
Renames alpaca_order_id to broker_order_id on TradeProposal model.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4d5e6f7g8h9'
down_revision: Union[str, None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Users table: add SnapTrade columns ---
    op.add_column('users', sa.Column('snaptrade_user_id', sa.String(), nullable=True))
    op.add_column('users', sa.Column('snaptrade_user_secret', sa.String(), nullable=True))
    op.add_column('users', sa.Column('snaptrade_account_id', sa.String(), nullable=True))

    op.create_unique_constraint('uq_users_snaptrade_user_id', 'users', ['snaptrade_user_id'])
    op.create_index('ix_users_snaptrade_user_id', 'users', ['snaptrade_user_id'])
    op.create_index('ix_users_snaptrade_account_id', 'users', ['snaptrade_account_id'])

    # Copy broker_account_id data into snaptrade_account_id
    op.execute("UPDATE users SET snaptrade_account_id = broker_account_id WHERE broker_account_id IS NOT NULL")

    # Set default broker to 'snaptrade'
    op.alter_column('users', 'broker', server_default='snaptrade')

    # Drop old broker_account_id column
    op.drop_index('ix_users_broker_account_id', table_name='users')
    op.drop_constraint('uq_users_broker_account_id', 'users', type_='unique')
    op.drop_column('users', 'broker_account_id')

    # --- Trade proposals table: rename alpaca_order_id -> broker_order_id ---
    op.alter_column('trade_proposals', 'alpaca_order_id', new_column_name='broker_order_id')


def downgrade() -> None:
    # --- Trade proposals table: rename back ---
    op.alter_column('trade_proposals', 'broker_order_id', new_column_name='alpaca_order_id')

    # --- Users table: restore broker_account_id ---
    op.add_column('users', sa.Column('broker_account_id', sa.String(), nullable=True))

    # Copy snaptrade_account_id back to broker_account_id
    op.execute("UPDATE users SET broker_account_id = snaptrade_account_id WHERE snaptrade_account_id IS NOT NULL")

    op.create_unique_constraint('uq_users_broker_account_id', 'users', ['broker_account_id'])
    op.create_index('ix_users_broker_account_id', 'users', ['broker_account_id'])

    # Remove server default
    op.alter_column('users', 'broker', server_default=None)

    # Drop SnapTrade columns
    op.drop_index('ix_users_snaptrade_account_id', table_name='users')
    op.drop_index('ix_users_snaptrade_user_id', table_name='users')
    op.drop_constraint('uq_users_snaptrade_user_id', 'users', type_='unique')
    op.drop_column('users', 'snaptrade_account_id')
    op.drop_column('users', 'snaptrade_user_secret')
    op.drop_column('users', 'snaptrade_user_id')
