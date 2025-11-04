"""Configuration settings for Gemini Image Generator"""

import os
from typing import Optional
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
project_root = Path(__file__).parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    # Try loading from current working directory
    load_dotenv()


@dataclass
class Settings:
    """Application settings"""
    
    # API Configuration
    gemini_api_key: Optional[str] = None
    model_name: str = "gemini-2.5-flash-image"
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 7860
    share: bool = False
    
    # Generation Configuration
    max_history_length: int = 20
    response_modalities: list = None

    # Batch Generation Configuration
    max_batch_size: int = 8
    default_batch_size: int = 4
    enable_parallel_generation: bool = True
    batch_timeout_seconds: int = 300
    max_concurrent_requests: int = 4

    # File Storage
    export_dir: str = "./exports"
    temp_dir: str = "./temp"
    
    def __post_init__(self):
        if self.response_modalities is None:
            self.response_modalities = ["IMAGE", "TEXT"]
        
        # Get settings from environment variables if not set
        if not self.gemini_api_key:
            self.gemini_api_key = os.environ.get("GEMINI_API_KEY")
        
        # Override with environment variables if they exist
        self.model_name = os.environ.get("GEMINI_MODEL_NAME", self.model_name)
        self.host = os.environ.get("HOST", self.host)
        self.port = int(os.environ.get("PORT", str(self.port)))
        self.share = os.environ.get("SHARE", "false").lower() == "true"
        self.max_history_length = int(os.environ.get("MAX_HISTORY_LENGTH", str(self.max_history_length)))

        # Batch generation settings
        self.max_batch_size = int(os.environ.get("MAX_BATCH_SIZE", str(self.max_batch_size)))
        self.default_batch_size = int(os.environ.get("DEFAULT_BATCH_SIZE", str(self.default_batch_size)))
        self.enable_parallel_generation = os.environ.get("ENABLE_PARALLEL_GENERATION", "true").lower() == "true"
        self.batch_timeout_seconds = int(os.environ.get("BATCH_TIMEOUT_SECONDS", str(self.batch_timeout_seconds)))
        self.max_concurrent_requests = int(os.environ.get("MAX_CONCURRENT_REQUESTS", str(self.max_concurrent_requests)))

        self.export_dir = os.environ.get("EXPORT_DIR", self.export_dir)
        self.temp_dir = os.environ.get("TEMP_DIR", self.temp_dir)
        
        # Create directories if they don't exist
        os.makedirs(self.export_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def validate(self) -> bool:
        """Validate settings"""
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        return True


# Singleton instance
_settings = None


def get_settings() -> Settings:
    """Get application settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings