"""Rename subindustry to sub_industry in etf_screener table

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
Create Date: 2025-12-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h9i0j1k2l3m4'
down_revision: Union[str, None] = 'g8h9i0j1k2l3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old index
    op.drop_index(
        op.f('ix_screener_data_etf_screener_subindustry'),
        table_name='etf_screener',
        schema='screener_data'
    )

    # Rename column
    op.alter_column(
        'etf_screener',
        'subindustry',
        new_column_name='sub_industry',
        schema='screener_data'
    )

    # Create new index with correct name
    op.create_index(
        op.f('ix_screener_data_etf_screener_sub_industry'),
        'etf_screener',
        ['sub_industry'],
        unique=False,
        schema='screener_data'
    )


def downgrade() -> None:
    # Drop new index
    op.drop_index(
        op.f('ix_screener_data_etf_screener_sub_industry'),
        table_name='etf_screener',
        schema='screener_data'
    )

    # Rename column back
    op.alter_column(
        'etf_screener',
        'sub_industry',
        new_column_name='subindustry',
        schema='screener_data'
    )

    # Recreate old index
    op.create_index(
        op.f('ix_screener_data_etf_screener_subindustry'),
        'etf_screener',
        ['subindustry'],
        unique=False,
        schema='screener_data'
    )