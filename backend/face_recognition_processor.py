"""
Face Recognition Processor
Matches faces in video frames against Person of Interest (POI) database
Integrates with video processing pipeline for automated POI detection
"""
import cv2
import face_recognition
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from database import SessionLocal
import models
from storage_config import storage_manager
import tempfile
import os
import base64
import io
from PIL import Image


class FaceRecognitionProcessor:
    """
    Process video frames to detect and match faces against POI database
    """
    
    def __init__(self):
        """Initialize face recognition processor with default settings"""
        self.tolerance = 0.50  # Face matching tolerance (0.0-1.0, lower = stricter)
        self.frame_skip_seconds = 0.3  # Process 1 frame every 0.3 seconds
        print(f"FaceRecognitionProcessor initialized (tolerance={self.tolerance})")
    
    def load_poi_faces(self, db) -> Tuple[List[np.ndarray], List[Dict]]:
        """
        Load all POI face encodings from database
        
        Args:
            db: Database session
        
        Returns:
            Tuple of (face_encodings, poi_metadata)
            - face_encodings: List of numpy arrays representing face embeddings
            - poi_metadata: List of POI info dicts aligned with encodings
        """
        print("Loading POI face encodings from database...")
        
        pois = db.query(models.PersonOfInterest).all()

        if not pois:
            print("No POIs found in database")
            return [], []
        
        face_encodings = []
        poi_metadata = []
        
        for poi in pois:
            try:
                print(f"{poi}")
                # Decode base64 photograph
                photo_data = poi.photograph_base64
                
                # Skip if no photo
                if not photo_data or not photo_data.strip():
                    print(f"  ⚠️ No photograph for: {poi.name}")
                    continue
                
                # Handle data URL format (e.g., "data:image/jpeg;base64,...")
                if photo_data.startswith('data:image'):
                    photo_data = photo_data.split(',', 1)[1]
                
                # Decode base64 to bytes
                try:
                    image_bytes = base64.b64decode(photo_data)
                except Exception as decode_err:
                    print(f"  ❌ Base64 decode error for {poi.name}: {decode_err}")
                    continue
                
                # Open image
                try:
                    image = Image.open(io.BytesIO(image_bytes))
                except Exception as img_err:
                    print(f"  ❌ Image open error for {poi.name}: {img_err}")
                    print(f"     Image bytes length: {len(image_bytes)}")
                    print(f"     First 20 bytes: {image_bytes[:20]}")
                    continue
                
                # Convert to RGB numpy array (required by face_recognition)
                image_np = np.array(image.convert('RGB'))
                
                # Extract face encoding
                encodings = face_recognition.face_encodings(image_np)
                
                if encodings:
                    face_encodings.append(encodings[0])
                    poi_metadata.append({
                        'id': poi.id,
                        'name': poi.name,
                        'phone_number': poi.phone_number,
                        'details': poi.details or {}
                    })
                    print(f"Loaded face encoding for: {poi.name}")
                else:
                    print(f"No face detected in photo for: {poi.name}")
                    
            except Exception as e:
                print(f"Error loading face for {poi.name}: {e}")
                continue
        
        print(f"Loaded {len(face_encodings)} POI face encodings from {len(pois)} total POIs")
        return face_encodings, poi_metadata
    
    def process_video_for_faces(
        self, 
        video_path: str, 
        poi_encodings: List[np.ndarray],
        poi_metadata: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Process video and detect POI faces in frames
        
        Args:
            video_path: Path to video file
            poi_encodings: List of POI face encodings
            poi_metadata: List of POI metadata (aligned with encodings)
        
        Returns:
            List of detection dictionaries containing:
            - poi_id: POI database ID
            - poi_name: POI name
            - poi_phone: POI phone number
            - frame_number: Frame number where detected
            - timestamp: Time in seconds where detected
            - face_location: Bounding box coordinates {top, right, bottom, left}
        """
        print(f"Processing video for face recognition: {video_path}")
        
        if not poi_encodings:
            print("No POI encodings provided, skipping face recognition")
            return []
        
        # Open video file
        video = cv2.VideoCapture(video_path)
        
        if not video.isOpened():
            print(f"Failed to open video: {video_path}")
            return []
        
        # Get video properties
        fps = int(video.get(cv2.CAP_PROP_FPS))
        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        frame_skip_interval = max(1, int(fps * self.frame_skip_seconds))
        
        print(f"Video Properties:")
        print(f"   - Total frames: {total_frames}")
        print(f"   - FPS: {fps}")
        print(f"   - Duration: {duration:.1f}s")
        print(f"   - Processing interval: 1 frame every {self.frame_skip_seconds}s ({frame_skip_interval} frames)")
        
        detections = []
        frame_number = 0
        processed_count = 0
        
        while True:
            # Set frame position
            video.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            # Read frame
            ret, frame = video.read()
            
            if not ret:
                break
            
            # Process this frame
            if frame_number % frame_skip_interval == 0:
                processed_count += 1
                timestamp = frame_number / fps if fps > 0 else 0
                
                # Convert BGR (OpenCV format) to RGB (face_recognition format)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Detect all faces in this frame
                face_locations = face_recognition.face_locations(rgb_frame, model='hog')  # 'hog' is faster, 'cnn' is more accurate
                
                if face_locations:
                    if processed_count % 10 == 0 or len(face_locations) > 0:  # Log every 10th frame or when faces found
                        print(f"Frame {frame_number} (t={timestamp:.1f}s): Found {len(face_locations)} face(s)")
                    
                    # Encode all faces found in this frame
                    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                    
                    # Compare each detected face with all POIs
                    for face_encoding, face_location in zip(face_encodings, face_locations):
                        # Compare this face against all known POI faces
                        matches = face_recognition.compare_faces(
                            poi_encodings,
                            face_encoding,
                            tolerance=self.tolerance
                        )
                        
                        # Calculate face distances (lower = better match)
                        face_distances = face_recognition.face_distance(poi_encodings, face_encoding)
                        
                        # Find best match
                        for idx, (is_match, distance) in enumerate(zip(matches, face_distances)):
                            if is_match:
                                poi = poi_metadata[idx]
                                top, right, bottom, left = face_location
                                
                                # Calculate confidence (1 - distance)
                                confidence = 1.0 - distance
                                
                                detection = {
                                    'poi_id': poi['id'],
                                    'poi_name': poi['name'],
                                    'poi_phone': poi['phone_number'],
                                    'frame_number': frame_number,
                                    'timestamp': timestamp,
                                    'confidence': float(confidence),
                                    'face_location': {
                                        'top': int(top),
                                        'right': int(right),
                                        'bottom': int(bottom),
                                        'left': int(left)
                                    }
                                }
                                
                                detections.append(detection)
                                print(f"POI MATCH: {poi['name']} at {timestamp:.1f}s (confidence: {confidence:.2f})")
            
            frame_number += frame_skip_interval
            
            # Safety check: don't process beyond total frames
            if frame_number >= total_frames:
                break
        
        video.release()
        
        print(f"Face recognition complete: {len(detections)} POI detection(s) in {processed_count} processed frames")
        
        # Deduplicate detections (same POI in consecutive frames)
        if detections:
            unique_pois = set(d['poi_name'] for d in detections)
            print(f"Unique POIs detected: {len(unique_pois)}")
            for poi_name in sorted(unique_pois):
                poi_detections = [d for d in detections if d['poi_name'] == poi_name]
                print(f"   - {poi_name}: {len(poi_detections)} appearance(s)")
        
        return detections
    
    def create_video_poi_detections(
        self,
        db,
        document_id: int,
        detections: List[Dict[str, Any]]
    ):
        """
        Create VideoPOIDetection records in database
        
        Args:
            db: Database session
            document_id: Video document ID
            detections: List of POI detections from process_video_for_faces
        """
        if not detections:
            print("No detections to save")
            return
        
        print(f"Creating {len(detections)} VideoPOIDetection records...")
        
        for detection in detections:
            video_poi = models.VideoPOIDetection(
                document_id=document_id,
                poi_id=detection['poi_id'],
                frame_number=detection['frame_number'],
                timestamp=detection['timestamp'],
                face_location=detection['face_location'],
                confidence_score=detection.get('confidence', 0.95)
            )
            db.add(video_poi)
        
        try:
            db.commit()
            print(f"Successfully created {len(detections)} VideoPOIDetection records")
        except Exception as e:
            print(f"Error saving detections: {e}")
            db.rollback()
            raise
    
    def process_video_document(self, db, document_id: int, video_gcs_path: str):
        """
        Complete face recognition workflow for a video document
        
        This is the main entry point for face recognition integration.
        Call this from video processor after video is uploaded.
        
        Args:
            db: Database session
            document_id: Video document ID from database
            video_gcs_path: GCS path to video file
        """
        print(f"\n{'='*60}")
        print(f"Starting Face Recognition for Document {document_id}")
        print(f"Video: {video_gcs_path}")
        print(f"{'='*60}\n")
        
        # Load all POI faces from database
        poi_encodings, poi_metadata = self.load_poi_faces(db)
        
        if not poi_encodings:
            print("No POI faces available in database, skipping face recognition")
            print("To use face recognition, add POIs with photographs in the dashboard")
            return
        
        # Download video to temporary file
        temp_video = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        temp_video.close()
        
        try:
            print(f"Downloading video from storage...")
            storage_manager.download_file(video_gcs_path, temp_video.name)
            print(f"Video downloaded to: {temp_video.name}")
            
            # Process video for POI face detections
            detections = self.process_video_for_faces(
                temp_video.name,
                poi_encodings,
                poi_metadata
            )
            
            # Save detection records to database
            if detections:
                self.create_video_poi_detections(db, document_id, detections)
                print(f"\nFace recognition completed successfully")
            else:
                print(f"\nNo POI matches found in this video")
        
        except Exception as e:
            print(f"\nFace recognition error: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        finally:
            # Cleanup temporary file
            if os.path.exists(temp_video.name):
                os.unlink(temp_video.name)
                print(f"Cleaned up temporary video file")
        
        print(f"{'='*60}\n")


# Singleton instance for easy import
face_recognition_processor = FaceRecognitionProcessor()
