"""merge multiple heads

Revision ID: dfbedd9b2448
Revises: 4c19bb5312a8, b5c6d7e8f9a0
Create Date: 2026-03-18 06:23:02.414290

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dfbedd9b2448'
down_revision: Union[str, Sequence[str], None] = ('4c19bb5312a8', 'b5c6d7e8f9a0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
