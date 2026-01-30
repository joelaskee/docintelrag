"""Initial schema with all models

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Tenants table
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('config', postgresql.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    
    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('role', sa.Enum('admin', 'operatore', 'manager', name='userrole'), nullable=False),
        sa.Column('is_active', sa.String(1), nullable=False, server_default='Y'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_users_tenant', 'users', ['tenant_id'])
    
    # Documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('filename', sa.String(512), nullable=False),
        sa.Column('file_path', sa.String(1024), nullable=False),
        sa.Column('file_hash', sa.String(64), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('queued', 'processing', 'extracted', 'validated', 'failed', name='documentstatus'), nullable=False),
        sa.Column('is_scanned', sa.Boolean(), nullable=True),
        sa.Column('ocr_quality', sa.Float(), nullable=True),
        sa.Column('doc_type', sa.Enum('po', 'ddt', 'fattura', 'altro', name='documenttype'), nullable=True),
        sa.Column('doc_type_confidence', sa.Float(), nullable=True),
        sa.Column('doc_type_override', sa.Enum('po', 'ddt', 'fattura', 'altro', name='documenttype'), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('warnings', postgresql.JSON(), nullable=False, server_default='[]'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('doc_number', sa.String(100), nullable=True),
        sa.Column('doc_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_documents_tenant', 'documents', ['tenant_id'])
    op.create_index('ix_documents_hash', 'documents', ['tenant_id', 'file_hash'])
    op.create_index('ix_documents_status', 'documents', ['tenant_id', 'status'])
    
    # Document pages table
    op.create_table(
        'document_pages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('text_content', sa.Text(), nullable=True),
        sa.Column('ocr_confidence', sa.Float(), nullable=True),
    )
    op.create_index('ix_document_pages_doc', 'document_pages', ['document_id'])
    
    # Extracted fields table
    op.create_table(
        'extracted_fields',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('raw_value', sa.Text(), nullable=True),
        sa.Column('normalized_value', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0'),
        sa.Column('page', sa.Integer(), nullable=True),
        sa.Column('bbox', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_extracted_fields_doc', 'extracted_fields', ['document_id'])
    
    # Document lines table
    op.create_table(
        'document_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=False),
        sa.Column('item_code', sa.String(100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=True),
        sa.Column('unit', sa.String(20), nullable=True),
        sa.Column('unit_price', sa.Float(), nullable=True),
        sa.Column('total_price', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0'),
        sa.Column('page', sa.Integer(), nullable=True),
        sa.Column('bbox', postgresql.JSON(), nullable=True),
        sa.Column('embedding', sa.dialects.postgresql.ARRAY(sa.Float), nullable=True),  # Vector stored as array
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_document_lines_doc', 'document_lines', ['document_id'])
    
    # Field events table (audit trail)
    op.create_table(
        'field_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('field_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('extracted_fields.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('event_type', sa.Enum('created', 'updated', 'validated', name='fieldeventtype'), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_field_events_field', 'field_events', ['field_id'])


def downgrade() -> None:
    op.drop_table('field_events')
    op.drop_table('document_lines')
    op.drop_table('extracted_fields')
    op.drop_table('document_pages')
    op.drop_table('documents')
    op.drop_table('users')
    op.drop_table('tenants')
    
    op.execute('DROP TYPE IF EXISTS fieldeventtype')
    op.execute('DROP TYPE IF EXISTS documenttype')
    op.execute('DROP TYPE IF EXISTS documentstatus')
    op.execute('DROP TYPE IF EXISTS userrole')
