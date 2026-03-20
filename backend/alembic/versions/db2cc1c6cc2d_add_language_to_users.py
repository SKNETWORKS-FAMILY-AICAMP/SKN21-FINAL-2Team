"""add language to users

Revision ID: db2cc1c6cc2d
Revises: 896f411016d2
Create Date: 2026-03-18 18:28:00.413776

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'db2cc1c6cc2d'
down_revision: Union[str, Sequence[str], None] = '896f411016d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    language_enum = sa.Enum('en', 'ko', 'ja', 'zh', name='languagetype')
    op.add_column(
        'users',
        sa.Column(
            'language',
            language_enum,
            nullable=False,
            server_default=sa.text("'en'"),
            comment='UI Language Preference',
        ),
    )
    op.alter_column('users', 'language', server_default=None, existing_type=language_enum)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'language')
