"""Add details to reservation

Revision ID: 4c19bb5312a8
Revises: a1b2c3d4e5f6
Create Date: 2026-03-16 10:32:45.928241

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy import inspect as sa_inspect


def _index_exists(conn, table: str, index_name: str) -> bool:
    return any(i['name'] == index_name for i in sa_inspect(conn).get_indexes(table))


def _column_exists(conn, table: str, column: str) -> bool:
    return any(c['name'] == column for c in sa_inspect(conn).get_columns(table))


def _fk_exists(conn, table: str, fk_name: str) -> bool:
    return any(fk['name'] == fk_name for fk in sa_inspect(conn).get_foreign_keys(table))

# revision identifiers, used by Alembic.
revision: str = '4c19bb5312a8'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    op.alter_column('chat_places', 'bookmark_yn',
               existing_type=mysql.TINYINT(display_width=1),
               nullable=True,
               existing_server_default=sa.text("'0'"))
    if not _index_exists(conn, 'chat_places', 'ix_chat_places_id'):
        op.create_index(op.f('ix_chat_places_id'), 'chat_places', ['id'], unique=False)
    op.alter_column('chat_rooms', 'created_at',
               existing_type=mysql.TIMESTAMP(),
               type_=sa.DateTime(),
               existing_nullable=True,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    if not _index_exists(conn, 'chat_rooms', 'ix_chat_rooms_id'):
        op.create_index(op.f('ix_chat_rooms_id'), 'chat_rooms', ['id'], unique=False)
    if _fk_exists(conn, 'users', 'users_ibfk_1'):
        op.drop_constraint(op.f('users_ibfk_1'), 'users', type_='foreignkey')
    op.alter_column('country', 'code',
               existing_type=mysql.VARCHAR(length=255),
               type_=sa.String(length=10),
               comment='ISO Country Code',
               existing_nullable=False)
    op.alter_column('country', 'name',
               existing_type=mysql.VARCHAR(length=255),
               comment='Country Name',
               existing_nullable=True)
    op.alter_column('diary_entries', 'cover_image_path',
               existing_type=mysql.VARCHAR(length=255),
               type_=sa.String(length=1000),
               existing_nullable=True)
    op.alter_column('diary_entries', 'created_at',
               existing_type=mysql.TIMESTAMP(),
               type_=sa.DateTime(),
               existing_nullable=True,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    op.alter_column('diary_entries', 'updated_at',
               existing_type=mysql.TIMESTAMP(),
               type_=sa.DateTime(),
               existing_nullable=True,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    if not _index_exists(conn, 'diary_entries', 'ix_diary_entries_entry_date'):
        op.create_index(op.f('ix_diary_entries_entry_date'), 'diary_entries', ['entry_date'], unique=False)
    if not _index_exists(conn, 'diary_entries', 'ix_diary_entries_id'):
        op.create_index(op.f('ix_diary_entries_id'), 'diary_entries', ['id'], unique=False)
    if not _index_exists(conn, 'diary_entries', 'ix_diary_entries_user_id'):
        op.create_index(op.f('ix_diary_entries_user_id'), 'diary_entries', ['user_id'], unique=False)
    op.alter_column('diary_entry_places', 'image_path',
               existing_type=mysql.VARCHAR(length=255),
               type_=sa.String(length=1000),
               existing_nullable=True)
    op.alter_column('diary_entry_places', 'created_at',
               existing_type=mysql.TIMESTAMP(),
               type_=sa.DateTime(),
               existing_nullable=True,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    if not _index_exists(conn, 'diary_entry_places', 'ix_diary_entry_places_entry_id'):
        op.create_index(op.f('ix_diary_entry_places_entry_id'), 'diary_entry_places', ['entry_id'], unique=False)
    if not _index_exists(conn, 'diary_entry_places', 'ix_diary_entry_places_id'):
        op.create_index(op.f('ix_diary_entry_places_id'), 'diary_entry_places', ['id'], unique=False)
    if not _index_exists(conn, 'hot_places', 'ix_hot_places_id'):
        op.create_index(op.f('ix_hot_places_id'), 'hot_places', ['id'], unique=False)
    if not _column_exists(conn, 'reservation_list', 'details'):
        op.add_column('reservation_list', sa.Column('details', sa.JSON(), nullable=True))
    if not _index_exists(conn, 'reservation_list', 'ix_reservation_list_id'):
        op.create_index(op.f('ix_reservation_list_id'), 'reservation_list', ['id'], unique=False)
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
    if not _index_exists(conn, 'users', 'ix_users_id'):
        op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_foreign_key(op.f('users_ibfk_1'), 'users', 'country', ['country_code'], ['code'])
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
    op.drop_index(op.f('ix_reservation_list_id'), table_name='reservation_list')
    op.drop_column('reservation_list', 'details')
    op.drop_index(op.f('ix_hot_places_id'), table_name='hot_places')
    op.drop_index(op.f('ix_diary_entry_places_id'), table_name='diary_entry_places')
    op.drop_index(op.f('ix_diary_entry_places_entry_id'), table_name='diary_entry_places')
    op.alter_column('diary_entry_places', 'created_at',
               existing_type=sa.DateTime(),
               type_=mysql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    op.alter_column('diary_entry_places', 'image_path',
               existing_type=sa.String(length=1000),
               type_=mysql.VARCHAR(length=255),
               existing_nullable=True)
    op.drop_index(op.f('ix_diary_entries_user_id'), table_name='diary_entries')
    op.drop_index(op.f('ix_diary_entries_id'), table_name='diary_entries')
    op.drop_index(op.f('ix_diary_entries_entry_date'), table_name='diary_entries')
    op.alter_column('diary_entries', 'updated_at',
               existing_type=sa.DateTime(),
               type_=mysql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    op.alter_column('diary_entries', 'created_at',
               existing_type=sa.DateTime(),
               type_=mysql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    op.alter_column('diary_entries', 'cover_image_path',
               existing_type=sa.String(length=1000),
               type_=mysql.VARCHAR(length=255),
               existing_nullable=True)
    op.alter_column('country', 'name',
               existing_type=mysql.VARCHAR(length=255),
               comment=None,
               existing_comment='Country Name',
               existing_nullable=True)
    op.alter_column('country', 'code',
               existing_type=sa.String(length=10),
               type_=mysql.VARCHAR(length=255),
               comment=None,
               existing_comment='ISO Country Code',
               existing_nullable=False)
    op.drop_index(op.f('ix_chat_rooms_id'), table_name='chat_rooms')
    op.alter_column('chat_rooms', 'created_at',
               existing_type=sa.DateTime(),
               type_=mysql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    op.drop_index(op.f('ix_chat_places_id'), table_name='chat_places')
    op.alter_column('chat_places', 'bookmark_yn',
               existing_type=mysql.TINYINT(display_width=1),
               nullable=False,
               existing_server_default=sa.text("'0'"))
    # ### end Alembic commands ###
