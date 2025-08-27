"""Conversation history management"""

import base64
import io
from typing import List, Dict, Optional
from datetime import datetime
from PIL import Image


class ConversationManager:
    """Manage conversation history with edit and delete capabilities"""
    
    def __init__(self):
        """Initialize empty conversation"""
        self.history: List[Dict] = []
    
    def add_message(
        self,
        role: str,
        content: str = None,
        image: Optional[Image.Image] = None,
        images: Optional[List[Image.Image]] = None
    ) -> List[Dict]:
        """
        Add a message to conversation history

        Args:
            role: 'user' or 'model'/'assistant'
            content: Text content of the message
            image: Optional single PIL Image (for backward compatibility)
            images: Optional list of PIL Images (for batch results)

        Returns:
            Updated history list
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }

        # Handle single image (backward compatibility)
        if image:
            message["image"] = self._encode_image(image)

        # Handle multiple images (new batch functionality)
        if images and len(images) > 0:
            if len(images) == 1:
                # Single image in list - treat as single image
                message["image"] = self._encode_image(images[0])
            else:
                # Multiple images - store as batch
                message["images"] = [self._encode_image(img) for img in images]
                message["image_count"] = len(images)

        self.history.append(message)
        return self.history
    
    def edit_message(self, index: int, new_content: str) -> List[Dict]:
        """
        Edit a specific message in history
        
        Args:
            index: Index of message to edit
            new_content: New text content
            
        Returns:
            Updated history list
        """
        if 0 <= index < len(self.history):
            self.history[index]["content"] = new_content
            self.history[index]["edited"] = True
            self.history[index]["edit_timestamp"] = datetime.now().isoformat()
        return self.history
    
    def delete_message(self, index: int) -> List[Dict]:
        """
        Delete a specific message from history
        
        Args:
            index: Index of message to delete
            
        Returns:
            Updated history list
        """
        if 0 <= index < len(self.history):
            self.history.pop(index)
        return self.history
    
    def clear_history(self) -> List[Dict]:
        """Clear all conversation history"""
        self.history = []
        return self.history
    
    def get_history(self) -> List[Dict]:
        """Get current history"""
        return self.history
    
    def set_history(self, history: List[Dict]):
        """Set history from external source"""
        self.history = history
    
    def get_exportable_history(self) -> List[Dict]:
        """
        Get history suitable for export (without large image data)
        
        Returns:
            History list with image data removed
        """
        export_history = []
        for msg in self.history:
            export_msg = {
                "role": msg["role"],
                "content": msg.get("content", ""),
                "timestamp": msg.get("timestamp", ""),
            }
            
            if "image" in msg:
                export_msg["has_image"] = True
            elif "images" in msg:
                export_msg["has_images"] = True
                export_msg["image_count"] = msg.get("image_count", len(msg["images"]))
            
            if msg.get("edited"):
                export_msg["edited"] = True
                export_msg["edit_timestamp"] = msg.get("edit_timestamp", "")
            
            export_history.append(export_msg)
        
        return export_history
    
    def load_from_export(self, exported_history: List[Dict]):
        """
        Load history from exported format
        
        Args:
            exported_history: History list from export
        """
        self.history = []
        for msg in exported_history:
            history_msg = {
                "role": msg["role"],
                "content": msg.get("content", ""),
                "timestamp": msg.get("timestamp", datetime.now().isoformat())
            }
            
            if msg.get("edited"):
                history_msg["edited"] = True
                history_msg["edit_timestamp"] = msg.get("edit_timestamp", "")
            
            self.history.append(history_msg)
    
    def decode_image(self, image_data: str) -> Image.Image:
        """Decode base64 image data to PIL Image"""
        img_data = base64.b64decode(image_data)
        return Image.open(io.BytesIO(img_data))
    
    def _encode_image(self, image: Image.Image) -> str:
        """Encode PIL Image to base64 string"""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    def add_batch_result(
        self,
        role: str,
        images: List[Image.Image],
        texts: List[str],
        selected_index: Optional[int] = None
    ) -> List[Dict]:
        """
        Add batch generation result to conversation history

        Args:
            role: 'assistant' or 'model'
            images: List of generated images
            texts: List of corresponding text descriptions
            selected_index: Index of selected image (None if no selection)

        Returns:
            Updated history list
        """
        if not images:
            return self.history

        # Combine all texts into a summary
        if len(set(texts)) == 1:
            # All texts are the same
            content = texts[0] if texts else f"{len(images)}枚の画像を生成しました"
        else:
            # Different texts
            content = f"{len(images)}枚の画像を生成しました"

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "images": [self._encode_image(img) for img in images],
            "image_count": len(images),
            "batch_texts": texts
        }

        if selected_index is not None and 0 <= selected_index < len(images):
            message["selected_index"] = selected_index
            message["selected_image"] = self._encode_image(images[selected_index])

        self.history.append(message)
        return self.history

    def select_image_from_batch(self, message_index: int, image_index: int) -> bool:
        """
        Select a specific image from a batch message

        Args:
            message_index: Index of the message in history
            image_index: Index of the image to select

        Returns:
            True if selection was successful, False otherwise
        """
        if not (0 <= message_index < len(self.history)):
            return False

        message = self.history[message_index]
        if "images" not in message:
            return False

        if not (0 <= image_index < len(message["images"])):
            return False

        # Update selection
        message["selected_index"] = image_index
        message["selected_image"] = message["images"][image_index]
        message["edit_timestamp"] = datetime.now().isoformat()

        return True

    def get_batch_images(self, message_index: int) -> Optional[List[Image.Image]]:
        """
        Get all images from a batch message

        Args:
            message_index: Index of the message in history

        Returns:
            List of PIL Images or None if not found
        """
        if not (0 <= message_index < len(self.history)):
            return None

        message = self.history[message_index]
        if "images" not in message:
            return None

        return [self.decode_image(img_data) for img_data in message["images"]]