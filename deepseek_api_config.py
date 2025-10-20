import os
import json
from pathlib import Path
from openai import OpenAI

# DeepSeek Models: deepseek-chat, deepseek-reasoner

class DeepSeekAPIConfig:
    """Manages the DeepSeek API key configuration."""

    def __init__(self):
        """Initialize the configuration manager."""
        self.config_dir = Path.home() / ".config" / "chat_py2"
        self.config_file = self.config_dir / "deepseek_api_config.json"
        self.api_key = None
        self._load_config()

    def _load_config(self):
        """Load configuration from file."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.api_key = config.get('api_key', None)

            # Check environment variable as fallback
            if not self.api_key:
                self.api_key = os.environ.get('DEEPSEEK_API_KEY', None)  # Use DEEPSEEK_API_KEY
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

def get_deepseek_response(messages, model="deepseek-chat", stream=False):
    """Get a response from the DeepSeek API."""
    config = DeepSeekAPIConfig()
    api_key = config.get_api_key()

    if not api_key:
        raise ValueError("DeepSeek API key is not configured. Please set it using the API menu.")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=stream
    )

    if stream:
        response_content = ""
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                response_content += chunk.choices[0].delta.content
        return response_content
    else:
        return response.choices[0].message.content
