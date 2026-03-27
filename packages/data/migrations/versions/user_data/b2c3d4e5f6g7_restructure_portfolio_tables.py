"""Restructure portfolio tables: create portfolios parent table and portfolio_items child table

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-12-30

This migration restructures the portfolio data model:
- Old: Single 'portfolios' table with denormalized data (each row = one position)
- New: Parent 'portfolios' table (metadata) + child 'portfolio_items' table (positions)

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Drop indexes that may conflict (using raw SQL for IF EXISTS support)
    # In PostgreSQL, index names are unique within a schema, so we need to drop old indexes
    # before creating new ones with the same names
    op.execute("DROP INDEX IF EXISTS ix_portfolios_user_id")
    op.execute("DROP INDEX IF EXISTS ix_portfolios_name")
    op.execute("DROP INDEX IF EXISTS ix_portfolios_is_current")
    op.execute("DROP INDEX IF EXISTS ix_portfolios_is_discretionary")
    op.execute("DROP INDEX IF EXISTS ix_portfolios_portfolio_id")
    op.execute("DROP INDEX IF EXISTS ix_portfolios_sector")
    op.execute("DROP INDEX IF EXISTS ix_portfolios_industry")
    op.execute("DROP INDEX IF EXISTS ix_portfolios_company_id")

    # Step 2: Handle partial migration state - if portfolios_old exists, drop the new portfolios table
    # and restore the old one before re-running the migration
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'portfolios_old') THEN
                DROP TABLE IF EXISTS portfolios CASCADE;
                ALTER TABLE portfolios_old RENAME TO portfolios;
            END IF;
        END $$;
    """)

    # Step 3: Rename old portfolios table to temp name
    op.rename_table('portfolios', 'portfolios_old')

    # Step 4: Create new portfolios parent table
    op.create_table(
        'portfolios',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=True, default=False),
        sa.Column('is_discretionary', sa.Boolean(), nullable=True, default=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_portfolios_user_id', 'portfolios', ['user_id'], unique=False)
    op.create_index('ix_portfolios_name', 'portfolios', ['name'], unique=False)
    op.create_index('ix_portfolios_is_current', 'portfolios', ['is_current'], unique=False)
    op.create_index('ix_portfolios_is_discretionary', 'portfolios', ['is_discretionary'], unique=False)

    # Step 5: Create portfolio_items child table
    op.create_table(
        'portfolio_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('portfolio_id', UUID(as_uuid=True), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('allocation', sa.Float(), nullable=True),
        sa.Column('supporting_metrics', JSONB(), nullable=True),
        sa.Column('reason_for_rec', sa.Text(), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_portfolio_items_portfolio_id', 'portfolio_items', ['portfolio_id'], unique=False)

    # Step 6: Migrate data from old table to new tables
    # First, insert unique portfolios into the new portfolios table
    # Using portfolio_id from old table as the new id to maintain references
    op.execute("""
        INSERT INTO portfolios (id, user_id, name, created_date, updated_date, is_current, is_discretionary)
        SELECT DISTINCT ON (portfolio_id)
            portfolio_id as id,
            user_id,
            name,
            created_date,
            updated_date,
            is_current,
            is_discretionary
        FROM portfolios_old
        WHERE user_id IS NOT NULL
        ORDER BY portfolio_id, created_date DESC
    """)

    # Then, insert all positions into portfolio_items
    op.execute("""
        INSERT INTO portfolio_items (portfolio_id, ticker, allocation, supporting_metrics, reason_for_rec, created_date, updated_date)
        SELECT
            portfolio_id,
            ticker,
            allocation,
            supporting_metrics,
            reason_for_rec,
            created_date,
            updated_date
        FROM portfolios_old
        WHERE portfolio_id IN (SELECT id FROM portfolios)
    """)

    # Step 7: Drop old table
    op.drop_table('portfolios_old')


def downgrade() -> None:
    # Step 1: Rename new portfolios to temp name
    op.rename_table('portfolios', 'portfolios_new')

    # Step 2: Recreate old portfolios table structure
    op.create_table(
        'portfolios',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('portfolio_id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('sector', sa.String(), nullable=True),
        sa.Column('industry', sa.String(), nullable=True),
        sa.Column('sub_industry', sa.String(), nullable=True),
        sa.Column('allocation', sa.Float(), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_discretionary', sa.Boolean(), nullable=True, default=False),
        sa.Column('supporting_metrics', JSONB(), nullable=True),
        sa.Column('reason_for_rec', sa.Text(), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.Column('company_id', UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_portfolios_portfolio_id', 'portfolios', ['portfolio_id'], unique=False)
    op.create_index('ix_portfolios_name', 'portfolios', ['name'], unique=False)
    op.create_index('ix_portfolios_sector', 'portfolios', ['sector'], unique=False)
    op.create_index('ix_portfolios_industry', 'portfolios', ['industry'], unique=False)
    op.create_index('ix_portfolios_is_current', 'portfolios', ['is_current'], unique=False)
    op.create_index('ix_portfolios_is_discretionary', 'portfolios', ['is_discretionary'], unique=False)
    op.create_index('ix_portfolios_company_id', 'portfolios', ['company_id'], unique=False)
    op.create_index('ix_portfolios_user_id', 'portfolios', ['user_id'], unique=False)

    # Step 3: Migrate data back to old structure
    op.execute("""
        INSERT INTO portfolios (portfolio_id, name, ticker, allocation, is_current, is_discretionary, supporting_metrics, reason_for_rec, created_date, updated_date, user_id)
        SELECT
            p.id as portfolio_id,
            p.name,
            pi.ticker,
            pi.allocation,
            p.is_current,
            p.is_discretionary,
            pi.supporting_metrics,
            pi.reason_for_rec,
            pi.created_date,
            pi.updated_date,
            p.user_id
        FROM portfolios_new p
        JOIN portfolio_items pi ON p.id = pi.portfolio_id
    """)

    # Step 4: Drop new tables
    op.drop_index('ix_portfolio_items_portfolio_id', table_name='portfolio_items')
    op.drop_table('portfolio_items')
    op.drop_index('ix_portfolios_user_id', table_name='portfolios_new')
    op.drop_index('ix_portfolios_name', table_name='portfolios_new')
    op.drop_index('ix_portfolios_is_current', table_name='portfolios_new')
    op.drop_index('ix_portfolios_is_discretionary', table_name='portfolios_new')
    op.drop_table('portfolios_new')
