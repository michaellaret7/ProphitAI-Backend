"""change_num_shares_to_float

Revision ID: 3d3b530ba1f7
Revises: b1c2d3e4f5g6
Create Date: 2026-02-23 09:42:34.787022

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3d3b530ba1f7'
down_revision: Union[str, None] = 'b1c2d3e4f5g6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('portfolio_items', 'num_shares',
                    existing_type=sa.Integer(),
                    type_=sa.Float(),
                    existing_nullable=True)


def downgrade() -> None:
    op.alter_column('portfolio_items', 'num_shares',
                    existing_type=sa.Float(),
                    type_=sa.Integer(),
                    existing_nullable=True)
