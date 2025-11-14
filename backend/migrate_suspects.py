"""
Verification Script: Check POI and Suspects Data
This script verifies:
1. If suspects are being uploaded correctly
2. If they have photo embeddings
3. If suspects are being converted to person_of_interest table
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from database import SessionLocal, engine
import models
import json


def check_table_structure():
    """Check the structure of relevant tables"""
    print("=" * 80)
    print("📊 TABLE STRUCTURE VERIFICATION")
    print("=" * 80)
    
    inspector = inspect(engine)
    
    # Check person_of_interest table
    print("\n1️⃣  person_of_interest table:")
    if 'person_of_interest' in inspector.get_table_names():
        columns = inspector.get_columns('person_of_interest')
        for col in columns:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            print(f"   - {col['name']}: {col['type']} ({nullable})")
    else:
        print("   ❌ Table does not exist!")
    
    # Check suspects table
    print("\n2️⃣  suspects table:")
    if 'suspects' in inspector.get_table_names():
        columns = inspector.get_columns('suspects')
        for col in columns:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            print(f"   - {col['name']}: {col['type']} ({nullable})")
    else:
        print("   ❌ Table does not exist!")
    
    # Check suspect_fields table
    print("\n3️⃣  suspect_fields table:")
    if 'suspect_fields' in inspector.get_table_names():
        columns = inspector.get_columns('suspect_fields')
        for col in columns:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            print(f"   - {col['name']}: {col['type']} ({nullable})")
    else:
        print("   ❌ Table does not exist!")


def check_poi_data():
    """Check data in person_of_interest table"""
    print("\n" + "=" * 80)
    print("🔍 PERSON OF INTEREST DATA CHECK")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        # Count POIs
        poi_count = db.query(models.PersonOfInterest).count()
        print(f"\n📊 Total POIs in database: {poi_count}")
        
        if poi_count == 0:
            print("⚠️  No POI records found!")
            return
        
        # Get sample POIs
        pois = db.query(models.PersonOfInterest).limit(5).all()
        
        print(f"\n📋 Sample POI Records (showing {len(pois)}):")
        print("-" * 80)
        
        for idx, poi in enumerate(pois, 1):
            print(f"\n{idx}. POI ID: {poi.id}")
            print(f"   Name: {poi.name}")
            print(f"   Phone: {poi.phone_number}")
            print(f"   Photo (base64 length): {len(poi.photograph_base64) if poi.photograph_base64 else 0}")
            print(f"   Details: {json.dumps(poi.details, indent=6) if poi.details else '{}'}")
            
            # Check embeddings
            has_details_embedding = poi.details_embedding is not None
            has_photo_embedding = poi.photograph_embedding is not None
            
            print(f"   Details Embedding: {'✅ Present' if has_details_embedding else '❌ Missing'}")
            if has_details_embedding:
                print(f"      - Length: {len(poi.details_embedding)}")
            
            print(f"   Photo Embedding: {'✅ Present' if has_photo_embedding else '❌ Missing'}")
            if has_photo_embedding:
                print(f"      - Length: {len(poi.photograph_embedding)}")
            
            print(f"   Created: {poi.created_at}")
        
        # Check embeddings statistics
        print("\n" + "=" * 80)
        print("📊 EMBEDDING STATISTICS")
        print("=" * 80)
        
        pois_with_details_embedding = db.query(models.PersonOfInterest).filter(
            models.PersonOfInterest.details_embedding.isnot(None)
        ).count()
        
        pois_with_photo_embedding = db.query(models.PersonOfInterest).filter(
            models.PersonOfInterest.photograph_embedding.isnot(None)
        ).count()
        
        print(f"\nPOIs with Details Embedding: {pois_with_details_embedding}/{poi_count} ({(pois_with_details_embedding/poi_count*100):.1f}%)")
        print(f"POIs with Photo Embedding: {pois_with_photo_embedding}/{poi_count} ({(pois_with_photo_embedding/poi_count*100):.1f}%)")
        
        if pois_with_photo_embedding == 0:
            print("\n⚠️  WARNING: No POIs have photo embeddings!")
            print("   Photo embeddings are required for face recognition in videos.")
            print("   Check if face recognition is properly configured.")
        
    finally:
        db.close()


def check_suspects_data():
    """Check data in suspects table"""
    print("\n" + "=" * 80)
    print("🔍 SUSPECTS DATA CHECK")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        # Count suspects
        suspect_count = db.query(models.Suspect).count()
        print(f"\n📊 Total Suspects in database: {suspect_count}")
        
        if suspect_count == 0:
            print("⚠️  No suspect records found!")
            print("   Suspects are uploaded with jobs but stored separately from POI.")
            return
        
        # Get sample suspects with their fields
        suspects = db.query(models.Suspect).limit(5).all()
        
        print(f"\n📋 Sample Suspect Records (showing {len(suspects)}):")
        print("-" * 80)
        
        for idx, suspect in enumerate(suspects, 1):
            print(f"\n{idx}. Suspect ID: {suspect.id}")
            print(f"   Job ID: {suspect.job_id}")
            print(f"   Created: {suspect.created_at}")
            
            # Get suspect fields
            fields = db.query(models.SuspectField).filter(
                models.SuspectField.suspect_id == suspect.id
            ).all()
            
            print(f"   Fields ({len(fields)}):")
            for field in fields:
                print(f"      - {field.key}: {field.value}")
        
        # Check if suspects have photos
        print("\n" + "=" * 80)
        print("📷 PHOTO DATA IN SUSPECTS")
        print("=" * 80)
        
        suspects_with_photo = db.query(models.Suspect).join(
            models.SuspectField
        ).filter(
            models.SuspectField.key.in_(['photo', 'photograph', 'image', 'photo_base64'])
        ).count()
        
        print(f"\nSuspects with photo fields: {suspects_with_photo}/{suspect_count}")
        
        if suspects_with_photo == 0:
            print("⚠️  No suspects have photo data!")
            print("   Check the frontend upload to ensure photos are being sent.")
        
    finally:
        db.close()


def check_conversion_status():
    """Check if suspects are being converted to POI"""
    print("\n" + "=" * 80)
    print("🔄 SUSPECTS → POI CONVERSION CHECK")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        suspect_count = db.query(models.Suspect).count()
        poi_count = db.query(models.PersonOfInterest).count()
        
        print(f"\nSuspects in database: {suspect_count}")
        print(f"POIs in database: {poi_count}")
        
        if suspect_count > 0 and poi_count == 0:
            print("\n⚠️  WARNING: Suspects exist but no POIs!")
            print("   Suspects are NOT being automatically converted to POI.")
            print("   You need to either:")
            print("   1. Create a migration/script to convert suspects to POI")
            print("   2. Or use the POI API endpoint to manually create POIs")
        
        elif suspect_count == 0 and poi_count > 0:
            print("\n✅ POIs exist (created via API)")
            print("   No suspects in database - POIs were created directly.")
        
        elif suspect_count > 0 and poi_count > 0:
            print("\n📊 Both suspects and POIs exist")
            print("   Check if they're linked or separate entities.")
        
        else:
            print("\n⚠️  No suspects or POIs in database")
            print("   Upload some data to test the flow.")
        
    finally:
        db.close()


def provide_recommendations():
    """Provide recommendations based on findings"""
    print("\n" + "=" * 80)
    print("💡 RECOMMENDATIONS")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        suspect_count = db.query(models.Suspect).count()
        poi_count = db.query(models.PersonOfInterest).count()
        pois_with_photo_embedding = db.query(models.PersonOfInterest).filter(
            models.PersonOfInterest.photograph_embedding.isnot(None)
        ).count()
        
        print("\n1. Suspects Upload:")
        if suspect_count == 0:
            print("   ⚠️  No suspects found. Upload suspects via the job upload endpoint.")
        else:
            print(f"   ✅ {suspect_count} suspects found in database.")
        
        print("\n2. POI Creation:")
        if poi_count == 0:
            print("   ⚠️  No POIs found. Create POIs using:")
            print("      - POST /api/v1/person-of-interest endpoint")
            print("      - Or create a script to convert suspects to POI")
        else:
            print(f"   ✅ {poi_count} POIs found in database.")
        
        print("\n3. Photo Embeddings:")
        if pois_with_photo_embedding == 0:
            print("   ❌ No photo embeddings found!")
            print("      - Photo embeddings are currently set to None (TODO in code)")
            print("      - Need to integrate face recognition library")
            print("      - Check main.py around line 672 and 732")
        else:
            print(f"   ✅ {pois_with_photo_embedding} POIs have photo embeddings.")
        
        print("\n4. Required Actions:")
        if suspect_count > 0 and poi_count == 0:
            print("   🔧 Create a migration script to convert suspects to POI")
        if poi_count > 0 and pois_with_photo_embedding == 0:
            print("   🔧 Implement photo embedding generation (face recognition)")
        
    finally:
        db.close()


def main():
    """Main verification function"""
    print("\n" + "=" * 80)
    print("🔍 POI AND SUSPECTS VERIFICATION SCRIPT")
    print("=" * 80)
    
    try:
        check_table_structure()
        check_poi_data()
        check_suspects_data()
        check_conversion_status()
        provide_recommendations()
        
        print("\n" + "=" * 80)
        print("✅ VERIFICATION COMPLETE")
        print("=" * 80)
        print()
        
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
