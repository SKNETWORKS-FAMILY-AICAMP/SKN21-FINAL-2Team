"""clean_baseline - 전체 스키마를 단일 파일로 관리

Revision ID: 000000000001
Revises:
Create Date: 2026-03-20

모든 테이블을 IF NOT EXISTS 방식으로 생성합니다.
- 신규 환경: 테이블 전체 생성
- 기존 RDS:  alembic stamp 000000000001 후 upgrade head (no-op)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = '000000000001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = set(inspector.get_table_names())

    # 1. users (FK 참조 없음 → 가장 먼저 생성)
    if 'users' not in existing:
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('email', sa.String(255), nullable=False),
            sa.Column('name', sa.String(255), nullable=True),
            sa.Column('nickname', sa.String(255), nullable=True),
            sa.Column('profile_picture', sa.String(1000), nullable=True),
            sa.Column('gender', sa.Enum('male', 'female', 'other', name='gendertype'), nullable=True),
            sa.Column('social_provider', sa.String(255), nullable=True),
            sa.Column('social_id', sa.String(255), nullable=True),
            sa.Column('social_access_token', sa.String(255), nullable=True),
            sa.Column('social_refresh_token', sa.String(255), nullable=True),
            sa.Column('plan_prefer', sa.String(255), nullable=True),
            sa.Column('vibe_prefer', sa.String(255), nullable=True),
            sa.Column('places_prefer', sa.String(255), nullable=True),
            sa.Column('extra_prefer1', sa.String(255), nullable=True),
            sa.Column('extra_prefer2', sa.String(255), nullable=True),
            sa.Column('extra_prefer3', sa.String(255), nullable=True),
            sa.Column('country_code', sa.String(10), nullable=True, comment='ISO Country Code'),
            sa.Column('birthday', sa.Date(), nullable=True, comment='생년월일'),
            sa.Column('language', sa.Enum('en', 'ko', 'ja', 'zh', name='languagetype'), nullable=False, comment='UI Language Preference'),
            sa.Column('is_join', sa.Boolean(), nullable=True, server_default=sa.text("'0'")),
            sa.Column('is_prefer', sa.Boolean(), nullable=True, server_default=sa.text("'0'")),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('email'),
            sa.UniqueConstraint('social_id'),
        )
        op.create_index('ix_users_id', 'users', ['id'], unique=False)

    # 2. chat_rooms (users 참조)
    if 'chat_rooms' not in existing:
        op.create_table(
            'chat_rooms',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('title', sa.String(255), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('history', sa.Text(), nullable=True),
            sa.Column('adult_num', sa.Integer(), nullable=True),
            sa.Column('child_num', sa.Integer(), nullable=True),
            sa.Column('start_date', sa.Date(), nullable=True),
            sa.Column('end_date', sa.Date(), nullable=True),
            sa.Column('bookmark_yn', sa.Boolean(), nullable=False, server_default=sa.text("'0'")),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_chat_rooms_id', 'chat_rooms', ['id'], unique=False)

    # 3. chat_messages (chat_rooms 참조)
    if 'chat_messages' not in existing:
        op.create_table(
            'chat_messages',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('room_id', sa.Integer(), sa.ForeignKey('chat_rooms.id'), nullable=True),
            sa.Column('message', sa.Text(), nullable=True),
            sa.Column('role', sa.Enum('human', 'ai', name='roletype'), nullable=True),
            sa.Column('image_path', sa.Text().with_variant(mysql.LONGTEXT(), 'mysql'), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('longitude', sa.Float(), nullable=True),
            sa.Column('latitude', sa.Float(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_chat_messages_id', 'chat_messages', ['id'], unique=False)

    # 4. chat_places (chat_messages 참조)
    if 'chat_places' not in existing:
        op.create_table(
            'chat_places',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('messages_id', sa.Integer(), sa.ForeignKey('chat_messages.id'), nullable=True),
            sa.Column('contenttypeid', sa.Integer(), nullable=True, server_default=sa.text('0')),
            sa.Column('llm_text', sa.Text(), nullable=True, comment='LLM 생성 텍스트'),
            sa.Column('name', sa.String(255), nullable=True),
            sa.Column('adress', sa.String(255), nullable=True),
            sa.Column('image_path', sa.String(255), nullable=True),
            sa.Column('longitude', sa.Float(), nullable=True),
            sa.Column('latitude', sa.Float(), nullable=True),
            sa.Column('bookmark_yn', sa.Boolean(), nullable=True, server_default=sa.text("'0'")),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_chat_places_id', 'chat_places', ['id'], unique=False)

    # 5. hot_places (FK 없음)
    if 'hot_places' not in existing:
        op.create_table(
            'hot_places',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.Text(), nullable=True),
            sa.Column('adress', sa.Text(), nullable=True),
            sa.Column('feature', sa.Text(), nullable=True),
            sa.Column('tag1', sa.Text(), nullable=True),
            sa.Column('tag2', sa.Text(), nullable=True),
            sa.Column('image_path', sa.String(255), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_hot_places_id', 'hot_places', ['id'], unique=False)

    # 6. reservation_list (users 참조)
    if 'reservation_list' not in existing:
        op.create_table(
            'reservation_list',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('category', sa.String(255), nullable=True),
            sa.Column('name', sa.String(255), nullable=True),
            sa.Column('date', sa.Date(), nullable=True),
            sa.Column('image_path', sa.String(255), nullable=True),
            sa.Column('details', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_reservation_list_id', 'reservation_list', ['id'], unique=False)

    # 7. diary_entries (users, chat_rooms 참조)
    if 'diary_entries' not in existing:
        op.create_table(
            'diary_entries',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('title', sa.String(255), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('entry_date', sa.Date(), nullable=False),
            sa.Column('cover_image_path', sa.String(1000), nullable=True),
            sa.Column('linked_chat_room_id', sa.Integer(), sa.ForeignKey('chat_rooms.id'), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_diary_entries_id', 'diary_entries', ['id'], unique=False)
        op.create_index('ix_diary_entries_entry_date', 'diary_entries', ['entry_date'], unique=False)
        op.create_index('ix_diary_entries_user_id', 'diary_entries', ['user_id'], unique=False)

    # 8. diary_entry_places (diary_entries, chat_places 참조)
    if 'diary_entry_places' not in existing:
        op.create_table(
            'diary_entry_places',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('entry_id', sa.Integer(), sa.ForeignKey('diary_entries.id'), nullable=False),
            sa.Column('chat_place_id', sa.Integer(), sa.ForeignKey('chat_places.id'), nullable=True),
            sa.Column('contenttypeid', sa.Integer(), nullable=True),
            sa.Column('name', sa.String(255), nullable=True),
            sa.Column('adress', sa.String(255), nullable=True),
            sa.Column('image_path', sa.String(1000), nullable=True),
            sa.Column('longitude', sa.Float(), nullable=True),
            sa.Column('latitude', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_diary_entry_places_id', 'diary_entry_places', ['id'], unique=False)
        op.create_index('ix_diary_entry_places_entry_id', 'diary_entry_places', ['entry_id'], unique=False)


def downgrade() -> None:
    op.drop_table('diary_entry_places')
    op.drop_table('diary_entries')
    op.drop_table('reservation_list')
    op.drop_table('hot_places')
    op.drop_table('chat_places')
    op.drop_table('chat_messages')
    op.drop_table('chat_rooms')
    op.drop_table('users')
