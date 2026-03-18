"""add birthday column to users

Revision ID: b5c6d7e8f9a0
Revises: a1b2c3d4e5f6
Create Date: 2026-03-18

"""
from alembic import op
import sqlalchemy as sa

revision = 'b5c6d7e8f9a0'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('users', sa.Column('birthday', sa.Date(), nullable=True, comment='생년월일'))

def downgrade() -> None:
    op.drop_column('users', 'birthday')
