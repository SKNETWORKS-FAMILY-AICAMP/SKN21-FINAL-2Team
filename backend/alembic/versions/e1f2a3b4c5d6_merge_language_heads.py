"""merge language heads

Revision ID: e1f2a3b4c5d6
Revises: bef46e9cdb71, db2cc1c6cc2d
Create Date: 2026-03-20 00:00:00.000000

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = ('bef46e9cdb71', 'db2cc1c6cc2d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
