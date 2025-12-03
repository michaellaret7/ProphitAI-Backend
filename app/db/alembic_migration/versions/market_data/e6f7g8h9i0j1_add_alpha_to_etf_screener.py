"""Add alpha column to etf_screener table

Revision ID: e6f7g8h9i0j1
Revises: d5e6f7g8h9i0
Create Date: 2025-12-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6f7g8h9i0j1'
down_revision: Union[str, None] = 'd5e6f7g8h9i0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'etf_screener',
        sa.Column('alpha', sa.Float(), nullable=True),
        schema='screener_data'
    )


def downgrade() -> None:
    op.drop_column('etf_screener', 'alpha', schema='screener_data')
