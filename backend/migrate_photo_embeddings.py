"""
Migration Script: Generate photo embeddings for existing POI records
Runs face_recognition on all POIs that have photographs but missing photo embeddings
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
import models
from photo_embedding import generate_photo_embedding
from sqlalchemy import func


def migrate_photo_embeddings():
    """Generate photo embeddings for all POIs missing them"""
    
    print("=" * 70)
    print("POI Photo Embedding Migration")
    print("=" * 70)
    
    db = SessionLocal()
    
    try:
        # Count total POIs
        total_pois = db.query(models.PersonOfInterest).count()
        print(f"\n📊 Total POIs in database: {total_pois}")
        
        # Find POIs without photo embeddings
        pois_without_embeddings = db.query(models.PersonOfInterest).filter(
            models.PersonOfInterest.photograph_embedding == None
        ).all()
        
        print(f"📊 POIs missing photo embeddings: {len(pois_without_embeddings)}")
        
        if not pois_without_embeddings:
            print("\n✅ All POIs already have photo embeddings!")
            return
        
        print(f"\n🔧 Processing {len(pois_without_embeddings)} POIs...\n")
        
        success_count = 0
        no_face_count = 0
        error_count = 0
        
        for idx, poi in enumerate(pois_without_embeddings, 1):
            print(f"[{idx}/{len(pois_without_embeddings)}] Processing: {poi.name}")
            
            try:
                # Check if photograph exists
                if not poi.photograph_base64 or not poi.photograph_base64.strip():
                    print(f"  ⚠️ No photograph available, skipping")
                    no_face_count += 1
                    continue
                
                # Generate photo embedding
                embedding = generate_photo_embedding(poi.photograph_base64)
                
                if embedding:
                    # Update POI with photo embedding
                    poi.photograph_embedding = embedding
                    db.commit()
                    success_count += 1
                    print(f"  ✅ Photo embedding generated ({len(embedding)} dimensions)")
                else:
                    no_face_count += 1
                    print(f"  ⚠️ No face detected in photograph")
                    
            except Exception as e:
                error_count += 1
                print(f"  ❌ Error: {e}")
                db.rollback()
        
        print("\n" + "=" * 70)
        print("Migration Summary")
        print("=" * 70)
        print(f"✅ Successfully generated: {success_count}")
        print(f"⚠️  No face detected: {no_face_count}")
        print(f"❌ Errors: {error_count}")
        print(f"📊 Total processed: {len(pois_without_embeddings)}")
        
        # Show current stats
        pois_with_embeddings = db.query(models.PersonOfInterest).filter(
            models.PersonOfInterest.photograph_embedding != None
        ).count()
        
        print(f"\n📊 Current Stats:")
        print(f"   POIs with photo embeddings: {pois_with_embeddings}/{total_pois}")
        print(f"   Coverage: {pois_with_embeddings/total_pois*100:.1f}%")
        
        print("\n" + "=" * 70)
        print("✅ Migration completed!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    migrate_photo_embeddings()
