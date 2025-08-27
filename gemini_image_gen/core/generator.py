"""Gemini API image generation core functionality"""

import io
from typing import Optional, Tuple, List, Dict, Callable
from PIL import Image
from google import genai
from google.genai import types
import gradio as gr

from ..config import get_settings
from ..utils.batch_utils import BatchProcessor, BatchGenerationResult


class GeminiImageGenerator:
    """Handles image generation using Gemini API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the generator with API credentials"""
        self.settings = get_settings()
        api_key = api_key or self.settings.gemini_api_key
        
        if not api_key:
            raise ValueError("API key is required")
        
        self.client = genai.Client(api_key=api_key)
        self.model = self.settings.model_name
        self.batch_processor = BatchProcessor()
    
    def generate(
        self, 
        prompt: str, 
        conversation_history: List[Dict],
        input_image: Optional[Image.Image] = None
    ) -> Tuple[Optional[Image.Image], str]:
        """
        Generate image based on prompt and conversation history
        
        Args:
            prompt: Text prompt for generation
            conversation_history: List of conversation messages
            input_image: Optional input image for editing/reference
            
        Returns:
            Tuple of (generated_image, response_text)
        """
        # Build contents from conversation history
        contents = self._build_contents(conversation_history, prompt, input_image)
        
        # Configure generation
        config = types.GenerateContentConfig(
            response_modalities=self.settings.response_modalities,
        )
        
        # Generate content
        generated_image = None
        response_text = ""
        
        try:
            for chunk in self.client.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=config,
            ):
                if not self._is_valid_chunk(chunk):
                    continue
                
                part = chunk.candidates[0].content.parts[0]
                
                # Handle image data
                if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
                    generated_image = self._process_image_data(part.inline_data)
                
                # Handle text response
                elif hasattr(part, 'text') and part.text:
                    response_text += part.text
        
        except Exception as e:
            raise gr.Error(f"Generation error: {str(e)}")
        
        return generated_image, response_text

    def generate_batch(
        self,
        prompt: str,
        conversation_history: List[Dict],
        input_image: Optional[Image.Image] = None,
        batch_size: Optional[int] = None,
        use_parallel: Optional[bool] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> BatchGenerationResult:
        """
        Generate multiple images based on prompt and conversation history

        Args:
            prompt: Text prompt for generation
            conversation_history: List of conversation messages
            input_image: Optional input image for editing/reference
            batch_size: Number of images to generate (default from settings)
            use_parallel: Force parallel (True) or sequential (False). Auto-detect if None.
            progress_callback: Optional callback for progress updates

        Returns:
            BatchGenerationResult containing all generated images and metadata
        """
        # Set default batch size
        if batch_size is None:
            batch_size = self.settings.default_batch_size

        # Validate batch size
        if batch_size < 1:
            raise ValueError("バッチサイズは1以上である必要があります")
        if batch_size > self.settings.max_batch_size:
            raise ValueError(f"バッチサイズは{self.settings.max_batch_size}以下である必要があります")

        # Set progress callback
        if progress_callback:
            self.batch_processor.set_progress_callback(progress_callback)

        # Create generation function that captures current context
        def single_generation() -> Tuple[Optional[Image.Image], str]:
            return self.generate(prompt, conversation_history, input_image)

        # Run batch generation
        return self.batch_processor.run_batch(
            batch_size=batch_size,
            generation_func=single_generation,
            use_parallel=use_parallel
        )

    def cancel_batch(self):
        """Cancel the current batch generation"""
        self.batch_processor.cancel()

    def _build_contents(
        self, 
        conversation_history: List[Dict], 
        current_prompt: str,
        input_image: Optional[Image.Image] = None
    ) -> List[types.Content]:
        """Build content list for API request"""
        contents = []
        
        # Add conversation history
        for msg in conversation_history:
            if msg["role"] == "user":
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=msg["content"])]
                ))
            elif msg["role"] == "model" and msg.get("content"):
                contents.append(types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=msg["content"])] if msg["content"] else []
                ))
        
        # Add current prompt with optional image
        parts = [types.Part.from_text(text=current_prompt)]
        if input_image:
            # Convert PIL Image to bytes for the API
            buffered = io.BytesIO()
            input_image.save(buffered, format="PNG")
            image_bytes = buffered.getvalue()
            parts.append(types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/png"
            ))
        
        contents.append(types.Content(
            role="user",
            parts=parts
        ))
        
        return contents
    
    def _is_valid_chunk(self, chunk) -> bool:
        """Check if chunk contains valid data"""
        return (
            chunk.candidates is not None and
            chunk.candidates[0].content is not None and
            chunk.candidates[0].content.parts is not None
        )
    
    def _process_image_data(self, inline_data) -> Image.Image:
        """Process inline image data to PIL Image"""
        return Image.open(io.BytesIO(inline_data.data))