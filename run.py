#!/usr/bin/env python
"""Main entry point for Gemini Image Generator"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from gemini_image_gen.ui.app import launch_app

if __name__ == "__main__":
    try:
        launch_app()
    except KeyboardInterrupt:
        print("\n\nApplication stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)