"""add_rotation_angle_to_pages

Revision ID: 002_rotation_angle
Revises: 001_initial
Create Date: 2026-01-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_rotation_angle'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add rotation_angle column to document_pages
    op.add_column('document_pages', sa.Column('rotation_angle', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('document_pages', 'rotation_angle')
