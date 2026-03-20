"""add language

Revision ID: bef46e9cdb71
Revises: c7d8e9f0a1b2
Create Date: 2026-03-19 06:58:29.886570

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'bef46e9cdb71'
down_revision: Union[str, Sequence[str], None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # country 테이블은 c7d8e9f0a1b2에서 이미 삭제됨 - 재생성 불필요

    # 인덱스가 이미 존재할 수 있으므로 조건부 생성
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    hot_places_indexes = [idx['name'] for idx in inspector.get_indexes('hot_places')]
    if 'ix_hot_places_id' not in hot_places_indexes:
        op.create_index(op.f('ix_hot_places_id'), 'hot_places', ['id'], unique=False)

    op.alter_column('reservation_list', 'date',
               existing_type=mysql.DATETIME(),
               type_=sa.Date(),
               existing_nullable=True)

    reservation_indexes = [idx['name'] for idx in inspector.get_indexes('reservation_list')]
    if 'ix_reservation_list_id' not in reservation_indexes:
        op.create_index(op.f('ix_reservation_list_id'), 'reservation_list', ['id'], unique=False)

    users_columns = [col['name'] for col in inspector.get_columns('users')]
    if 'language' not in users_columns:
        op.add_column('users', sa.Column('language', sa.Enum('en', 'ko', 'ja', 'zh', name='languagetype'), nullable=False, comment='UI Language Preference'))
    op.alter_column('users', 'profile_picture',
               existing_type=mysql.VARCHAR(length=255),
               type_=sa.String(length=1000),
               existing_nullable=True)
    op.alter_column('users', 'country_code',
               existing_type=mysql.VARCHAR(length=255),
               type_=sa.String(length=10),
               comment='ISO Country Code',
               existing_nullable=True)
    op.alter_column('users', 'is_join',
               existing_type=mysql.TINYINT(display_width=1),
               nullable=True,
               existing_server_default=sa.text("'0'"))
    op.alter_column('users', 'is_prefer',
               existing_type=mysql.TINYINT(display_width=1),
               nullable=True,
               existing_server_default=sa.text("'0'"))
    op.alter_column('users', 'created_at',
               existing_type=mysql.TIMESTAMP(),
               type_=sa.DateTime(),
               existing_nullable=True,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    op.alter_column('users', 'updated_at',
               existing_type=mysql.TIMESTAMP(),
               type_=sa.DateTime(),
               existing_nullable=True,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))

    users_indexes = [idx['name'] for idx in inspector.get_indexes('users')]
    if 'ix_users_id' not in users_indexes:
        op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    users_indexes = [idx['name'] for idx in inspector.get_indexes('users')]
    if 'ix_users_id' in users_indexes:
        op.drop_index(op.f('ix_users_id'), table_name='users')

    op.alter_column('users', 'updated_at',
               existing_type=sa.DateTime(),
               type_=mysql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    op.alter_column('users', 'created_at',
               existing_type=sa.DateTime(),
               type_=mysql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    op.alter_column('users', 'is_prefer',
               existing_type=mysql.TINYINT(display_width=1),
               nullable=False,
               existing_server_default=sa.text("'0'"))
    op.alter_column('users', 'is_join',
               existing_type=mysql.TINYINT(display_width=1),
               nullable=False,
               existing_server_default=sa.text("'0'"))
    op.alter_column('users', 'country_code',
               existing_type=sa.String(length=10),
               type_=mysql.VARCHAR(length=255),
               comment=None,
               existing_comment='ISO Country Code',
               existing_nullable=True)
    op.alter_column('users', 'profile_picture',
               existing_type=sa.String(length=1000),
               type_=mysql.VARCHAR(length=255),
               existing_nullable=True)
    op.drop_column('users', 'language')

    reservation_indexes = [idx['name'] for idx in inspector.get_indexes('reservation_list')]
    if 'ix_reservation_list_id' in reservation_indexes:
        op.drop_index(op.f('ix_reservation_list_id'), table_name='reservation_list')

    op.alter_column('reservation_list', 'date',
               existing_type=sa.Date(),
               type_=mysql.DATETIME(),
               existing_nullable=True)

    hot_places_indexes = [idx['name'] for idx in inspector.get_indexes('hot_places')]
    if 'ix_hot_places_id' in hot_places_indexes:
        op.drop_index(op.f('ix_hot_places_id'), table_name='hot_places')
