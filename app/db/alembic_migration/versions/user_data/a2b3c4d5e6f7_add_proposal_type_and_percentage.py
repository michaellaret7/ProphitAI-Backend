"""add proposal_type and percentage to trade_proposals

Revision ID: a2b3c4d5e6f7
Revises: 046e9951b304
Create Date: 2026-02-27 12:00:00.000000

Adds a proposal_type discriminator column ('trade' or 'close_position') and
a percentage column for partial position closes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = '046e9951b304'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('trade_proposals', sa.Column('proposal_type', sa.String(), nullable=False, server_default='trade'))
    op.add_column('trade_proposals', sa.Column('percentage', sa.Float(), nullable=True))
    op.create_index(op.f('ix_trade_proposals_proposal_type'), 'trade_proposals', ['proposal_type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_trade_proposals_proposal_type'), table_name='trade_proposals')
    op.drop_column('trade_proposals', 'percentage')
    op.drop_column('trade_proposals', 'proposal_type')
