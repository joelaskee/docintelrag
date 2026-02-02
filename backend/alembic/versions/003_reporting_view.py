"""create_reporting_view

Revision ID: 003_reporting
Revises: 002_rotation
Create Date: 2026-01-30 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_reporting'
down_revision: Union[str, None] = '002_rotation_angle'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Reporting View
    op.execute("""
    CREATE OR REPLACE VIEW v_reporting_documents AS
    SELECT 
        d.id AS document_id,
        d.tenant_id, 
        d.filename,
        d.status,
        d.doc_type AS document_type,
        d.created_at AS upload_date,
        d.doc_date AS document_date,
        d.doc_number AS document_number,
        d.fornitore AS supplier_name,
        d.emittente AS issuer_name,
        d.totale AS total_amount,
        d.imponibile AS net_amount,
        d.importo_iva AS tax_amount,
        'EUR' as currency,
        extract(year from (COALESCE(d.doc_date, d.created_at))) as doc_year,
        extract(month from (COALESCE(d.doc_date, d.created_at))) as doc_month
    FROM documents d;
    """)
    
    # 2. Create BI User (if not exists)
    # Note: passwords should be managed securely, but for MVP we set a default
    # Using DO block to avoid error if role exists
    op.execute("""
    DO
    $do$
    BEGIN
       IF NOT EXISTS (
          SELECT FROM pg_catalog.pg_roles
          WHERE  rolname = 'bi_user') THEN
          CREATE ROLE bi_user WITH LOGIN PASSWORD 'bi_readonly_password';
       END IF;
    END
    $do$;
    """)
    
    # 3. Grant Privileges
    op.execute("GRANT CONNECT ON DATABASE docintelrag TO bi_user;")
    op.execute("GRANT USAGE ON SCHEMA public TO bi_user;")
    op.execute("GRANT SELECT ON v_reporting_documents TO bi_user;")


def downgrade() -> None:
    # Drop View
    op.execute("DROP VIEW IF EXISTS v_reporting_documents;")
    
    # Revoke and Drop Role
    op.execute("REVOKE ALL PRIVILEGES ON v_reporting_documents FROM bi_user;")
    op.execute("REVOKE USAGE ON SCHEMA public FROM bi_user;")
    op.execute("REVOKE CONNECT ON DATABASE docintelrag FROM bi_user;")
    op.execute("DROP ROLE IF EXISTS bi_user;")
