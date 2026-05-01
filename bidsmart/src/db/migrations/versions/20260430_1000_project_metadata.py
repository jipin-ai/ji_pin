"""Add project metadata fields: department, editor, bid_time

Revision ID: proj_meta_v1
Revises: 20260430_0850_security_models
Create Date: 2026-04-30 10:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'proj_meta_v1'
down_revision: Union[str, None] = 'b1a2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('department', sa.String(255), nullable=True))
    op.add_column('projects', sa.Column('editor', sa.String(255), nullable=True))
    op.add_column('projects', sa.Column('bid_time', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('projects', 'bid_time')
    op.drop_column('projects', 'editor')
    op.drop_column('projects', 'department')
