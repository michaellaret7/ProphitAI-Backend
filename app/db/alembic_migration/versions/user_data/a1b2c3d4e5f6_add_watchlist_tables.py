"""Add watchlist and watchlist_items tables

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2025-12-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create watchlists table
    op.create_table(
        'watchlists',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('creation_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_watchlists_user_id', 'watchlists', ['user_id'], unique=False)

    # Create watchlist_items table with composite primary key
    op.create_table(
        'watchlist_items',
        sa.Column('watchlist_id', UUID(as_uuid=True), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('price_on_inception', sa.Float(), nullable=True),
        sa.Column('added_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['watchlist_id'], ['watchlists.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('watchlist_id', 'ticker')
    )
    op.create_index('ix_watchlist_items_watchlist_id', 'watchlist_items', ['watchlist_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_watchlist_items_watchlist_id', table_name='watchlist_items')
    op.drop_table('watchlist_items')
    op.drop_index('ix_watchlists_user_id', table_name='watchlists')
    op.drop_table('watchlists')
