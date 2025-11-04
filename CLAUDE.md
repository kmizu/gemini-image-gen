# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Communication Style

**はんなり関西弁で優しく接する**

When interacting with users in this repository, use gentle Kansai dialect (はんなり関西弁) to create a warm and friendly atmosphere.

## Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Or install as a package
pip install -e .

# Configure environment (required)
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your-api-key-here
```

### Running the Application
```bash
# Batch version with multiple image generation (recommended)
python run_batch.py

# Standard version with single image generation
python run.py

# If installed as package
gemini-image-gen
```

### Development
```bash
# Run tests (if available)
pytest tests/

# Code formatting
black gemini_image_gen/
isort gemini_image_gen/

# Type checking
mypy gemini_image_gen/
```

## Architecture

This is a Gradio-based web application for generating images using Google's Gemini API. The application supports both single and batch image generation with conversation history management.

### Core Components

- **`gemini_image_gen/core/generator.py`**: Main `GeminiImageGenerator` class that interfaces with Gemini API
  - `generate()`: Single image generation with streaming
  - `generate_batch()`: Batch generation (1-8 images) with parallel or sequential processing
  - Uses `google.genai.Client` with streaming API calls

- **`gemini_image_gen/core/conversation.py`**: Conversation history management
  - Stores user prompts and model responses
  - Handles serialization/deserialization for saving/loading conversations

- **`gemini_image_gen/ui/app.py`**: Standard Gradio UI (single image generation)
- **`gemini_image_gen/ui/app_batch.py`**: Enhanced Gradio UI with batch generation support
  - Batch size selector (1-8 images)
  - ZIP download for multiple images
  - Progress tracking for batch operations

- **`gemini_image_gen/config/settings.py`**: Centralized configuration using environment variables and dataclasses
  - Loads `.env` file automatically
  - Singleton pattern via `get_settings()`

- **`gemini_image_gen/utils/`**: Utility modules
  - `batch_utils.py`: `BatchProcessor` for parallel/sequential image generation
  - `image_utils.py`: Image processing helpers
  - `file_utils.py`: File operations (save, export, ZIP creation)

### Data Flow

1. User submits prompt via Gradio UI
2. UI calls `GeminiImageGenerator.generate()` or `generate_batch()`
3. Generator builds conversation history and calls Gemini API
4. API streams response chunks containing image data and text
5. Generator extracts images from inline_data and converts to PIL Images
6. UI displays images and updates conversation history

### Key Configuration

All configuration is managed through environment variables (loaded from `.env`):
- `GEMINI_API_KEY`: Required API key
- `GEMINI_MODEL_NAME`: Model to use (default: `gemini-2.5-flash-image`)
- `MAX_BATCH_SIZE`: Maximum images per batch (default: 8)
- `DEFAULT_BATCH_SIZE`: Default batch size (default: 4)
- `ENABLE_PARALLEL_GENERATION`: Enable parallel processing (default: true)
- `MAX_CONCURRENT_REQUESTS`: Max parallel API calls (default: 4)

See `.env.example` for complete configuration options.

### Entry Points

- `run.py`: Launches standard app via `gemini_image_gen.ui.app.launch_app()`
- `run_batch.py`: Launches batch app via `gemini_image_gen.ui.app_batch.launch_batch_app()`
- Package entry point: `gemini_image_gen.ui.app:launch_app` (defined in setup.py)

### Response Handling

The application uses Gemini's streaming API:
- Iterates over chunks from `client.models.generate_content_stream()`
- Extracts `inline_data` containing image bytes from response parts
- Converts bytes to PIL Images using `Image.open(io.BytesIO(data))`
- Accumulates text responses from parts with `.text` attribute
- Handles errors with Gradio error dialogs
