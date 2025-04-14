import os
import json
from pathlib import Path
from typing import List, Dict, Any, Iterator, Optional
import anthropic
from datetime import datetime, timedelta

class AnthropicAPIConfig:
    """Manages the Anthropic Claude API key configuration and model information."""
    
    def __init__(self):
        """Initialize the configuration manager."""
        self.config_dir = Path.home() / ".config" / "chat_py2"
        self.config_file = self.config_dir / "anthropic_api_config.json"
        self.api_key = None
        self._models_cache = None
        self._cache_timestamp = None
        self._cache_valid_duration = timedelta(hours=24)  # Cache valid for 24 hours
        
        # Default models in case API is not available
        self._default_text_models = [
            "claude-3-7-sonnet-20250219",
            "claude-3-5-haiku-20241022"
        ]
        
        # Vision-capable models (default fallback)
        self._default_vision_models = [
            "claude-3-7-sonnet-20250219",
            "claude-3-5-haiku-20241022"
        ]
        
        # Load saved configuration
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.api_key = config.get('api_key', None)
                    
                    # Load cached models if available
                    if 'models_cache' in config and 'cache_timestamp' in config:
                        self._models_cache = config.get('models_cache')
                        timestamp_str = config.get('cache_timestamp')
                        self._cache_timestamp = datetime.fromisoformat(timestamp_str)
            
            # Check environment variable as fallback
            if not self.api_key:
                self.api_key = os.environ.get('ANTHROPIC_API_KEY', None)
        except Exception:
            # If loading fails, reset to default
            self.api_key = None
    
    def save_config(self):
        """Save configuration to file."""
        try:
            # Create directory if it doesn't exist
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            config_data = {'api_key': self.api_key}
            
            # Save model cache if available
            if self._models_cache and self._cache_timestamp:
                config_data['models_cache'] = self._models_cache
                config_data['cache_timestamp'] = self._cache_timestamp.isoformat()
            
            # Save config
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f)
            
            return True
        except Exception:
            return False
    
    def set_api_key(self, api_key):
        """Set the API key and save to config."""
        self.api_key = api_key
        # Clear the models cache to force a refresh with new API key
        self._models_cache = None
        self._cache_timestamp = None
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
        self._models_cache = None
        self._cache_timestamp = None
        if self.config_file.exists():
            try:
                # Remove the file
                self.config_file.unlink()
                return True
            except Exception:
                return False
        return True
    
    def _update_models_from_api(self):
        """Fetch the latest models from the Anthropic API."""
        if not self.is_configured():
            return False
        
        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            models_response = client.models.list()
            
            # Extract model data
            all_models = []
            vision_models = []
            
            for model in models_response.data:
                model_id = model.id
                all_models.append(model_id)
                
                # Check if the model supports vision
                # Most Claude models after Claude 3 support vision, but this may change
                if any(vision_name in model_id.lower() for vision_name in ["claude-3"]):
                    vision_models.append(model_id)
            
            # Update cache
            self._models_cache = {
                'all_models': all_models,
                'vision_models': vision_models
            }
            self._cache_timestamp = datetime.now()
            self.save_config()  # Save the updated cache
            
            return True
        except Exception:
            return False
    
    def _ensure_models_up_to_date(self):
        """Make sure models are up to date, fetching if necessary."""
        # If cache doesn't exist or is expired, update from API
        cache_expired = (self._cache_timestamp is None or 
                         datetime.now() - self._cache_timestamp > self._cache_valid_duration)
        
        if self._models_cache is None or cache_expired:
            success = self._update_models_from_api()
            if not success:
                # If API fetch fails, use default models
                self._models_cache = {
                    'all_models': self._default_text_models,
                    'vision_models': self._default_vision_models
                }
    
    # Model management methods
    def get_text_models(self) -> List[str]:
        """Return the list of available text models."""
        self._ensure_models_up_to_date()
        return self._models_cache.get('all_models', self._default_text_models)
    
    def get_vision_models(self) -> List[str]:
        """Return the list of available vision models."""
        self._ensure_models_up_to_date()
        return self._models_cache.get('vision_models', self._default_vision_models)
    
    def get_embedding_models(self) -> List[str]:
        """Return the list of available embedding models."""
        return []  # Claude doesn't offer embedding models
    
    def get_all_models(self) -> List[str]:
        """Return all available models."""
        return self.get_text_models()
    
    def is_vision_model(self, model_name: str) -> bool:
        """Check if the model is a vision model."""
        self._ensure_models_up_to_date()
        return model_name in self._models_cache.get('vision_models', self._default_vision_models)
    
    def get_default_model(self) -> str:
        """Get the default model to use."""
        models = self.get_text_models()
        if models:
            return models[0]
        return "claude-3-sonnet-20240229"  # Fallback to a known model
    
    def get_default_vision_model(self) -> str:
        """Get the default vision model to use."""
        models = self.get_vision_models()
        if models:
            return models[0]
        return "claude-3-sonnet-20240229"  # Fallback to a known model


def get_anthropic_response(messages, model="claude-3-sonnet-20240229", stream=True, max_tokens=2048, temperature=0.7) -> Iterator[str]:
    """Get a streaming response from the Anthropic API."""
    config = AnthropicAPIConfig()
    api_key = config.get_api_key()

    if not api_key:
        raise ValueError("Anthropic API key is not configured. Please set it in the settings.")

    client = anthropic.Anthropic(api_key=api_key)
    
    # Convert messages to Anthropic format
    anthropic_messages = []
    system_content = None
    
    for msg in messages:
        if msg["role"] == "system":
            system_content = msg["content"]
        elif msg["role"] == "user" or msg["role"] == "assistant":
            content = []
            
            # Handle text content
            if "content" in msg and msg["content"]:
                content.append({
                    "type": "text",
                    "text": msg["content"]
                })
            
            # Handle images if present
            if "images" in msg and msg["role"] == "user":
                for image_data in msg["images"]:
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_data.decode("utf-8") if isinstance(image_data, bytes) else image_data
                        }
                    })
            
            anthropic_messages.append({
                "role": "user" if msg["role"] == "user" else "assistant",
                "content": content
            })
    
    # Create the message with the Claude API
    response = client.messages.create(
        model=model,
        messages=anthropic_messages,
        system=system_content,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=stream
    )
    
    if stream:
        for chunk in response:
            if chunk.type == "content_block_delta" and hasattr(chunk.delta, "text"):
                yield chunk.delta.text
    else:
        yield response.content[0].text
