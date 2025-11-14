"""
Migration: Fix photo embedding dimension from 1024 to 128

This migration updates the photograph_embedding column in person_of_interest table
to use 128 dimensions (face_recognition standard) instead of 1024.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATABASE_URL

def migrate():
    """Run the migration"""
    engine = create_engine(DATABASE_URL)
    
    print("🔄 Starting migration: Fix photo embedding dimension...")
    
    with engine.connect() as conn:
        try:
            # Check if table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'person_of_interest'
                );
            """))
            table_exists = result.scalar()
            
            if not table_exists:
                print("✅ Table 'person_of_interest' does not exist yet. Migration not needed.")
                return
            
            # Check current dimension
            result = conn.execute(text("""
                SELECT atttypmod 
                FROM pg_attribute 
                WHERE attrelid = 'person_of_interest'::regclass 
                AND attname = 'photograph_embedding';
            """))
            current_dim = result.scalar()
            
            if current_dim:
                # atttypmod stores dimension + 4, so actual dimension is atttypmod - 4
                actual_dim = current_dim - 4
                print(f"📊 Current photograph_embedding dimension: {actual_dim}")
                
                if actual_dim == 128:
                    print("✅ Dimension is already correct (128). No migration needed.")
                    return
            
            print("🔧 Dropping old photograph_embedding column...")
            conn.execute(text("""
                ALTER TABLE person_of_interest 
                DROP COLUMN IF EXISTS photograph_embedding;
            """))
            conn.commit()
            
            print("➕ Adding new photograph_embedding column with dimension 128...")
            conn.execute(text("""
                ALTER TABLE person_of_interest 
                ADD COLUMN photograph_embedding vector(128);
            """))
            conn.commit()
            
            print("🔍 Dropping old index if exists...")
            conn.execute(text("""
                DROP INDEX IF EXISTS ix_poi_photo_embedding;
            """))
            conn.commit()
            
            print("📇 Creating new index...")
            conn.execute(text("""
                CREATE INDEX ix_poi_photo_embedding 
                ON person_of_interest 
                USING ivfflat (photograph_embedding vector_cosine_ops) 
                WITH (lists = 100);
            """))
            conn.commit()
            
            print("✅ Migration completed successfully!")
            print("⚠️  Note: All existing photograph embeddings have been cleared.")
            print("   POIs will need to be re-processed to generate new face encodings.")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            conn.rollback()
            raise

def rollback():
    """Rollback the migration"""
    engine = create_engine(DATABASE_URL)
    
    print("🔄 Rolling back migration: Fix photo embedding dimension...")
    
    with engine.connect() as conn:
        try:
            print("🔧 Dropping photograph_embedding column...")
            conn.execute(text("""
                ALTER TABLE person_of_interest 
                DROP COLUMN IF EXISTS photograph_embedding;
            """))
            conn.commit()
            
            print("➕ Adding photograph_embedding column with dimension 1024...")
            conn.execute(text("""
                ALTER TABLE person_of_interest 
                ADD COLUMN photograph_embedding vector(1024);
            """))
            conn.commit()
            
            print("📇 Creating index...")
            conn.execute(text("""
                CREATE INDEX ix_poi_photo_embedding 
                ON person_of_interest 
                USING ivfflat (photograph_embedding vector_cosine_ops) 
                WITH (lists = 100);
            """))
            conn.commit()
            
            print("✅ Rollback completed successfully!")
            
        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix photo embedding dimension migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()
    
    if args.rollback:
        rollback()
    else:
        migrate()
