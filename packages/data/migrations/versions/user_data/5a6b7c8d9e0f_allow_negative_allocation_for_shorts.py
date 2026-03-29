"""Allow negative allocation for short positions

Revision ID: 5a6b7c8d9e0f
Revises: 4e24b89a02cc
Create Date: 2026-02-20

The ck_portfolio_items_allocation_decimal constraint enforced allocation >= 0,
but portfolios with short positions have negative num_shares and therefore
negative allocation values (e.g. HYG at -0.05 for a short).
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '5a6b7c8d9e0f'
down_revision: Union[str, None] = '4e24b89a02cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('ck_portfolio_items_allocation_decimal', 'portfolio_items', type_='check')
    op.create_check_constraint(
        'ck_portfolio_items_allocation_decimal',
        'portfolio_items',
        'allocation >= -1 AND allocation <= 1'
    )


def downgrade() -> None:
    op.drop_constraint('ck_portfolio_items_allocation_decimal', 'portfolio_items', type_='check')
    op.create_check_constraint(
        'ck_portfolio_items_allocation_decimal',
        'portfolio_items',
        'allocation >= 0 AND allocation <= 1'
    )
