"""add location to chat_messages

Revision ID: 000000000002
Revises: 000000000001
Create Date: 2026-03-24

chat_messages 테이블에 location(주소 문자열) 컬럼 추가.
geocoder_node가 위도/경도를 역지오코딩한 결과를 저장한다.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '000000000002'
down_revision: Union[str, Sequence[str], None] = '000000000001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    existing_columns = {col['name'] for col in inspector.get_columns('chat_messages')}
    if 'location' not in existing_columns:
        op.add_column(
            'chat_messages',
            sa.Column('location', sa.String(255), nullable=True),
        )


def downgrade() -> None:
    op.drop_column('chat_messages', 'location')
