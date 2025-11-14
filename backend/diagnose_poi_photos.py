"""
Diagnostic Script: Check POI photograph and embedding status
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
import models
import base64
from io import BytesIO
from PIL import Image


def diagnose_poi_photos():
    """Diagnose POI photograph issues"""
    
    print("=" * 70)
    print("POI Photograph Diagnostic Report")
    print("=" * 70)
    
    db = SessionLocal()
    
    try:
        # Get all POIs
        pois = db.query(models.PersonOfInterest).all()
        
        print(f"\n📊 Total POIs: {len(pois)}\n")
        
        if not pois:
            print("⚠️ No POIs found in database")
            return
        
        stats = {
            'total': len(pois),
            'has_photo': 0,
            'has_text_embedding': 0,
            'has_photo_embedding': 0,
            'photo_valid': 0,
            'photo_invalid': 0,
            'photo_empty': 0,
        }
        
        print("POI Details:")
        print("-" * 70)
        
        for idx, poi in enumerate(pois, 1):
            print(f"\n[{idx}] {poi.name}")
            print(f"    ID: {poi.id}")
            print(f"    Phone: {poi.phone_number}")
            
            # Check photograph
            if poi.photograph_base64:
                stats['has_photo'] += 1
                photo_len = len(poi.photograph_base64)
                print(f"    📸 Photograph: Yes ({photo_len:,} chars)")
                
                # Try to validate photo
                try:
                    photo_data = poi.photograph_base64
                    if photo_data.startswith('data:image'):
                        photo_data = photo_data.split(',', 1)[1]
                    
                    image_bytes = base64.b64decode(photo_data)
                    image = Image.open(BytesIO(image_bytes))
                    image.verify()
                    
                    stats['photo_valid'] += 1
                    print(f"    ✅ Photo valid: {image.format} {image.size}")
                    
                except Exception as e:
                    stats['photo_invalid'] += 1
                    print(f"    ❌ Photo invalid: {e}")
            else:
                stats['photo_empty'] += 1
                print(f"    📸 Photograph: None")
            
            # Check text embedding
            if poi.details_embedding:
                stats['has_text_embedding'] += 1
                embedding_dim = len(poi.details_embedding) if hasattr(poi.details_embedding, '__len__') else 0
                print(f"    📝 Text embedding: Yes ({embedding_dim} dims)")
            else:
                print(f"    📝 Text embedding: None")
            
            # Check photo embedding
            if poi.photograph_embedding:
                stats['has_photo_embedding'] += 1
                embedding_dim = len(poi.photograph_embedding) if hasattr(poi.photograph_embedding, '__len__') else 0
                print(f"    👤 Photo embedding: Yes ({embedding_dim} dims)")
            else:
                print(f"    👤 Photo embedding: None")
            
            # Show details
            if poi.details:
                print(f"    📋 Details: {len(poi.details)} fields")
                for key, value in poi.details.items():
                    if isinstance(value, list):
                        print(f"       - {key}: {len(value)} items")
                    else:
                        preview = str(value)[:50]
                        print(f"       - {key}: {preview}")
        
        # Summary
        print("\n" + "=" * 70)
        print("Summary Statistics")
        print("=" * 70)
        print(f"Total POIs:                {stats['total']}")
        print(f"With photographs:          {stats['has_photo']} ({stats['has_photo']/stats['total']*100:.1f}%)")
        print(f"  - Valid photos:          {stats['photo_valid']}")
        print(f"  - Invalid photos:        {stats['photo_invalid']}")
        print(f"  - Empty photos:          {stats['photo_empty']}")
        print(f"With text embeddings:      {stats['has_text_embedding']} ({stats['has_text_embedding']/stats['total']*100:.1f}%)")
        print(f"With photo embeddings:     {stats['has_photo_embedding']} ({stats['has_photo_embedding']/stats['total']*100:.1f}%)")
        
        # Issues
        print("\n" + "=" * 70)
        print("Issues Found")
        print("=" * 70)
        
        issues = []
        
        if stats['photo_invalid'] > 0:
            issues.append(f"❌ {stats['photo_invalid']} POI(s) have invalid photographs")
        
        if stats['photo_empty'] > 0:
            issues.append(f"⚠️  {stats['photo_empty']} POI(s) have no photographs")
        
        missing_text_embeddings = stats['total'] - stats['has_text_embedding']
        if missing_text_embeddings > 0:
            issues.append(f"⚠️  {missing_text_embeddings} POI(s) missing text embeddings")
        
        missing_photo_embeddings = stats['has_photo'] - stats['has_photo_embedding']
        if missing_photo_embeddings > 0:
            issues.append(f"⚠️  {missing_photo_embeddings} POI(s) with photos but missing photo embeddings")
        
        if issues:
            for issue in issues:
                print(issue)
        else:
            print("✅ No issues found!")
        
        # Recommendations
        print("\n" + "=" * 70)
        print("Recommendations")
        print("=" * 70)
        
        if stats['photo_invalid'] > 0:
            print("1. Fix invalid photographs:")
            print("   - Re-upload photos for POIs with invalid images")
        
        if missing_photo_embeddings > 0:
            print("2. Generate missing photo embeddings:")
            print("   python migrate_photo_embeddings.py")
        
        if missing_text_embeddings > 0:
            print("3. Generate missing text embeddings:")
            print("   - This should not happen for new POIs")
            print("   - Check POI creation endpoint")
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    diagnose_poi_photos()
