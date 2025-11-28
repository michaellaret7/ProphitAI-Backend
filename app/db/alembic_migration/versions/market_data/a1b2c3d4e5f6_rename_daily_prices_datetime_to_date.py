"""rename daily_prices datetime to date

Revision ID: a1b2c3d4e5f6
Revises: dd8692b53765
Create Date: 2025-11-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'dd8692b53765'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('daily_prices', 'datetime',
                    new_column_name='date',
                    existing_type=sa.DateTime(),
                    schema='price_data')


def downgrade() -> None:
    op.alter_column('daily_prices', 'date',
                    new_column_name='datetime',
                    existing_type=sa.DateTime(),
                    schema='price_data')
