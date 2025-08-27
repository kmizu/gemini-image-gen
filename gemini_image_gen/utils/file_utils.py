"""File handling utilities"""

import json
import tempfile
import zipfile
import os
from typing import List, Dict, Optional
from datetime import datetime
from PIL import Image

from ..config import get_settings

def save_conversation(history: List[Dict], filename: Optional[str] = None) -> str:
    """
    Save conversation history to JSON file
    
    Args:
        history: Conversation history list
        filename: Optional filename, auto-generated if not provided
        
    Returns:
        Path to saved file
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"conversation_{timestamp}.json"
    
    # Create temporary file for download
    temp_file = tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.json',
        delete=False,
        encoding='utf-8'
    )
    
    json.dump(history, temp_file, ensure_ascii=False, indent=2)
    temp_file.close()
    
    return temp_file.name


def load_conversation(filepath: str) -> List[Dict]:
    """
    Load conversation history from JSON file
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        Conversation history list
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def create_batch_zip(
    images: List[Image.Image],
    texts: List[str],
    base_name: Optional[str] = None
) -> str:
    """
    Create a ZIP file containing multiple images with metadata

    Args:
        images: List of PIL Image objects
        texts: List of corresponding text descriptions
        base_name: Optional base name for files

    Returns:
        Path to created ZIP file
    """
    if not images:
        raise ValueError("画像リストが空です")

    if len(images) != len(texts):
        raise ValueError("画像とテキストの数が一致しません")

    settings = get_settings()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if base_name is None:
        base_name = f"batch_images_{timestamp}"

    # Create temporary ZIP file
    temp_zip = tempfile.NamedTemporaryFile(
        suffix='.zip',
        delete=False,
        dir=settings.temp_dir
    )
    temp_zip.close()

    try:
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add metadata file
            metadata = {
                "generated_at": timestamp,
                "total_images": len(images),
                "images": []
            }

            # Add each image to ZIP
            for i, (image, text) in enumerate(zip(images, texts)):
                # Save image to temporary file
                img_filename = f"{base_name}_{i+1:03d}.png"

                # Create temporary image file
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_img:
                    image.save(temp_img.name, "PNG")

                    # Add to ZIP
                    zipf.write(temp_img.name, img_filename)

                    # Clean up temporary image file
                    os.unlink(temp_img.name)

                # Add to metadata
                metadata["images"].append({
                    "filename": img_filename,
                    "description": text,
                    "index": i + 1
                })

            # Add metadata.json to ZIP
            metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2)
            zipf.writestr("metadata.json", metadata_json)

        return temp_zip.name

    except Exception as e:
        # Clean up ZIP file if creation failed
        if os.path.exists(temp_zip.name):
            os.unlink(temp_zip.name)
        raise Exception(f"ZIP作成エラー: {str(e)}")


def save_image_with_metadata(
    image: Image.Image,
    text: str,
    filename: Optional[str] = None
) -> str:
    """
    Save a single image with metadata to temporary file

    Args:
        image: PIL Image object
        text: Description text
        filename: Optional filename

    Returns:
        Path to saved file
    """
    settings = get_settings()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # microsecond precision

    if filename is None:
        filename = f"generated_image_{timestamp}.png"

    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(
        suffix='.png',
        delete=False,
        dir=settings.temp_dir
    )
    temp_file.close()

    try:
        # Add metadata to image (if supported)
        from PIL.PngImagePlugin import PngInfo
        metadata = PngInfo()
        metadata.add_text("Description", text)
        metadata.add_text("Generated", timestamp)

        # Save image with metadata
        image.save(temp_file.name, "PNG", pnginfo=metadata)

        return temp_file.name

    except Exception as e:
        # Fallback: save without metadata
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

        temp_file = tempfile.NamedTemporaryFile(
            suffix='.png',
            delete=False,
            dir=settings.temp_dir
        )
        temp_file.close()

        image.save(temp_file.name, "PNG")
        return temp_file.name


def cleanup_temp_files(file_paths: List[str]):
    """
    Clean up temporary files

    Args:
        file_paths: List of file paths to delete
    """
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception:
            # Ignore cleanup errors
            pass
