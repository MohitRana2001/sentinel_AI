"""
Migration: Add detected_language column to documents table
Date: 2024-01-XX
Purpose: Store detected language for documents to reflect in file naming and metadata
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    """Add detected_language column to documents table"""
    op.add_column('documents', sa.Column('detected_language', sa.String(10), nullable=True))
    print("✅ Added detected_language column to documents table")


def downgrade():
    """Remove detected_language column from documents table"""
    op.drop_column('documents', 'detected_language')
    print("✅ Removed detected_language column from documents table")
