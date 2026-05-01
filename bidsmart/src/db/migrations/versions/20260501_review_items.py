"""Add confirmed_items and ignored_items tables for review result handling.

Revision ID: review_items_v1
Revises: proj_meta_v1
Create Date: 2026-05-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'review_items_v1'
down_revision: Union[str, None] = 'proj_meta_v1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'confirmed_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('requirement', sa.Text(), nullable=False),
        sa.Column('bid_response', sa.Text(), nullable=True),
        sa.Column('verdict', sa.String(32), nullable=False),
        sa.Column('weight_level', sa.String(16), nullable=True),
        sa.Column('tender_page', sa.Integer(), default=0),
        sa.Column('bid_page', sa.Integer(), default=0),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('suggestion', sa.Text(), nullable=True),
        sa.Column('handled_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_confirmed_project', 'confirmed_items', ['project_id'])

    op.create_table(
        'ignored_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('requirement', sa.Text(), nullable=False),
        sa.Column('bid_response', sa.Text(), nullable=True),
        sa.Column('verdict', sa.String(32), nullable=False),
        sa.Column('weight_level', sa.String(16), nullable=True),
        sa.Column('tender_page', sa.Integer(), default=0),
        sa.Column('bid_page', sa.Integer(), default=0),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('suggestion', sa.Text(), nullable=True),
        sa.Column('handled_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ignored_project', 'ignored_items', ['project_id'])


def downgrade() -> None:
    op.drop_index('ix_ignored_project', table_name='ignored_items')
    op.drop_table('ignored_items')
    op.drop_index('ix_confirmed_project', table_name='confirmed_items')
    op.drop_table('confirmed_items')
