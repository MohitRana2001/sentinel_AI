"""
Standalone Migration Script: Add detected_language column to documents table
Run this script directly: python add_detected_language_column.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, Column, String, text, inspect
from sqlalchemy.exc import OperationalError, ProgrammingError
from config import settings
from database import Base, SessionLocal
import models


def check_column_exists(engine, table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def add_detected_language_column():
    """Add detected_language column to documents table"""
    
    print("=" * 60)
    print("Migration: Add detected_language column to documents table")
    print("=" * 60)
    
    # Create database connection
    print(f"\n📊 Connecting to database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        # Check if column already exists
        if check_column_exists(engine, 'documents', 'detected_language'):
            print("⚠️  Column 'detected_language' already exists in 'documents' table")
            print("✅ No migration needed")
            return
        
        print("\n🔧 Adding 'detected_language' column to 'documents' table...")
        
        # Add the column using raw SQL
        with engine.connect() as conn:
            # For PostgreSQL
            if 'postgresql' in settings.DATABASE_URL:
                conn.execute(text("""
                    ALTER TABLE documents 
                    ADD COLUMN detected_language VARCHAR(10);
                """))
                conn.commit()
            # For SQLite
            else:
                conn.execute(text("""
                    ALTER TABLE documents 
                    ADD COLUMN detected_language TEXT;
                """))
                conn.commit()
        
        print("✅ Successfully added 'detected_language' column")
        
        # Verify the column was added
        if check_column_exists(engine, 'documents', 'detected_language'):
            print("✅ Verified: Column exists in database")
        else:
            print("❌ Error: Column was not added successfully")
            return
        
        # Show current table structure
        print("\n📋 Current 'documents' table columns:")
        inspector = inspect(engine)
        for col in inspector.get_columns('documents'):
            print(f"   - {col['name']}: {col['type']}")
        
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        
    except OperationalError as e:
        print(f"\n❌ Database connection error: {e}")
        print("Please check your database configuration in .env file")
        sys.exit(1)
    except ProgrammingError as e:
        print(f"\n❌ SQL error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    add_detected_language_column()
