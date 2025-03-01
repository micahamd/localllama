# Enhanced LLM Chat

A modular, feature-rich chat interface for interacting with various large language models. This application provides a seamless experience with local models via Ollama and cloud models like Google's Gemini and Deepseek.

## Features

### Core Features
- **Multi-Provider Support**: Use models from Ollama or Google Gemini
- **RAG (Retrieval-Augmented Generation)**: Enhance responses with knowledge from your documents
- **Conversation Management**: Save, load, and manage chat sessions
- **File Processing**: Drop files directly into the chat or process files in batch mode
- **Image Support**: Send images to vision-capable models
- **System Instructions**: Customize model behavior with system prompts

### Advanced Features
- **RAG Visualization**: Understand which documents influenced the model's response
- **Semantic Chunking**: Improved document splitting for better context retrieval
- **Persistent Settings**: Save your preferences between sessions
- **Error Handling**: Informative error messages and robust exception handling
- **Batch Processing**: Process multiple files with the same prompt
- **Highlighting**: Code block detection and syntax highlighting

## Getting Started

### Prerequisites
- Python 3.8+
- [Ollama](https://ollama.ai/) for local models
- (Optional) Google API key for Gemini models

### Installation

1. Clone this repository:
```
git clone https://github.com/yourusername/enhanced-llm-chat.git
cd enhanced-llm-chat
```

2. Install required dependencies:
```
pip install -r requirements.txt
```

3. Run the application:
```
python main.py
```

## Usage Guide

### Basic Chat
1. Select a model provider (Ollama or Google)
2. Choose an LLM model from the dropdown
3. Type your message in the input field
4. Click "Send" or press Ctrl+Enter

### Working with Files
- **Drop Files**: Drag and drop files directly into the chat window
- **Batch Process**: Process multiple files with the same prompt
- **File Types**: Supports text files, PDFs, Word documents, images, and more

### Using RAG
1. Select an embedding model from the dropdown
2. Click "Select RAG Files" to choose reference documents
3. Adjust chunk size and semantic chunking options if needed
4. Ask questions related to your documents
5. Click "Show RAG Visualization" to see which chunks were used

### Managing Conversations
- **New Conversation**: Start a fresh chat session
- **Save Conversation**: Save the current conversation to a file
- **Load Conversation**: Load a previously saved conversation
- **Recent Conversations**: Double-click on recent conversations in the sidebar

### Customization
- **Temperature**: Control model creativity (higher = more creative)
- **Context Size**: Adjust the context window size for the model
- **System Instructions**: Set custom instructions for the model's behavior

## Architecture

The application is built with a modular architecture for maintainability:

- **main.py**: Entry point and UI coordination
- **settings.py**: Manages persistent user preferences
- **conversation.py**: Handles chat history and conversation management
- **models_manager.py**: Abstracts different model providers
- **rag_module.py**: Implements retrieval-augmented generation
- **rag_visualizer.py**: Visualizes RAG process and results
- **error_handler.py**: Provides robust error management

## Requirements

- tkinter (for the GUI)
- tkinterdnd2 (for drag-and-drop functionality)
- ollama (for local model integration)
- google-generativeai (for Gemini integration)
- chromadb (for vector database)
- sentence-transformers (for semantic chunking)
- PIL/Pillow (for image handling)
- markitdown (for file parsing)
- nltk (for text processing)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
