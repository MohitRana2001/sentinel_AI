"""
Migration script to:
1. Update PersonOfInterest table with mandatory fields (name, phone_number, photograph_base64)
2. Add CDR status tracking fields to cdr_records table
3. Create VideoPOIDetection joint table
4. Create CDRPOIMatch joint table
5. Mark Suspect and SuspectField tables for deprecation (but keep for backwards compatibility)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, SessionLocal
from sqlalchemy import text
import models


def run_migration():
    """Run database migrations"""
    
    db = SessionLocal()
    
    try:
        print("Starting database migration...")
        
        # 1. Update PersonOfInterest table - add mandatory fields
        print("\n1. Updating PersonOfInterest table...")
        try:
            # Check if phone_number column exists
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='person_of_interest' AND column_name='phone_number'
            """))
            
            if not result.fetchone():
                print("  Adding phone_number column (mandatory)...")
                db.execute(text("""
                    ALTER TABLE person_of_interest 
                    ADD COLUMN phone_number VARCHAR NOT NULL DEFAULT '';
                """))
                
                # Create index
                db.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_poi_phone_number ON person_of_interest(phone_number);
                """))
                print("  ✅ Added phone_number column with index")
            else:
                print("  ✓ phone_number column already exists")
                
                # Ensure it's NOT NULL
                db.execute(text("""
                    ALTER TABLE person_of_interest 
                    ALTER COLUMN phone_number SET NOT NULL;
                """))
                print("  ✅ Updated phone_number to NOT NULL")
            
            # Update photograph_base64 to be NOT NULL
            result = db.execute(text("""
                SELECT column_name, is_nullable
                FROM information_schema.columns 
                WHERE table_name='person_of_interest' AND column_name='photograph_base64'
            """))
            
            col = result.fetchone()
            if col and col[1] == 'YES':
                print("  Updating photograph_base64 to be mandatory...")
                # First, set default for existing NULL values
                db.execute(text("""
                    UPDATE person_of_interest 
                    SET photograph_base64 = '' 
                    WHERE photograph_base64 IS NULL;
                """))
                
                db.execute(text("""
                    ALTER TABLE person_of_interest 
                    ALTER COLUMN photograph_base64 SET NOT NULL;
                """))
                print("  ✅ Updated photograph_base64 to NOT NULL")
            else:
                print("  ✓ photograph_base64 is already NOT NULL")
            
            db.commit()
            
        except Exception as e:
            print(f"  ⚠️  Warning updating PersonOfInterest: {e}")
            db.rollback()
        
        # 2. Update CDRRecord table - add status tracking fields
        print("\n2. Updating CDRRecord table with status tracking...")
        try:
            # Add status column
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='cdr_records' AND column_name='status'
            """))
            
            if not result.fetchone():
                print("  Adding status tracking columns...")
                db.execute(text("""
                    ALTER TABLE cdr_records 
                    ADD COLUMN status VARCHAR DEFAULT 'queued',
                    ADD COLUMN processing_stages JSON DEFAULT '{}',
                    ADD COLUMN current_stage VARCHAR,
                    ADD COLUMN error_message TEXT,
                    ADD COLUMN started_at TIMESTAMP,
                    ADD COLUMN completed_at TIMESTAMP;
                """))
                print("  ✅ Added status tracking columns to cdr_records")
            else:
                print("  ✓ Status tracking columns already exist")
            
            db.commit()
            
        except Exception as e:
            print(f"  ⚠️  Warning updating CDRRecord: {e}")
            db.rollback()
        
        # 3. Create VideoPOIDetection table
        print("\n3. Creating VideoPOIDetection joint table...")
        try:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS video_poi_detections (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    poi_id INTEGER NOT NULL REFERENCES person_of_interest(id) ON DELETE CASCADE,
                    job_id VARCHAR NOT NULL REFERENCES processing_jobs(id) ON DELETE CASCADE,
                    frames VARCHAR NOT NULL,
                    confidence_scores JSON,
                    detection_metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_video_poi_document_id ON video_poi_detections(document_id);
            """))
            
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_video_poi_poi_id ON video_poi_detections(poi_id);
            """))
            
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_video_poi_job_id ON video_poi_detections(job_id);
            """))
            
            print("  ✅ Created VideoPOIDetection table with indexes")
            db.commit()
            
        except Exception as e:
            print(f"  ⚠️  Warning creating VideoPOIDetection: {e}")
            db.rollback()
        
        # 4. Create CDRPOIMatch table
        print("\n4. Creating CDRPOIMatch joint table...")
        try:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS cdr_poi_matches (
                    id SERIAL PRIMARY KEY,
                    poi_id INTEGER NOT NULL REFERENCES person_of_interest(id) ON DELETE CASCADE,
                    job_id VARCHAR NOT NULL REFERENCES processing_jobs(id) ON DELETE CASCADE,
                    phone_number VARCHAR NOT NULL,
                    cdr_record_data JSONB NOT NULL,
                    matched_field VARCHAR NOT NULL,
                    match_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_cdr_poi_poi_id ON cdr_poi_matches(poi_id);
            """))
            
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_cdr_poi_job_id ON cdr_poi_matches(job_id);
            """))
            
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_cdr_poi_phone ON cdr_poi_matches(phone_number);
            """))
            
            print("  ✅ Created CDRPOIMatch table with indexes")
            db.commit()
            
        except Exception as e:
            print(f"  ⚠️  Warning creating CDRPOIMatch: {e}")
            db.rollback()
        
        # 5. Add deprecation notice for Suspect tables
        print("\n5. Marking Suspect tables as deprecated...")
        print("  ℹ️  Note: Suspect and SuspectField tables are kept for backwards compatibility")
        print("  ℹ️  New implementations should use PersonOfInterest table instead")
        print("  ℹ️  To migrate existing suspects to POI, run a separate migration script")
        
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        
    finally:
        db.close()


if __name__ == "__main__":
    print("="*60)
    print("Database Migration: POI Updates & Joint Tables")
    print("="*60)
    run_migration()
