"""drop country table and FK constraint

Revision ID: c7d8e9f0a1b2
Revises: 896f411016d2
Create Date: 2026-03-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, Sequence[str], None] = '896f411016d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. FK 제약 조건 제거 (users.country_code → country.code) 먼저 수행
    try:
        op.drop_constraint('users_ibfk_1', 'users', type_='foreignkey')
    except Exception:
        pass

    # 2. 기존 언어코드(소문자) → ISO 국가코드(대문자) 매핑 보정
    lang_to_country = {
        "ko": "KR", "en": "US", "ja": "JP", "zh": "CN",
        "th": "TH", "vi": "VN", "id": "ID", "ms": "MY",
        "de": "DE", "fr": "FR", "es": "ES", "it": "IT",
        "pt": "BR",
    }
    for lang_code, country_code in lang_to_country.items():
        op.execute(f"UPDATE users SET country_code = '{country_code}' WHERE country_code = '{lang_code}'")
        op.execute(f"UPDATE users SET country_code = '{country_code}' WHERE country_code = '{lang_code.upper()}'")

    # 나머지 소문자 코드는 대문자로 변환
    op.execute("UPDATE users SET country_code = UPPER(country_code) WHERE country_code IS NOT NULL AND country_code != UPPER(country_code)")

    # 3. country 테이블 삭제
    op.drop_table('country')


def downgrade() -> None:
    # country 테이블 재생성
    op.create_table('country',
        sa.Column('code', sa.String(length=10), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('code'),
    )
    # FK 복원
    op.create_foreign_key('users_ibfk_1', 'users', 'country', ['country_code'], ['code'])
