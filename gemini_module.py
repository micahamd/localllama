import os
from typing import Optional, List
import google.generativeai as genai

class GeminiChat:
    def __init__(self):
        # API key from environment variable
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise EnvironmentError("GOOGLE_API_KEY environment variable not set")
        genai.configure(api_key=self.api_key)
        
        # Model configuration based on current list
        self.model_name_mapping = {
            'flash2':'gemini-flash-2.0-exp',
            'flash': 'gemini-1.5-flash',  
            'pro': 'gemini-1.5-pro'
        }
        
    def get_response(self, messages: List[dict], temperature: float = 0.7, max_tokens: int = 4096):
        """
        Get a response from the Gemini model.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            temperature: Controls randomness in the response
            max_tokens: Maximum number of tokens to generate
        
        Returns:
            Generator yielding response chunks
        """
        try:
            # Configure the model
            generation_config = {
                "temperature": temperature,
                "top_p": 0.95,
                "top_k": 60,
                "max_output_tokens": max_tokens
            }
            
            # Get the model
            model = genai.GenerativeModel('gemini-1.5-pro', generation_config=generation_config)
            
            # Format messages for Gemini
            formatted_messages = []
            system_message = None
            
            for msg in messages:
                if msg['role'] == 'system':
                    system_message = msg['content']
                else:
                    content = msg['content']
                    if 'images' in msg:
                        # Handle image input if present
                        # Note: Gemini expects images in a different format, would need conversion
                        pass
                    formatted_messages.append(content)
            
            # Combine system message with user message if present
            if system_message:
                formatted_messages[0] = f"{system_message}\n\n{formatted_messages[0]}"
            
            # Generate response
            response = model.generate_content(formatted_messages, stream=True)
            
            # Stream the response
            for chunk in response:
                if chunk.text:
                    yield {'message': {'content': chunk.text}}
                
        except Exception as e:
            yield {'message': {'content': f"Error: {str(e)}"}}

    def list_models(self):
        """
        List available Gemini models.
        Returns a list of model names.
        """
        return list(self.model_name_mapping.keys())
