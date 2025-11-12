"""
Database migration script to add timing fields and CDR table
Run this script to update your existing database schema
"""
from sqlalchemy import create_engine, text
from config import settings

def migrate_database():
    """Add new columns and tables for timing and CDR features"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        print("Starting database migration...")
        
        # Check if we're using PostgreSQL or SQLite
        is_postgres = settings.DATABASE_URL.startswith("postgresql")
        
        try:
            # 1. Add processing_stages column to processing_jobs
            print("Adding processing_stages column...")
            if is_postgres:
                conn.execute(text("""
                    ALTER TABLE processing_jobs 
                    ADD COLUMN IF NOT EXISTS processing_stages JSON DEFAULT '{}'
                """))
            else:
                # SQLite doesn't support JSON type, use TEXT
                conn.execute(text("""
                    ALTER TABLE processing_jobs 
                    ADD COLUMN processing_stages TEXT DEFAULT '{}'
                """))
            print("✅ processing_stages column added")
            
        except Exception as e:
            print(f"⚠️  processing_stages column may already exist: {e}")
        
        try:
            # 2. Add current_stage column to processing_jobs
            print("Adding current_stage column...")
            conn.execute(text("""
                ALTER TABLE processing_jobs 
                ADD COLUMN IF NOT EXISTS current_stage VARCHAR
            """))
            print("✅ current_stage column added")
            
        except Exception as e:
            print(f"⚠️  current_stage column may already exist: {e}")
        
        try:
            # 3. Create cdr_records table
            print("Creating cdr_records table...")
            if is_postgres:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS cdr_records (
                        id SERIAL PRIMARY KEY,
                        job_id VARCHAR NOT NULL REFERENCES processing_jobs(id),
                        original_filename VARCHAR NOT NULL,
                        file_path VARCHAR NOT NULL,
                        data JSONB NOT NULL,
                        record_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create index
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_cdr_job_id ON cdr_records(job_id)
                """))
            else:
                # SQLite version
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS cdr_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id VARCHAR NOT NULL,
                        original_filename VARCHAR NOT NULL,
                        file_path VARCHAR NOT NULL,
                        data TEXT NOT NULL,
                        record_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (job_id) REFERENCES processing_jobs(id)
                    )
                """))
                
                # Create index
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_cdr_job_id ON cdr_records(job_id)
                """))
            
            print("✅ cdr_records table created")
            
        except Exception as e:
            print(f"⚠️  cdr_records table may already exist: {e}")
        
        try:
            # 4. Create suspects table if it doesn't exist
            print("Creating suspects table (if needed)...")
            if is_postgres:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS suspects (
                        id VARCHAR PRIMARY KEY,
                        job_id VARCHAR NOT NULL REFERENCES processing_jobs(id),
                        fields JSON NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_suspects_job_id ON suspects(job_id)
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS suspects (
                        id VARCHAR PRIMARY KEY,
                        job_id VARCHAR NOT NULL,
                        fields TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (job_id) REFERENCES processing_jobs(id)
                    )
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_suspects_job_id ON suspects(job_id)
                """))
            
            print("✅ suspects table created/verified")
            
        except Exception as e:
            print(f"⚠️  suspects table may already exist: {e}")
        
        # Commit all changes
        conn.commit()
        
        print("\n" + "="*50)
        print("✅ Database migration completed successfully!")
        print("="*50)
        print("\nNew columns added to processing_jobs:")
        print("  - processing_stages (JSON)")
        print("  - current_stage (VARCHAR)")
        print("\nNew tables created:")
        print("  - cdr_records (with JSONB data)")
        print("  - suspects (verified)")
        print("\nYou can now restart your backend server.")
        print("="*50)


if __name__ == "__main__":
    print("\n" + "="*50)
    print("DATABASE MIGRATION SCRIPT")
    print("="*50 + "\n")
    
    try:
        migrate_database()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("\nPlease check your database connection and try again.")
        import traceback
        traceback.print_exc()
