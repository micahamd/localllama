from typing import List, Dict, Any, Optional, Iterator
import ollama
import google.generativeai as genai
from error_handler import safe_execute, error_handler
import time
from gemini_api_config import GeminiAPIConfig
from deepseek_api_config import DeepSeekAPIConfig, get_deepseek_response
from anthropic_api_config import AnthropicAPIConfig, get_anthropic_response
import PIL.Image
from io import BytesIO
from PIL import Image


class ModelManager:
    """Base class for model management."""

    def __init__(self):
        self.models = []

    def list_models(self) -> List[str]:
        """List available models."""
        return self.models

    def get_response(self, messages: List[Dict[str, Any]], **kwargs) -> Iterator[Dict[str, Any]]:
        """Get a response from the model."""
        raise NotImplementedError("Subclasses must implement get_response")

    def get_embedding(self, text: str) -> List[float]:
        """Get an embedding for the given text."""
        raise NotImplementedError("Subclasses must implement get_embedding")


class OllamaManager(ModelManager):
    """Manager for Ollama models."""

    @safe_execute("Fetching Ollama models")
    def __init__(self):
        super().__init__()
        self.refresh_models()

    @safe_execute("Refreshing Ollama models")
    def refresh_models(self) -> None:
        """Refresh the list of available Ollama models."""
        models = ollama.list()
        self.models = [model.model for model in models.models]
        self.llm_models = [name for name in self.models if 'embed' not in name]
        self.embedding_models = [name for name in self.models if 'embed' in name]

    def get_llm_models(self) -> List[str]:
        """Get list of LLM models (excluding embedding models)."""
        return self.llm_models

    def get_embedding_models(self) -> List[str]:
        """Get list of embedding models."""
        return self.embedding_models

    @safe_execute("Getting Ollama response")
    def get_response(self, messages: List[Dict[str, Any]], **kwargs) -> Iterator[Dict[str, Any]]:
        """Get a streaming response from an Ollama model."""
        model_name = kwargs.get("model", "llama2")
        temperature = kwargs.get("temperature", 0.7)
        context_size = kwargs.get("context_size", 4096)

        # Get streaming response from Ollama
        stream = ollama.chat(
            model=model_name,
            messages=messages,
            stream=True,
            options={
                "temperature": temperature,
                "num_ctx": context_size
            }
        )

        # Yield each chunk from the stream
        for chunk in stream:
            yield chunk

    @safe_execute("Getting Ollama embedding")
    def get_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        """Get an embedding for the given text using Ollama."""
        if not model:
            # Use first available embedding model, or default to nomic-embed-text if none available
            model = next((m for m in self.embedding_models), "nomic-embed-text")

        response = ollama.embeddings(model=model, prompt=text)
        return response.get("embedding", [])


