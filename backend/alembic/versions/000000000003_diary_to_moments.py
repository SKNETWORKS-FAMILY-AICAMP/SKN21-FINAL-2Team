"""diary_to_moments - diary_entries+diary_entry_places → moments, reservation_list → reservations

Revision ID: 000000000003
Revises: 000000000002
Create Date: 2026-03-26

기존 DB 환경에서 테이블 구조를 변경합니다.
- reservation_list  → reservations (rename)
- diary_entry_places → DROP
- diary_entries → moments (rename) + 컬럼 변경
    - cover_image_path RENAME → image_path
    - linked_chat_room_id DROP (FK 선제거 후)
    - ADD adress, longitude, latitude

신규 환경에서는 baseline(001)이 이미 새 이름으로 생성하므로 모두 no-op입니다.
각 단계가 독립적으로 멱등(idempotent)하게 동작합니다.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '000000000003'
down_revision: Union[str, Sequence[str], None] = '000000000002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    """매 호출마다 fresh inspector 반환 (rename 후 캐시 문제 방지)"""
    return sa.inspect(op.get_bind())


def _table_exists(name: str) -> bool:
    return name in _inspector().get_table_names()


def _col_exists(table: str, col: str) -> bool:
    return col in {c['name'] for c in _inspector().get_columns(table)}


def _drop_fks_to(table: str, referred_table: str) -> None:
    """table에서 referred_table을 참조하는 FK를 모두 제거"""
    try:
        for fk in _inspector().get_foreign_keys(table):
            if fk.get('referred_table') == referred_table and fk.get('name'):
                op.drop_constraint(fk['name'], table, type_='foreignkey')
    except Exception:
        pass


def _drop_all_fks(table: str) -> None:
    try:
        for fk in _inspector().get_foreign_keys(table):
            if fk.get('name'):
                op.drop_constraint(fk['name'], table, type_='foreignkey')
    except Exception:
        pass


def upgrade() -> None:
    # ── 1. reservation_list → reservations ──────────────────────────────────
    if _table_exists('reservation_list') and not _table_exists('reservations'):
        op.rename_table('reservation_list', 'reservations')

    # ── 2. diary_entry_places DROP ───────────────────────────────────────────
    if _table_exists('diary_entry_places'):
        _drop_all_fks('diary_entry_places')
        op.drop_table('diary_entry_places')

    # ── 3. diary_entries → moments rename ───────────────────────────────────
    if _table_exists('diary_entries') and not _table_exists('moments'):
        _drop_fks_to('diary_entries', 'chat_rooms')
        op.rename_table('diary_entries', 'moments')

    # ── 4. moments 컬럼 정리 (rename 여부와 관계없이 독립 실행) ──────────────
    if _table_exists('moments'):
        # 4-1. cover_image_path → image_path
        if _col_exists('moments', 'cover_image_path') and not _col_exists('moments', 'image_path'):
            op.alter_column(
                'moments', 'cover_image_path',
                new_column_name='image_path',
                existing_type=sa.String(1000),
                nullable=True,
            )

        # 4-2. linked_chat_room_id DROP (FK 먼저 제거)
        if _col_exists('moments', 'linked_chat_room_id'):
            _drop_fks_to('moments', 'chat_rooms')
            op.drop_column('moments', 'linked_chat_room_id')

        # 4-3. 새 컬럼 추가
        if not _col_exists('moments', 'adress'):
            op.add_column('moments', sa.Column('adress', sa.String(255), nullable=True))
        if not _col_exists('moments', 'longitude'):
            op.add_column('moments', sa.Column('longitude', sa.Float(), nullable=True))
        if not _col_exists('moments', 'latitude'):
            op.add_column('moments', sa.Column('latitude', sa.Float(), nullable=True))


def downgrade() -> None:
    # moments → diary_entries (역방향)
    if _table_exists('moments'):
        for col in ('adress', 'longitude', 'latitude'):
            if _col_exists('moments', col):
                op.drop_column('moments', col)

        if _col_exists('moments', 'image_path') and not _col_exists('moments', 'cover_image_path'):
            op.alter_column(
                'moments', 'image_path',
                new_column_name='cover_image_path',
                existing_type=sa.String(1000),
                nullable=True,
            )

        if not _col_exists('moments', 'linked_chat_room_id'):
            op.add_column('moments', sa.Column(
                'linked_chat_room_id', sa.Integer(),
                sa.ForeignKey('chat_rooms.id'), nullable=True,
            ))

        if not _table_exists('diary_entries'):
            op.rename_table('moments', 'diary_entries')

    # reservations → reservation_list
    if _table_exists('reservations') and not _table_exists('reservation_list'):
        op.rename_table('reservations', 'reservation_list')
