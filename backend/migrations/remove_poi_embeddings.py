#!/usr/bin/env python3
"""
Migration: Remove embedding columns from person_of_interest table and add job_id

This migration:
1. Drops the photograph_embedding column (128-dimensional face encodings)
2. Drops the details_embedding column (1024-dimensional text embeddings)
3. Drops the associated vector indexes
4. Adds job_id column to associate POIs with specific upload jobs

Run this migration after updating models.py
"""

from sqlalchemy import create_engine, text
from database import SQLALCHEMY_DATABASE_URL
import sys

def run_migration():
    """Run the migration to remove POI embedding columns"""
    print("🔧 Starting migration: Remove POI embeddings...")
    
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            # 1. Drop indexes first (they depend on the columns)
            print("📉 Dropping vector indexes...")
            
            conn.execute(text("""
                DROP INDEX IF EXISTS ix_poi_photo_embedding;
            """))
            print("  ✅ Dropped ix_poi_photo_embedding")
            
            conn.execute(text("""
                DROP INDEX IF EXISTS ix_poi_details_embedding;
            """))
            print("  ✅ Dropped ix_poi_details_embedding")
            
            # 2. Drop the embedding columns
            print("📉 Dropping embedding columns...")
            
            conn.execute(text("""
                ALTER TABLE person_of_interest 
                DROP COLUMN IF EXISTS photograph_embedding;
            """))
            print("  ✅ Dropped photograph_embedding column")
            
            conn.execute(text("""
                ALTER TABLE person_of_interest 
                DROP COLUMN IF EXISTS details_embedding;
            """))
            print("  ✅ Dropped details_embedding column")
            
            # 3. Add job_id column to associate POIs with upload jobs
            print("➕ Adding job_id column...")
            
            conn.execute(text("""
                ALTER TABLE person_of_interest 
                ADD COLUMN IF NOT EXISTS job_id VARCHAR;
            """))
            print("  ✅ Added job_id column")
            
            # 4. Add foreign key constraint
            print("🔗 Adding foreign key constraint...")
            
            conn.execute(text("""
                ALTER TABLE person_of_interest 
                ADD CONSTRAINT fk_poi_job_id 
                FOREIGN KEY (job_id) REFERENCES processing_jobs(id)
                ON DELETE SET NULL;
            """))
            print("  ✅ Added foreign key constraint")
            
            # 5. Add index on job_id for faster queries
            print("📈 Creating index on job_id...")
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_poi_job_id 
                ON person_of_interest(job_id);
            """))
            print("  ✅ Created index on job_id")
            
            # Commit transaction
            trans.commit()
            print("\n✅ Migration completed successfully!")
            print("\nChanges made:")
            print("  • Removed photograph_embedding column (no longer storing face encodings)")
            print("  • Removed details_embedding column")
            print("  • Removed associated vector indexes")
            print("  • Added job_id column to link POIs with upload jobs")
            print("  • Added foreign key constraint and index")
            
        except Exception as e:
            trans.rollback()
            print(f"\n❌ Migration failed: {e}")
            print("Rolling back changes...")
            sys.exit(1)

if __name__ == "__main__":
    run_migration()
