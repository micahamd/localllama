import json
import os
from typing import Dict, Any, Optional

class Settings:
    """Handles saving and loading user preferences."""

    DEFAULT_SETTINGS = {
        "developer": "ollama",
        "llm_model": "",
        "embedding_model": "",
        "temperature": 0.7,
        "context_size": 8000,  # Default to 8k context window
        "chunk_size": 128,
        "top_k": 20,  # Optimized default for better balance
        "top_p": 0.9,
        "repeat_penalty": 1.1,
        "max_tokens": 2048,
        "include_chat": True,
        "show_image": True,
        "include_file": True,
        "web_access": False,
        "advanced_web_access": False,
        "write_file": False,
        "read_file": False,
        "intelligent_processing": True,
        "system_prompt": "Respond honestly and factually at all times."
    }

    def __init__(self, settings_file: str = "chat_settings.json"):
        """Initialize settings with default values or from a settings file."""
        self.settings_file = settings_file
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.load_settings()

    def load_settings(self) -> None:
        """Load settings from the settings file if it exists."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                    # Update settings with loaded values
                    self.settings.update(loaded_settings)
                print(f"Settings loaded from {self.settings_file}")
        except Exception as e:
            print(f"Error loading settings: {str(e)}")

    def save_settings(self) -> None:
        """Save current settings to the settings file."""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
            print(f"Settings saved to {self.settings_file}")
        except Exception as e:
            print(f"Error saving settings: {str(e)}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value by key, with optional default."""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value by key."""
        self.settings[key] = value

    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple settings at once."""
        self.settings.update(updates)

    def get_all(self) -> Dict[str, Any]:
        """Get all settings as a dictionary."""
        return self.settings.copy()