class GeminiManager(ModelManager):
    """Manager for Google's Gemini models."""

    @safe_execute("Initializing Gemini")
    def __init__(self, api_key=None):
        super().__init__()
        self.api_config = GeminiAPIConfig()

        # If API key is provided during initialization, set it
        if (api_key):
            self.api_config.set_api_key(api_key)

        self._configure_api()
        self.refresh_models()

    def _configure_api(self):
        """Configure the Gemini API with the API key."""
        api_key = self.api_config.get_api_key()
        if api_key:
            genai.configure(api_key=api_key)

    def save_api_key(self, api_key):
        """Save a new API key and reconfigure."""
        result = self.api_config.set_api_key(api_key)
        if result:
            self._configure_api()
        return result

    @safe_execute("Refreshing Gemini models")
    def refresh_models(self) -> None:
        """Refresh the list of available Gemini models."""
        # Use models from the API config
        self.models = self.api_config.get_all_models()
        self.llm_models = self.api_config.get_text_models() + self.api_config.get_image_generation_models()  # Include image generation models
        self.embedding_models = self.api_config.get_embedding_models()

    def get_llm_models(self) -> List[str]:
        """Get list of available Gemini models."""
        return self.llm_models

    def get_embedding_models(self) -> List[str]:
        """Get list of embedding models."""
        return self.embedding_models

    @safe_execute("Getting Gemini response")
    def get_response(self, messages: List[Dict[str, Any]], **kwargs) -> Iterator[Dict[str, Any]]:
        """Get a streaming response from a Gemini model."""
        model_name = kwargs.get("model", self.api_config.get_default_model())
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 2048)

        # Check if API key is configured
        if not self.api_config.is_configured():
            raise ValueError("Gemini API key is not configured. Please set it in the settings.")

        # Convert messages to Gemini format
        gemini_messages = []
        image_parts = []
        system_content = None  # Initialize system_content

        for msg in messages:
            if msg["role"] == "system":
                # Gemini doesn't support system messages directly, so we prepend to the user's message
                system_content = msg["content"]
                continue

            content = msg["content"]

            # Check for images in the message
            if "images" in msg and msg.get("role") == "user":
                image_parts = [
                    {"mime_type": "image/jpeg", "data": image_data}  # Correct format for image data
                    for image_data in msg["images"]
                ]

            # If this is the first user message and there was a system message, prepend it
            if msg["role"] == "user" and system_content:
                content = f"System: {system_content}\n\nUser: {content}"
                system_content = None  # Clear system_content after use

            gemini_messages.append({
                "role": "user" if msg["role"] == "user" else "model",
                "parts": [{"text": content}] + image_parts
            })

            # Clear image parts after adding them to a message
            image_parts = []

        # Create Gemini generation config
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "top_p": 0.95,
            "top_k": 0,
        }

        # Determine which model to use based on whether images are present
        has_images = any("images" in msg for msg in messages)

        # Select appropriate model based on content and availability
        if has_images:
            # For multimodal inputs, use a vision model
            model_to_use = self.api_config.get_default_vision_model()
        else:
            # For text-only, use the selected model
            model_to_use = model_name

            # Fallback to default model if the selected model isn't available
            if model_to_use not in self.models:
                model_to_use = self.api_config.get_default_model()

        # Create the model instance
        model = genai.GenerativeModel(model_name=model_to_use)

        # Start the response stream
        response = model.generate_content(
            gemini_messages[-1]["parts"],  # Only send the last message for now
            stream=True,
            generation_config=generation_config
        )

        # Process stream chunks
        for chunk in response:
            # Convert chunk to a format compatible with our application
            compatible_chunk = {
                "message": {
                    "role": "assistant",
                    "content": chunk.text if hasattr(chunk, "text") else "",
                }
            }
            yield compatible_chunk

            # Add a small delay to make the stream more natural
            time.sleep(0.01)

    @safe_execute("Getting Gemini embedding")
    def get_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        """Get an embedding for the given text using Gemini."""
        if not model or model not in self.embedding_models:
            model = self.api_config.get_default_embedding_model()

        # Properly format the model name for the API
        embedding_model = genai.get_embedding_model(model)
        result = embedding_model.get_embeddings([text])

        if result and result[0] and hasattr(result[0], "values"):
            return result[0].values
        return []

    @safe_execute("Getting image generation response")
    def generate_image(self, prompt: str, image_data: Optional[bytes] = None, **kwargs) -> Iterator[Dict[str, Any]]:
        """Generate an image using Gemini's image generation capabilities.

        This method uses the Imagen model to generate high-quality images from text prompts.
        Implementation based on the working example in gemini_template.py.

        Args:
            prompt: The text prompt for image generation
            image_data: Optional image data (not used for Imagen, but kept for API compatibility)
            **kwargs: Additional parameters including temperature

        Returns:
            Iterator of message chunks containing text or image data
        """
        # Check if API key is configured
        if not self.api_config.is_configured():
            raise ValueError("Gemini API key is not configured. Please set it in the settings.")

        try:
            # Log the process
            print(f"Generating image with prompt: {prompt}")
            yield {"message": {"role": "assistant", "content": "Generating image based on your prompt..."}}

            # Import required libraries
            import google.generativeai as genai
            import PIL.Image
            import base64
            from io import BytesIO

            # Configure the API key
            genai.configure(api_key=self.api_config.get_api_key())

            # Generate the image using the Gemini API
            try:
                # Create a generation config
                generation_config = {
                    "temperature": kwargs.get("temperature", 0.4),
                    "top_p": 1,
                    "top_k": 32,
                }

                # Create the model
                model = genai.GenerativeModel('gemini-2.0-flash')

                # Generate the image
                response = model.generate_content(
                    f"Generate an image of {prompt}",
                    generation_config=generation_config,
                    stream=False
                )

                # Process the response
                has_content = False

                # Check if we have a response
                if response and hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            for part in candidate.content.parts:
                                if hasattr(part, 'text') and part.text and 'data:image' in part.text:
                                    has_content = True

                                    # Extract the base64 image data
                                    img_data = part.text.split(',')[1]
                                    image_bytes = base64.b64decode(img_data)

                                    # Yield the image
                                    yield {"message": {"role": "assistant", "image": image_bytes}}

                                    # Add a success message
                                    yield {"message": {"role": "assistant", "content": "Image generated successfully."}}

                # If no content was found, provide a fallback message
                if not has_content:
                    yield {"message": {"role": "assistant", "content": "I wasn't able to generate an image. Please try a different prompt or check your API key permissions."}}

            except Exception as img_error:
                error_message = f"Error generating image: {str(img_error)}"
                print(error_message)
                yield {"message": {"role": "error", "content": error_message}}

        except Exception as e:
            error_message = f"Image generation error: {str(e)}"
            print(f"Error in generate_image: {error_message}")  # Debug output
            yield {"message": {"role": "error", "content": error_message}}


