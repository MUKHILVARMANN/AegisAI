"""initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-09-28 20:00:00.000000

Mirrors the SQLAlchemy models in app/models exactly (table names, column
types, nullability, defaults) so `alembic upgrade head` and
`Base.metadata.create_all` produce identical schemas.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

from app.config import settings

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enable pgvector extension ─────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── Users ─────────────────────────────────────────────────────────────────
    user_role_enum = postgresql.ENUM('admin', 'user', name='userrole')
    user_role_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(320), nullable=False),
        sa.Column('username', sa.String(128), nullable=False),
        sa.Column('hashed_password', sa.String(512), nullable=False),
        sa.Column('role', sa.Enum('admin', 'user', name='userrole'), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    # ── Documents ─────────────────────────────────────────────────────────────
    doc_type_enum = postgresql.ENUM('pdf', 'docx', 'xlsx', 'csv', name='documenttype')
    doc_type_enum.create(op.get_bind(), checkfirst=True)
    doc_status_enum = postgresql.ENUM('uploaded', 'processing', 'indexed', 'failed', name='documentstatus')
    doc_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(512), nullable=False),
        sa.Column('type', sa.Enum('pdf', 'docx', 'xlsx', 'csv', name='documenttype'), nullable=False),
        sa.Column('status', sa.Enum('uploaded', 'processing', 'indexed', 'failed', name='documentstatus'), nullable=False),
        sa.Column('checksum', sa.String(64), nullable=False),
        sa.Column('storage_path', sa.String(1024), nullable=True),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('chunk_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_documents_checksum', 'documents', ['checksum'], unique=True)

    # ── Document Sections ─────────────────────────────────────────────────────
    op.create_table(
        'document_sections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('heading', sa.String(512), nullable=True),
        sa.Column('page_start', sa.Integer(), nullable=True),
        sa.Column('page_end', sa.Integer(), nullable=True),
        sa.Column('text', sa.Text(), nullable=True),
    )
    op.create_index('ix_document_sections_document_id', 'document_sections', ['document_id'])

    # ── Chunks (with pgvector) ────────────────────────────────────────────────
    op.create_table(
        'chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('section_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('parent_chunk_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('is_parent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('heading', sa.String(512), nullable=True),
        sa.Column('source_type', sa.String(64), nullable=True),
        sa.Column('chunk_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('extra_metadata', sa.JSON(), nullable=True),
        sa.Column('embedding', Vector(settings.embedding_dim), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_chunks_document_id', 'chunks', ['document_id'])
    op.create_index('ix_chunks_section_id', 'chunks', ['section_id'])
    op.create_index('ix_chunks_parent_chunk_id', 'chunks', ['parent_chunk_id'])

    # ── Conversations & Messages ──────────────────────────────────────────────
    message_role_enum = postgresql.ENUM('user', 'assistant', 'system', name='messagerole')
    message_role_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.Enum('user', 'assistant', 'system', name='messagerole'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('trace_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])
    op.create_index('ix_messages_trace_id', 'messages', ['trace_id'])

    # ── Traces ────────────────────────────────────────────────────────────────
    # Matches app/models/trace.py: UUID primary key, request_id unique-indexed,
    # all pipeline columns nullable (routes like SQL/summarize skip stages).
    op.create_table(
        'traces',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('request_id', sa.String(64), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('route', sa.String(64), nullable=True),
        sa.Column('routing_confidence', sa.Float(), nullable=True),
        sa.Column('routing_latency_ms', sa.Integer(), nullable=True),
        sa.Column('retrieval_latency_ms', sa.Integer(), nullable=True),
        sa.Column('retrieved_chunk_ids', sa.JSON(), nullable=True),
        sa.Column('retrieved_scores', sa.JSON(), nullable=True),
        sa.Column('reranker_latency_ms', sa.Integer(), nullable=True),
        sa.Column('final_chunk_ids', sa.JSON(), nullable=True),
        sa.Column('model', sa.String(128), nullable=True),
        sa.Column('prompt_version', sa.String(64), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('generation_latency_ms', sa.Integer(), nullable=True),
        sa.Column('estimated_cost_usd', sa.Float(), nullable=True),
        sa.Column('validation_passed', sa.Boolean(), nullable=True),
        sa.Column('validation_errors', sa.JSON(), nullable=True),
        sa.Column('confidence', sa.String(16), nullable=True),
        sa.Column('total_latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_traces_request_id', 'traces', ['request_id'], unique=True)
    op.create_index('ix_traces_conversation_id', 'traces', ['conversation_id'])

    # ── Feedback (table name matches the model: "feedback", no FK) ────────────
    op.create_table(
        'feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('request_id', sa.String(64), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_feedback_request_id', 'feedback', ['request_id'])

    # ── Evaluation Runs ───────────────────────────────────────────────────────
    op.create_table(
        'evaluation_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(256), nullable=True),
        sa.Column('status', sa.String(32), nullable=True, server_default='pending'),
        sa.Column('test_case_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ── Evaluation Results ────────────────────────────────────────────────────
    op.create_table(
        'evaluation_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('test_case_id', sa.String(128), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('expected_answer', sa.Text(), nullable=True),
        sa.Column('actual_answer', sa.Text(), nullable=True),
        sa.Column('metric', sa.String(64), nullable=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_evaluation_results_run_id', 'evaluation_results', ['run_id'])


def downgrade() -> None:
    op.drop_index('ix_evaluation_results_run_id', table_name='evaluation_results')
    op.drop_table('evaluation_results')
    op.drop_table('evaluation_runs')
    op.drop_index('ix_feedback_request_id', table_name='feedback')
    op.drop_table('feedback')
    op.drop_index('ix_traces_conversation_id', table_name='traces')
    op.drop_index('ix_traces_request_id', table_name='traces')
    op.drop_table('traces')
    op.drop_index('ix_messages_trace_id', table_name='messages')
    op.drop_index('ix_messages_conversation_id', table_name='messages')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_index('ix_chunks_parent_chunk_id', table_name='chunks')
    op.drop_index('ix_chunks_section_id', table_name='chunks')
    op.drop_index('ix_chunks_document_id', table_name='chunks')
    op.drop_table('chunks')
    op.drop_index('ix_document_sections_document_id', table_name='document_sections')
    op.drop_table('document_sections')
    op.drop_index('ix_documents_checksum', table_name='documents')
    op.drop_table('documents')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
    op.execute('DROP TYPE IF EXISTS messagerole')
    op.execute('DROP TYPE IF EXISTS documentstatus')
    op.execute('DROP TYPE IF EXISTS documenttype')
    op.execute('DROP TYPE IF EXISTS userrole')
