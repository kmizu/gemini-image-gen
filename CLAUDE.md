# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Set required environment variable
export GEMINI_API_KEY="your_api_key"

# Run the standard image generator
python run.py

# Run the batch-enabled image generator (recommended)
python run_batch.py
```

## Architecture

This is a simple Python application for generating images using Google's Gemini API:

- **main.py**: Single-file application that uses the Gemini 2.5 Flash Image Preview model to generate images based on text prompts
- **API Client**: Uses `google.genai.Client` with API key authentication
- **Streaming**: Implements streaming response handling for generated content
- **File Output**: Automatically saves generated images with appropriate file extensions

## Key Configuration Points

1. **Environment Variable**: The application requires `GEMINI_API_KEY` to be set
2. **Model**: Currently hardcoded to use `gemini-2.5-flash-image-preview`
3. **Placeholders to Configure**:
   - Line 38: Replace `INSERT_INPUT_HERE` with the actual prompt text
   - Line 62: Replace `ENTER_FILE_NAME_{file_index}` with desired output filename pattern

## Response Handling

The application processes streaming chunks from the Gemini API:
- Extracts inline image data from response chunks
- Automatically detects MIME type and applies appropriate file extension
- Saves binary image data to local files
- Prints any text responses to console