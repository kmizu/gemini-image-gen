"""Image utility functions"""

import base64
import io
from typing import Optional
from PIL import Image


def save_image(image: Image.Image, filepath: str, format: str = "PNG"):
    """
    Save PIL Image to file
    
    Args:
        image: PIL Image object
        filepath: Path to save the image
        format: Image format (PNG, JPEG, etc.)
    """
    image.save(filepath, format=format)


def encode_image(image: Image.Image, format: str = "PNG") -> str:
    """
    Encode PIL Image to base64 string
    
    Args:
        image: PIL Image object
        format: Image format for encoding
        
    Returns:
        Base64 encoded string
    """
    buffered = io.BytesIO()
    image.save(buffered, format=format)
    return base64.b64encode(buffered.getvalue()).decode()


def decode_image(image_data: str) -> Image.Image:
    """
    Decode base64 string to PIL Image
    
    Args:
        image_data: Base64 encoded image string
        
    Returns:
        PIL Image object
    """
    img_data = base64.b64decode(image_data)
    return Image.open(io.BytesIO(img_data))


def create_download_bytes(image: Image.Image, format: str = "PNG") -> bytes:
    """
    Create downloadable bytes from PIL Image
    
    Args:
        image: PIL Image object
        format: Image format
        
    Returns:
        Image as bytes
    """
    buffered = io.BytesIO()
    image.save(buffered, format=format)
    return buffered.getvalue()