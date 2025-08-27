#!/usr/bin/env python
"""Main entry point for Gemini Image Generator with Batch Support"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from gemini_image_gen.ui.app_batch import launch_batch_app

if __name__ == "__main__":
    try:
        from gemini_image_gen.config import get_settings
        settings = get_settings()
        print("🚀 Starting Gemini Image Generator with Batch Support...")
        print("📦 Features: Batch generation, parallel processing, ZIP downloads")
        print(f"🌐 Access the app at: http://localhost:{settings.port}")
        print("⏹️ Press Ctrl+C to stop\n")
        launch_batch_app()
    except KeyboardInterrupt:
        print("\n\n⏹️ Application stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)