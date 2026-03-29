"""Change intraday prices volume to bigint

Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
Create Date: 2026-02-20

Intraday Price.volume was Integer (max 2.1B) while DailyPrices already
uses BigInteger. High-volume tickers can exceed the Integer limit.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'i0j1k2l3m4n5'
down_revision: Union[str, None] = 'h9i0j1k2l3m4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('prices', 'volume',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=True,
               schema='price_data')


def downgrade() -> None:
    op.alter_column('prices', 'volume',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=True,
               schema='price_data')
