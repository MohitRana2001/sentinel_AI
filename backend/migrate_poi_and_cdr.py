"""
Database Migration: Person of Interest and CDR Integration
Date: November 14, 2025

This migration adds:
1. Mandatory fields to person_of_interest table (phone_number, photograph_base64)
2. Status tracking fields to cdr_records table
3. VideoPOIDetection joint table
4. CDRPOIMatch joint table
"""

from sqlalchemy import create_engine, text
from config import settings
import sys


def run_migration():
    """Run the database migration"""
    
    print("🔧 Starting database migration...")
    print(f"📊 Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    
    # Create engine
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            
            # 1. Update person_of_interest table
            print("\n1️⃣  Updating person_of_interest table...")
            
            # Add phone_number column if it doesn't exist
            try:
                conn.execute(text("""
                    ALTER TABLE person_of_interest 
                    ADD COLUMN IF NOT EXISTS phone_number VARCHAR NOT NULL DEFAULT '';
                """))
                print("   ✅ Added phone_number column")
            except Exception as e:
                print(f"   ⚠️  phone_number column: {e}")
            
            # Make photograph_base64 NOT NULL (with default)
            try:
                conn.execute(text("""
                    ALTER TABLE person_of_interest 
                    ALTER COLUMN photograph_base64 SET NOT NULL;
                """))
                print("   ✅ Made photograph_base64 mandatory")
            except Exception as e:
                print(f"   ⚠️  photograph_base64: {e}")
            
            # Make details have default value
            try:
                conn.execute(text("""
                    ALTER TABLE person_of_interest 
                    ALTER COLUMN details SET DEFAULT '{}';
                """))
                print("   ✅ Set default for details column")
            except Exception as e:
                print(f"   ⚠️  details default: {e}")
            
            # Add index on phone_number
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_poi_phone_number 
                    ON person_of_interest(phone_number);
                """))
                print("   ✅ Created index on phone_number")
            except Exception as e:
                print(f"   ⚠️  phone_number index: {e}")
            
            # 2. Update cdr_records table
            print("\n2️⃣  Updating cdr_records table...")
            
            # Add status column
            try:
                conn.execute(text("""
                    ALTER TABLE cdr_records 
                    ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'queued';
                """))
                print("   ✅ Added status column")
            except Exception as e:
                print(f"   ⚠️  status column: {e}")
            
            # Add processing_stages column
            try:
                conn.execute(text("""
                    ALTER TABLE cdr_records 
                    ADD COLUMN IF NOT EXISTS processing_stages JSON DEFAULT '{}';
                """))
                print("   ✅ Added processing_stages column")
            except Exception as e:
                print(f"   ⚠️  processing_stages column: {e}")
            
            # Add current_stage column
            try:
                conn.execute(text("""
                    ALTER TABLE cdr_records 
                    ADD COLUMN IF NOT EXISTS current_stage VARCHAR;
                """))
                print("   ✅ Added current_stage column")
            except Exception as e:
                print(f"   ⚠️  current_stage column: {e}")
            
            # Add error_message column
            try:
                conn.execute(text("""
                    ALTER TABLE cdr_records 
                    ADD COLUMN IF NOT EXISTS error_message TEXT;
                """))
                print("   ✅ Added error_message column")
            except Exception as e:
                print(f"   ⚠️  error_message column: {e}")
            
            # Add started_at column
            try:
                conn.execute(text("""
                    ALTER TABLE cdr_records 
                    ADD COLUMN IF NOT EXISTS started_at TIMESTAMP;
                """))
                print("   ✅ Added started_at column")
            except Exception as e:
                print(f"   ⚠️  started_at column: {e}")
            
            # Add completed_at column
            try:
                conn.execute(text("""
                    ALTER TABLE cdr_records 
                    ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP;
                """))
                print("   ✅ Added completed_at column")
            except Exception as e:
                print(f"   ⚠️  completed_at column: {e}")
            
            # 3. Create video_poi_detections table
            print("\n3️⃣  Creating video_poi_detections table...")
            try:
                conn.execute(text("""
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
                print("   ✅ Created video_poi_detections table")
            except Exception as e:
                print(f"   ⚠️  video_poi_detections table: {e}")
            
            # Create indexes
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_video_poi_document_id 
                    ON video_poi_detections(document_id);
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_video_poi_poi_id 
                    ON video_poi_detections(poi_id);
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_video_poi_job_id 
                    ON video_poi_detections(job_id);
                """))
                print("   ✅ Created indexes on video_poi_detections")
            except Exception as e:
                print(f"   ⚠️  video_poi_detections indexes: {e}")
            
            # 4. Create cdr_poi_matches table
            print("\n4️⃣  Creating cdr_poi_matches table...")
            try:
                conn.execute(text("""
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
                print("   ✅ Created cdr_poi_matches table")
            except Exception as e:
                print(f"   ⚠️  cdr_poi_matches table: {e}")
            
            # Create indexes
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_cdr_poi_poi_id 
                    ON cdr_poi_matches(poi_id);
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_cdr_poi_job_id 
                    ON cdr_poi_matches(job_id);
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_cdr_poi_phone 
                    ON cdr_poi_matches(phone_number);
                """))
                print("   ✅ Created indexes on cdr_poi_matches")
            except Exception as e:
                print(f"   ⚠️  cdr_poi_matches indexes: {e}")
            
            # Commit all changes
            conn.commit()
            
            print("\n✅ Migration completed successfully!")
            print("\n📋 Summary:")
            print("   • Updated person_of_interest with mandatory fields")
            print("   • Updated cdr_records with status tracking")
            print("   • Created video_poi_detections table")
            print("   • Created cdr_poi_matches table")
            print("   • Created all necessary indexes")
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        engine.dispose()


if __name__ == "__main__":
    print("=" * 60)
    print("  Person of Interest & CDR Integration Migration")
    print("=" * 60)
    
    response = input("\n⚠️  This will modify the database. Continue? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        run_migration()
    else:
        print("❌ Migration cancelled")
        sys.exit(0)
