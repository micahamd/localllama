import os
import json
from pathlib import Path
from typing import List, Dict, Any

class GeminiAPIConfig:
    """Manages the Gemini API key configuration and model information."""

    def __init__(self):
        """Initialize the configuration manager."""
        self.config_dir = Path.home() / ".config" / "chat_py2"
        self.config_file = self.config_dir / "gemini_api_config.json"
        self.api_key = None
        self._load_config()

        # Hard-coded model lists based on the latest available models
        self._text_models = [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-2.0-flash-thinking-exp-01-21",
            "gemini-2.5-pro-exp-03-25"
        ]

        self._vision_models = [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-2.0-flash-thinking-exp-01-21",
            "gemini-2.5-pro-exp-03-25"
        ]

        self._image_generation_models = [
            "gemini-2.0-flash-exp-image-generation",
            "imagen-3.0-generate-002"
        ]

        self._embedding_models = ["gemini-embedding-exp","text-embedding-004"]

    def get_default_image_generation_model(self):
        """Get the default image generation model."""
        return "gemini-2.0-flash-exp-image-generation"

    def _load_config(self):
        """Load configuration from file."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.api_key = config.get('api_key', None)

            # Check environment variable as fallback
            if not self.api_key:
                self.api_key = os.environ.get('GOOGLE_API_KEY', None)
        except Exception:
            # If loading fails, reset to default
            self.api_key = None

    def save_config(self):
        """Save configuration to file."""
        try:
            # Create directory if it doesn't exist
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # Save config
            with open(self.config_file, 'w') as f:
                json.dump({'api_key': self.api_key}, f)

            return True
        except Exception:
            return False

    def set_api_key(self, api_key):
        """Set the API key and save to config."""
        self.api_key = api_key
        return self.save_config()

    def get_api_key(self):
        """Get the current API key."""
        return self.api_key

    def is_configured(self):
        """Check if API key is configured."""
        return bool(self.api_key)

    def clear_api_key(self):
        """Delete the saved API key."""
        self.api_key = None
        if self.config_file.exists():
            try:
                # Remove the file
                self.config_file.unlink()
                return True
            except Exception:
                return False
        return True

    # Model management methods
    def get_text_models(self) -> List[str]:
        """Return the list of available text models."""
        return self._text_models

    def get_vision_models(self) -> List[str]:
        """Return the list of available vision models."""
        return self._vision_models

    def get_embedding_models(self) -> List[str]:
        """Return the list of available embedding models."""
        return self._embedding_models

    def get_all_models(self) -> List[str]:
        """Return all available models."""
        return self._text_models + self._vision_models

    def is_vision_model(self, model_name: str) -> bool:
        """Check if the model is a vision model."""
        return model_name in self._vision_models

    def get_default_model(self) -> str:
        """Get the default model to use."""
        if self._text_models:
            return self._text_models[0]
        return "gemini-2.0-flash"  # Fallback to a known model

    def get_default_vision_model(self) -> str:
        """Get the default vision model to use."""
        if self._vision_models:
            return self._vision_models[0]
        return "gemini-pro-vision"  # Fallback to a known model

    def get_default_embedding_model(self) -> str:
        """Get the default embedding model to use."""
        if self._embedding_models:
            return self._embedding_models[0]
        return "embedding-001"  # Fallback to a known model

    def get_image_generation_models(self) -> List[str]:
        """Return the list of available image generation models."""
        return self._image_generation_models

    def is_image_generation_model(self, model_name: str) -> bool:
        """Check if the model is an image generation model."""
        return model_name in self._image_generation_models

    def get_default_image_generation_model(self) -> str:
        """Get the default image generation model to use."""
        if self._image_generation_models:
            return self._image_generation_models[0]
        return "gemini-2.0-flash-exp-image-generation"  # Fallback to a known model
