"""
Gemini Image Generator
A web-based image generation application using Google's Gemini API
"""

__version__ = "1.0.0"
__author__ = "Gemini Image Gen Team"

from .core.generator import GeminiImageGenerator
from .ui.app import create_app

__all__ = [
    "GeminiImageGenerator",
    "create_app",
]