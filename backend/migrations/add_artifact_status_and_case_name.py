"""
Migration: Add per-artifact status tracking and case name fields

Run this script to add:
1. case_name and parent_job_id to processing_jobs table
2. status, processing_stages, current_stage, error_message, started_at, completed_at to documents table

Usage:
    python migrations/add_artifact_status_and_case_name.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine, SessionLocal

def run_migration():
    """Run database migration to add new columns"""
    
    migrations = [
        # 1. Add case_name and parent_job_id to processing_jobs
        """
        ALTER TABLE processing_jobs 
        ADD COLUMN IF NOT EXISTS case_name VARCHAR,
        ADD COLUMN IF NOT EXISTS parent_job_id VARCHAR REFERENCES processing_jobs(id);
        """,
        
        # 2. Create index on case_name for faster lookups
        """
        CREATE INDEX IF NOT EXISTS ix_processing_jobs_case_name 
        ON processing_jobs(case_name);
        """,
        
        # 3. Add per-artifact status fields to documents table
        """
        DO $$
        BEGIN
            -- Add status column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='documents' AND column_name='status'
            ) THEN
                ALTER TABLE documents ADD COLUMN status VARCHAR DEFAULT 'queued';
            END IF;
            
            -- Add processing_stages column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='documents' AND column_name='processing_stages'
            ) THEN
                ALTER TABLE documents ADD COLUMN processing_stages JSON;
            END IF;
            
            -- Add current_stage column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='documents' AND column_name='current_stage'
            ) THEN
                ALTER TABLE documents ADD COLUMN current_stage VARCHAR;
            END IF;
            
            -- Add error_message column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='documents' AND column_name='error_message'
            ) THEN
                ALTER TABLE documents ADD COLUMN error_message TEXT;
            END IF;
            
            -- Add started_at column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='documents' AND column_name='started_at'
            ) THEN
                ALTER TABLE documents ADD COLUMN started_at TIMESTAMP;
            END IF;
            
            -- Add completed_at column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='documents' AND column_name='completed_at'
            ) THEN
                ALTER TABLE documents ADD COLUMN completed_at TIMESTAMP;
            END IF;
        END $$;
        """,
        
        # 4. Update existing documents to have 'queued' status
        """
        UPDATE documents 
        SET status = 'queued' 
        WHERE status IS NULL;
        """,
    ]
    
    db = SessionLocal()
    try:
        for i, migration_sql in enumerate(migrations, 1):
            print(f"Running migration {i}/{len(migrations)}...")
            db.execute(text(migration_sql))
            db.commit()
            print(f"✅ Migration {i} completed")
        
        print("\n✅ All migrations completed successfully!")
        
        # Verify the changes
        print("\n📊 Verifying schema changes...")
        
        # Check processing_jobs columns
        result = db.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'processing_jobs' 
            AND column_name IN ('case_name', 'parent_job_id')
            ORDER BY column_name;
        """))
        
        print("\nProcessing Jobs new columns:")
        for row in result:
            print(f"  - {row[0]}: {row[1]}")
        
        # Check documents columns
        result = db.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'documents' 
            AND column_name IN ('status', 'processing_stages', 'current_stage', 
                                'error_message', 'started_at', 'completed_at')
            ORDER BY column_name;
        """))
        
        print("\nDocuments new columns:")
        for row in result:
            print(f"  - {row[0]}: {row[1]}")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("🔧 Starting database migration...")
    print("=" * 60)
    run_migration()
    print("=" * 60)
    print("✅ Migration complete!")
