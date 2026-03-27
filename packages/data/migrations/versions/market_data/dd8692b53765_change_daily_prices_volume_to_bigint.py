"""change daily_prices volume to bigint

Revision ID: dd8692b53765
Revises: 223048402776
Create Date: 2025-11-27 17:30:52.378467

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dd8692b53765'
down_revision: Union[str, None] = '223048402776'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('daily_prices', 'volume',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=True,
               schema='price_data')


def downgrade() -> None:
    op.alter_column('daily_prices', 'volume',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=True,
               schema='price_data')
