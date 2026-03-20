"""rename_place_id_to_contenttypeid_add_llm_text

Revision ID: 896f411016d2
Revises: dfbedd9b2448
Create Date: 2026-03-18 08:21:04.331568

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '896f411016d2'
down_revision: Union[str, Sequence[str], None] = 'dfbedd9b2448'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # chat_places: place_id → contenttypeid 리네임 + llm_text 추가
    op.alter_column('chat_places', 'place_id', new_column_name='contenttypeid',
                    existing_type=sa.Integer(), existing_nullable=True)
    op.add_column('chat_places', sa.Column('llm_text', sa.Text(), nullable=True, comment='LLM 생성 텍스트'))

    # diary_entry_places: place_id → contenttypeid 리네임
    op.alter_column('diary_entry_places', 'place_id', new_column_name='contenttypeid',
                    existing_type=sa.Integer(), existing_nullable=True)


def downgrade() -> None:
    op.alter_column('diary_entry_places', 'contenttypeid', new_column_name='place_id',
                    existing_type=sa.Integer(), existing_nullable=True)
    op.drop_column('chat_places', 'llm_text')
    op.alter_column('chat_places', 'contenttypeid', new_column_name='place_id',
                    existing_type=sa.Integer(), existing_nullable=True)
