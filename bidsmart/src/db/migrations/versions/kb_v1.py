"""Add kb_documents and kb_chunks tables.

Revision ID: kb_v1
Revises: review_items_v1
Create Date: 2026-05-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'kb_v1'
down_revision: Union[str, None] = 'review_items_v1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'kb_documents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False, server_default='manual'),
        sa.Column('source_path', sa.String(500), nullable=True),
        sa.Column('chunk_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'kb_chunks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('kb_documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('heading', sa.String(255), nullable=True),
        sa.Column('embedding_json', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_kb_chunks_doc', 'kb_chunks', ['document_id'])


def downgrade() -> None:
    op.drop_index('ix_kb_chunks_doc', table_name='kb_chunks')
    op.drop_table('kb_chunks')
    op.drop_table('kb_documents')
