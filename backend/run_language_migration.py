#!/usr/bin/env python3
"""
Quick migration script to add detected_language column to documents table
Run this script to apply the language detection migration
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, engine
from sqlalchemy import text
import models


def check_column_exists():
    """Check if detected_language column already exists"""
    db = SessionLocal()
    try:
        # Try to query the column
        result = db.execute(text("SELECT detected_language FROM documents LIMIT 1"))
        print("✅ Column 'detected_language' already exists")
        return True
    except Exception as e:
        if "column" in str(e).lower() and "does not exist" in str(e).lower():
            print("ℹ️  Column 'detected_language' does not exist yet")
            return False
        else:
            print(f"⚠️  Error checking column: {e}")
            return False
    finally:
        db.close()


def add_detected_language_column():
    """Add detected_language column to documents table"""
    db = SessionLocal()
    try:
        print("\n🔧 Adding 'detected_language' column to documents table...")
        
        # Add column
        db.execute(text("ALTER TABLE documents ADD COLUMN detected_language VARCHAR(10)"))
        db.commit()
        
        print("✅ Successfully added 'detected_language' column")
        print("   - Column type: VARCHAR(10)")
        print("   - Nullable: True")
        print("   - Default: NULL")
        
        return True
        
    except Exception as e:
        print(f"❌ Error adding column: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def verify_migration():
    """Verify the migration was successful"""
    db = SessionLocal()
    try:
        # Check if we can query the column
        result = db.execute(text("SELECT COUNT(*) as count FROM documents"))
        count = result.fetchone()[0]
        
        # Try to select with the new column
        result = db.execute(text("SELECT id, original_filename, detected_language FROM documents LIMIT 5"))
        rows = result.fetchall()
        
        print("\n📊 Verification:")
        print(f"   - Total documents: {count}")
        print(f"   - Sample documents with detected_language column:")
        
        if rows:
            for row in rows:
                doc_id, filename, lang = row
                print(f"     • ID {doc_id}: {filename} (language: {lang or 'NULL'})")
        else:
            print("     (No documents in database yet)")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False
    finally:
        db.close()


def main():
    """Main migration runner"""
    print("=" * 70)
    print("Language Detection Migration")
    print("Add 'detected_language' column to documents table")
    print("=" * 70)
    
    # Check if column already exists
    if check_column_exists():
        print("\n⏭️  Migration already applied, skipping")
        verify_migration()
        return
    
    # Apply migration
    print("\n🚀 Applying migration...")
    success = add_detected_language_column()
    
    if success:
        print("\n✅ Migration completed successfully!")
        verify_migration()
        print("\n" + "=" * 70)
        print("Next steps:")
        print("1. Restart document processor: docker-compose restart document_processor")
        print("2. Restart video processor: docker-compose restart video_processor")
        print("3. Upload new documents/videos to test language detection")
        print("=" * 70)
    else:
        print("\n❌ Migration failed. Please check the error messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
