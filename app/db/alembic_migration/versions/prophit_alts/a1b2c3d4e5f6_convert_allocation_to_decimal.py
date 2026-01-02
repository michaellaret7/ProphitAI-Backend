"""Convert final_positions.portfolio_allocation from percentage (0-100) to decimal (0-1)

Revision ID: a1b2c3d4e5f6
Revises: None
Create Date: 2026-01-02

Standardizes allocation format for prophit_alts database:
- Before: 25.0 means 25%
- After: 0.25 means 25%

Note: initial_positions.conviction is already in decimal format (0-1), no conversion needed.
Also adds CHECK constraint to enforce values between 0 and 1.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert portfolio_allocation values from percentage (0-100) to decimal (0-1)
    # Only convert values > 1 to avoid double-converting already-decimal values
    op.execute("""
        UPDATE prophit_alts_funds.final_positions
        SET portfolio_allocation = portfolio_allocation / 100.0
        WHERE portfolio_allocation > 1
    """)

    # Add CHECK constraint to enforce decimal format (0-1)
    op.create_check_constraint(
        'ck_final_positions_allocation_decimal',
        'final_positions',
        'portfolio_allocation >= 0 AND portfolio_allocation <= 1',
        schema='prophit_alts_funds'
    )

    # Add CHECK constraint for conviction in initial_positions (already decimal, just enforce)
    op.create_check_constraint(
        'ck_initial_positions_conviction_decimal',
        'initial_positions',
        'conviction >= 0 AND conviction <= 1',
        schema='prophit_alts_funds'
    )


def downgrade() -> None:
    # Remove CHECK constraints
    op.drop_constraint(
        'ck_initial_positions_conviction_decimal',
        'initial_positions',
        type_='check',
        schema='prophit_alts_funds'
    )
    op.drop_constraint(
        'ck_final_positions_allocation_decimal',
        'final_positions',
        type_='check',
        schema='prophit_alts_funds'
    )

    # Convert portfolio_allocation values back from decimal (0-1) to percentage (0-100)
    op.execute("""
        UPDATE prophit_alts_funds.final_positions
        SET portfolio_allocation = portfolio_allocation * 100.0
        WHERE portfolio_allocation <= 1
    """)
