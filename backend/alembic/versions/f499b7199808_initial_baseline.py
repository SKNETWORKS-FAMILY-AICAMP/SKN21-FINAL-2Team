"""initial_baseline

Revision ID: f499b7199808
Revises: 
Create Date: 2026-03-12 01:18:30.661328

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f499b7199808'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    이 baseline revision은 기존 RDS에 이미 테이블이 존재하는 상태에서
    Alembic을 최초 도입할 때 사용합니다.
    DDL을 실행하지 않고 버전만 기록합니다.

    기존 RDS에 적용 방법:
        alembic stamp f499b7199808
    이후 스키마 변경 시:
        alembic revision --autogenerate -m "변경 내용"
        alembic upgrade head
    """
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
