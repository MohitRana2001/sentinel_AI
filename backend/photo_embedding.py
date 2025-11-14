"""
Utility functions for generating photo embeddings for Person of Interest
Uses face_recognition library to create face encodings
"""

import base64
import io
import numpy as np
from PIL import Image
import face_recognition
from typing import Optional, List


def generate_photo_embedding(photograph_base64: str) -> Optional[List[float]]:
    """
    Generate face encoding (photo embedding) from base64 encoded image
    
    Args:
        photograph_base64: Base64 encoded image (with or without data URL prefix)
    
    Returns:
        List of 128 float values representing the face encoding, or None if no face detected
    
    Raises:
        ValueError: If image cannot be decoded or processed
    """
    try:
        # Handle data URL format (e.g., "data:image/jpeg;base64,...")
        photo_data = photograph_base64
        if photo_data.startswith('data:image'):
            photo_data = photo_data.split(',', 1)[1]
        
        # Decode base64 to bytes
        image_bytes = base64.b64decode(photo_data)
        
        # Open image
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB numpy array (required by face_recognition)
        image_np = np.array(image.convert('RGB'))
        
        # Extract face encoding (128-dimensional vector)
        encodings = face_recognition.face_encodings(image_np)
        
        if not encodings:
            print("⚠️ No face detected in photograph")
            return None
        
        if len(encodings) > 1:
            print(f"⚠️ Multiple faces detected ({len(encodings)}), using first one")
        
        # Convert numpy array to list for JSON serialization
        encoding = encodings[0].tolist()
        
        print(f"✅ Generated face encoding with {len(encoding)} dimensions")
        return encoding
        
    except base64.binascii.Error as e:
        raise ValueError(f"Invalid base64 encoding: {e}")
    except Exception as e:
        raise ValueError(f"Error processing image: {e}")


def validate_photo_base64(photograph_base64: str) -> bool:
    """
    Validate that a base64 string represents a valid image
    
    Args:
        photograph_base64: Base64 encoded image
    
    Returns:
        True if valid, False otherwise
    """
    try:
        # Handle data URL format
        photo_data = photograph_base64
        if photo_data.startswith('data:image'):
            photo_data = photo_data.split(',', 1)[1]
        
        # Try to decode and open as image
        image_bytes = base64.b64decode(photo_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Verify it's a valid image
        image.verify()
        return True
        
    except Exception:
        return False


def decode_photo_to_numpy(photograph_base64: str) -> np.ndarray:
    """
    Decode base64 photo to numpy array for face recognition
    
    Args:
        photograph_base64: Base64 encoded image
    
    Returns:
        RGB numpy array
    
    Raises:
        ValueError: If image cannot be decoded
    """
    try:
        # Handle data URL format
        photo_data = photograph_base64
        if photo_data.startswith('data:image'):
            photo_data = photo_data.split(',', 1)[1]
        
        # Decode base64 to bytes
        image_bytes = base64.b64decode(photo_data)
        
        # Open and convert to RGB
        image = Image.open(io.BytesIO(image_bytes))
        image_np = np.array(image.convert('RGB'))
        
        return image_np
        
    except Exception as e:
        raise ValueError(f"Error decoding photo: {e}")