class DeepSeekManager(ModelManager):
    """Manager for DeepSeek models."""

    def __init__(self):
        super().__init__()
        self.api_config = DeepSeekAPIConfig()
        self.llm_models = ["deepseek-chat", "deepseek-reasoner"]  # DeepSeek models
        self.embedding_models = []  # No embedding models for now

    def get_llm_models(self) -> List[str]:
        """Get list of available DeepSeek models."""
        return self.llm_models

    def get_embedding_models(self) -> List[str]:
        """Get list of embedding models (none for DeepSeek)."""
        # Fallback to available Ollama embedding models
        fallback = OllamaManager()
        return fallback.get_embedding_models()

    def save_api_key(self, api_key):
        """Save a new API key."""
        return self.api_config.set_api_key(api_key)

    @safe_execute("Getting DeepSeek response")
    def get_response(self, messages: List[Dict[str, Any]], **kwargs) -> Iterator[Dict[str, Any]]:
        """Get a streaming response from a DeepSeek model."""
        model_name = kwargs.get("model", "deepseek-chat")
        temperature = kwargs.get("temperature", 0.7)
        # context_size = kwargs.get("context_size", 4096)  # DeepSeek API might not use this directly

        # Check if API key is configured
        if not self.api_config.is_configured():
            raise ValueError("DeepSeek API key is not configured. Please set it in the settings.")

        # DeepSeek uses OpenAI-compatible API
        response_stream = get_deepseek_response(
            messages=messages,
            model=model_name,
            stream=True
        )

        for chunk in response_stream:
            yield {"message": {"role": "assistant", "content": chunk}}

    @safe_execute("Getting DeepSeek embedding")
    def get_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        """Get an embedding for the given text using fallback Ollama models."""
        fallback = OllamaManager()
        available = fallback.get_embedding_models()
        if not model or model not in available:
            model = available[0] if available else "nomic-embed-text"
        response = ollama.embeddings(model=model, prompt=text)
        return response.get("embedding", [])


class AnthropicManager(ModelManager):
    """Manager for Anthropic Claude models."""

    def __init__(self):
        super().__init__()
        self.api_config = AnthropicAPIConfig()
        self.llm_models = self.api_config.get_text_models()  # Claude models
        self.embedding_models = self.api_config.get_embedding_models()  # Empty list as Claude doesn't offer embeddings

    def get_llm_models(self) -> List[str]:
        """Get list of available Anthropic models."""
        return self.llm_models

    def get_embedding_models(self) -> List[str]:
        """Get list of embedding models (none for Claude)."""
        # Fallback to available Ollama embedding models
        fallback = OllamaManager()
        return fallback.get_embedding_models()

    def save_api_key(self, api_key):
        """Save a new API key."""
        return self.api_config.set_api_key(api_key)

    @safe_execute("Getting Claude response")
    def get_response(self, messages: List[Dict[str, Any]], **kwargs) -> Iterator[Dict[str, Any]]:
        """Get a streaming response from a Claude model."""
        model_name = kwargs.get("model", "claude-3-sonnet-20240229")
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 2048)

        # Check if API key is configured
        if not self.api_config.is_configured():
            raise ValueError("Anthropic API key is not configured. Please set it in the settings.")

        # Get streaming response using the helper function
        response_stream = get_anthropic_response(
            messages=messages,
            model=model_name,
            stream=True,
            max_tokens=max_tokens,
            temperature=temperature
        )

        for chunk in response_stream:
            yield {"message": {"role": "assistant", "content": chunk}}

    @safe_execute("Getting Claude embedding")
    def get_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        """Get an embedding for the given text using fallback Ollama models."""
        fallback = OllamaManager()
        available = fallback.get_embedding_models()
        if not model or model not in available:
            model = available[0] if available else "nomic-embed-text"
        response = ollama.embeddings(model=model, prompt=text)
        return response.get("embedding", [])


def create_model_manager(provider: str, api_key: Optional[str] = None) -> ModelManager:
    """Factory function to create the appropriate model manager."""
    if provider.lower() == "ollama":
        return OllamaManager()
    elif provider.lower() == "google":
        return GeminiManager(api_key)
    elif provider.lower() == "deepseek":
        return DeepSeekManager()
    elif provider.lower() == "anthropic":
        return AnthropicManager()
    else:
        raise ValueError(f"Unsupported model provider: {provider}")
