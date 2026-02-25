"""add trade_proposals table

Revision ID: 046e9951b304
Revises: 3d3b530ba1f7
Create Date: 2026-02-25 11:25:20.113987

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '046e9951b304'
down_revision: Union[str, None] = '3d3b530ba1f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('trade_proposals',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('account_id', sa.String(), nullable=False),
    sa.Column('symbol', sa.String(), nullable=False),
    sa.Column('side', sa.String(), nullable=False),
    sa.Column('qty', sa.Float(), nullable=True),
    sa.Column('notional', sa.Float(), nullable=True),
    sa.Column('limit_price', sa.Float(), nullable=True),
    sa.Column('stop_price', sa.Float(), nullable=True),
    sa.Column('trail_price', sa.Float(), nullable=True),
    sa.Column('trail_percent', sa.Float(), nullable=True),
    sa.Column('take_profit', sa.Float(), nullable=True),
    sa.Column('stop_loss', sa.Float(), nullable=True),
    sa.Column('stop_loss_limit', sa.Float(), nullable=True),
    sa.Column('order_class', sa.String(), nullable=True),
    sa.Column('time_in_force', sa.String(), nullable=False),
    sa.Column('agent_reasoning', sa.Text(), nullable=True),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('alpaca_order_id', sa.String(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('executed_at', sa.DateTime(), nullable=True),
    sa.Column('rejected_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trade_proposals_status'), 'trade_proposals', ['status'], unique=False)
    op.create_index(op.f('ix_trade_proposals_user_id'), 'trade_proposals', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_trade_proposals_user_id'), table_name='trade_proposals')
    op.drop_index(op.f('ix_trade_proposals_status'), table_name='trade_proposals')
    op.drop_table('trade_proposals')
