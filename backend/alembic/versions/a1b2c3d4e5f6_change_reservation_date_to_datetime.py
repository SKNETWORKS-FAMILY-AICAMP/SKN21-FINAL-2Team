"""change reservation date to datetime

Revision ID: a1b2c3d4e5f6
Revises: 5b79460e27ed
Create Date: 2026-03-15 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '5b79460e27ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """reservation_list.date 컬럼을 Date → DateTime 으로 변경 (시간까지 저장)"""
    op.alter_column(
        'reservation_list',
        'date',
        existing_type=sa.Date(),
        type_=sa.DateTime(),
        existing_nullable=True,
    )


def downgrade() -> None:
    """롤백: DateTime → Date (시간 정보는 손실됨)"""
    op.alter_column(
        'reservation_list',
        'date',
        existing_type=sa.DateTime(),
        type_=sa.Date(),
        existing_nullable=True,
    )
