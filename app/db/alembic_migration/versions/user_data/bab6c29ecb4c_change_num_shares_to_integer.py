"""change_num_shares_to_integer

Revision ID: bab6c29ecb4c
Revises: a753e28f2eb2
Create Date: 2026-01-06 10:16:18.023325

Changes num_shares column in portfolio_items from Float to Integer.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bab6c29ecb4c'
down_revision: Union[str, None] = 'a753e28f2eb2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('portfolio_items', 'num_shares',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Integer(),
               existing_nullable=True)


def downgrade() -> None:
    op.alter_column('portfolio_items', 'num_shares',
               existing_type=sa.Integer(),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
