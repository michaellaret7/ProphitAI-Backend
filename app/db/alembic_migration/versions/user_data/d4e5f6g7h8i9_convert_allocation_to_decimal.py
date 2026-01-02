"""Convert portfolio_items.allocation from percentage (0-100) to decimal (0-1)

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-01-02

Standardizes allocation format across the codebase:
- Before: 25.0 means 25%
- After: 0.25 means 25%

Also adds CHECK constraint to enforce values between 0 and 1.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6g7h8i9'
down_revision: Union[str, None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Cap any values > 100 to 100 (invalid allocations > 100%)
    op.execute("""
        UPDATE portfolio_items
        SET allocation = 100.0
        WHERE allocation > 100
    """)

    # Step 2: Convert allocation values from percentage (0-100) to decimal (0-1)
    # Only convert values > 1 to avoid double-converting already-decimal values
    op.execute("""
        UPDATE portfolio_items
        SET allocation = allocation / 100.0
        WHERE allocation > 1
    """)

    # Step 3: Cap any negative values to 0
    op.execute("""
        UPDATE portfolio_items
        SET allocation = 0
        WHERE allocation < 0
    """)

    # Step 4: Add CHECK constraint to enforce decimal format (0-1)
    op.create_check_constraint(
        'ck_portfolio_items_allocation_decimal',
        'portfolio_items',
        'allocation >= 0 AND allocation <= 1'
    )


def downgrade() -> None:
    # Remove CHECK constraint
    op.drop_constraint('ck_portfolio_items_allocation_decimal', 'portfolio_items', type_='check')

    # Convert allocation values back from decimal (0-1) to percentage (0-100)
    # Only convert values <= 1 to avoid double-converting
    op.execute("""
        UPDATE portfolio_items
        SET allocation = allocation * 100.0
        WHERE allocation <= 1
    """)
