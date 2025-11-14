"""
Migration to fix Suspect model - remove fields column if it exists

This migration removes the 'fields' column from the suspects table
since the Suspect model uses a relationship, not a column.

Run from the backend directory:
    cd backend
    python migrations/fix_suspect_fields_column.py
"""

import sys
import os

# Add parent directory to path to import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine

def upgrade():
    """Remove fields column from suspects table if it exists"""
    with engine.connect() as conn:
        # Check if the column exists and drop it
        try:
            conn.execute(text("""
                ALTER TABLE suspects 
                DROP COLUMN IF EXISTS fields;
            """))
            conn.commit()
            print("✅ Removed 'fields' column from suspects table")
        except Exception as e:
            print(f"❌ Error removing fields column: {e}")
            raise

def downgrade():
    """Add fields column back (not recommended)"""
    pass

if __name__ == "__main__":
    print("Running migration: Remove fields column from suspects table")
    upgrade()
    print("Migration complete!")
