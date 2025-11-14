"""
Verify database migration for per-artifact status and case management

Run this script after running the migration to verify all changes were applied correctly.

Usage:
    python migrations/verify_migration.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from database import engine, SessionLocal

def verify_migration():
    """Verify that all migration changes were applied"""
    
    print("🔍 Verifying database migration...")
    print("=" * 60)
    
    db = SessionLocal()
    inspector = inspect(engine)
    
    errors = []
    warnings = []
    
    try:
        # 1. Check processing_jobs table
        print("\n📋 Checking processing_jobs table...")
        job_columns = {col['name']: col for col in inspector.get_columns('processing_jobs')}
        
        required_job_columns = ['case_name', 'parent_job_id']
        for col_name in required_job_columns:
            if col_name in job_columns:
                print(f"   ✅ {col_name}: {job_columns[col_name]['type']}")
            else:
                errors.append(f"Missing column 'processing_jobs.{col_name}'")
                print(f"   ❌ {col_name}: MISSING")
        
        # Check index on case_name
        indexes = inspector.get_indexes('processing_jobs')
        case_name_indexed = any('case_name' in str(idx.get('column_names', [])) for idx in indexes)
        if case_name_indexed:
            print(f"   ✅ Index on case_name exists")
        else:
            warnings.append("Index on case_name not found (may affect performance)")
            print(f"   ⚠️  Index on case_name: MISSING (non-critical)")
        
        # 2. Check documents table
        print("\n📄 Checking documents table...")
        doc_columns = {col['name']: col for col in inspector.get_columns('documents')}
        
        required_doc_columns = [
            'status',
            'processing_stages',
            'current_stage',
            'error_message',
            'started_at',
            'completed_at'
        ]
        
        for col_name in required_doc_columns:
            if col_name in doc_columns:
                print(f"   ✅ {col_name}: {doc_columns[col_name]['type']}")
            else:
                errors.append(f"Missing column 'documents.{col_name}'")
                print(f"   ❌ {col_name}: MISSING")
        
        # 3. Test data integrity
        print("\n🔬 Testing data integrity...")
        
        # Check if case_name accepts NULL
        result = db.execute(text("""
            SELECT column_name, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'processing_jobs' 
            AND column_name = 'case_name';
        """)).fetchone()
        
        if result and result[1] == 'YES':
            print("   ✅ case_name allows NULL (correct)")
        else:
            errors.append("case_name should allow NULL values")
            print("   ❌ case_name nullable constraint incorrect")
        
        # Check if parent_job_id has foreign key
        fks = inspector.get_foreign_keys('processing_jobs')
        parent_fk_exists = any(
            'parent_job_id' in fk.get('constrained_columns', []) 
            for fk in fks
        )
        
        if parent_fk_exists:
            print("   ✅ parent_job_id has foreign key constraint")
        else:
            warnings.append("parent_job_id foreign key not found (may affect referential integrity)")
            print("   ⚠️  parent_job_id foreign key: MISSING (non-critical)")
        
        # 4. Test sample queries
        print("\n🧪 Testing sample queries...")
        
        # Test case name query
        try:
            result = db.execute(text("""
                SELECT COUNT(DISTINCT case_name) as case_count
                FROM processing_jobs
                WHERE case_name IS NOT NULL;
            """)).fetchone()
            print(f"   ✅ Case query works: {result[0]} cases found")
        except Exception as e:
            errors.append(f"Case query failed: {e}")
            print(f"   ❌ Case query failed: {e}")
        
        # Test artifact status query
        try:
            result = db.execute(text("""
                SELECT COUNT(*) as doc_count
                FROM documents
                WHERE status IS NOT NULL;
            """)).fetchone()
            print(f"   ✅ Artifact status query works: {result[0]} documents with status")
        except Exception as e:
            errors.append(f"Artifact status query failed: {e}")
            print(f"   ❌ Artifact status query failed: {e}")
        
        # 5. Summary
        print("\n" + "=" * 60)
        print("📊 VERIFICATION SUMMARY")
        print("=" * 60)
        
        if not errors and not warnings:
            print("✅ ALL CHECKS PASSED!")
            print("\nMigration completed successfully.")
            print("You can now use:")
            print("  - Case management features")
            print("  - Per-artifact status tracking")
            print("  - Real-time processing stage updates")
            return True
        
        if errors:
            print("\n❌ ERRORS FOUND:")
            for error in errors:
                print(f"  - {error}")
            print("\n⚠️  Migration may not have completed successfully.")
            print("   Please run the migration script again:")
            print("   python migrations/add_artifact_status_and_case_name.py")
            return False
        
        if warnings:
            print("\n⚠️  WARNINGS:")
            for warning in warnings:
                print(f"  - {warning}")
            print("\n✅ Migration functional but with minor issues.")
            print("   System will work but may have reduced performance.")
            return True
        
    except Exception as e:
        print(f"\n❌ Verification failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def print_schema_info():
    """Print detailed schema information for debugging"""
    print("\n" + "=" * 60)
    print("📋 DETAILED SCHEMA INFORMATION")
    print("=" * 60)
    
    inspector = inspect(engine)
    
    print("\n🏢 Processing Jobs Table:")
    for col in inspector.get_columns('processing_jobs'):
        print(f"  {col['name']:<25} {str(col['type']):<20} nullable={col['nullable']}")
    
    print("\n📄 Documents Table:")
    for col in inspector.get_columns('documents'):
        print(f"  {col['name']:<25} {str(col['type']):<20} nullable={col['nullable']}")
    
    print("\n🔗 Foreign Keys:")
    for fk in inspector.get_foreign_keys('processing_jobs'):
        print(f"  {fk['name']}: {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
    
    for fk in inspector.get_foreign_keys('documents'):
        print(f"  {fk['name']}: {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
    
    print("\n🔍 Indexes:")
    print("  Processing Jobs:")
    for idx in inspector.get_indexes('processing_jobs'):
        print(f"    {idx['name']}: {idx['column_names']}")
    
    print("  Documents:")
    for idx in inspector.get_indexes('documents'):
        print(f"    {idx['name']}: {idx['column_names']}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify database migration')
    parser.add_argument('--detailed', action='store_true', help='Show detailed schema information')
    args = parser.parse_args()
    
    success = verify_migration()
    
    if args.detailed:
        print_schema_info()
    
    sys.exit(0 if success else 1)
