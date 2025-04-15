# Local(o)llama chatbot

A modular, feature-rich Python-based chat interface for interacting with local (Ollama) and proprietary (Google, Deepseek, Anthropic) large language models.

## Features

- **Multiple Developers**: Switch between  Ollama, Google Gemini, Deepseek, or Anthropic models within a single session.
- **RAG (Retrieval-Augmented Generation)**: Use local/remote embedding models, with customizable chunk sizes, to retrieve document context.
- **Conversation Management**: Chat sessions can be saved and loaded as JSON files.
- **Temperature and Context customization**: Sliders manage these parameters directly in the UI for all models.
- **File Processing with MarkItDown**: Utilizes Microsoft's @markitdown package to process nearly all files into ML-readable markdown.
- **MultiMedia Support**: Process images, audio files, and YouTube videos.
- **System Instructions**: Customize model behavior with system prompts.
- **Batch Processing**: Process multiple files with the same prompt.
- **ZIP File Processing**: Extract content from ZIP archives directly.
- **URL Content Extraction**: Process web content from URLs using @crawlAI.
- **Automatic Dependency Management**: Dynamically install required dependencies

## Getting Started

### Prerequisites
- Python 3.8+
- [Ollama](https://ollama.ai/) for local models
- (Optional) Google API key for Gemini models
- (Optional) Deepseek API key for Deepseek models
- (Optional) Anthropic API key for Claude models
- (Optional) Dependencies for specific file types will be installed automatically as needed

### Installation

1. Clone this repository:
```
git clone https://github.com/micahamd/localllama.git
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
1. Select a model provider and an associated LLM model
2. Type your message in the input field, and click 'Send' or press Enter.

### Working with Files
- **Drop Files**: Drag and drop files directly into the chat window
- **Batch Process**: Process multiple files with the same prompt
- **File Types Supported**: 
  - **Documents**: PDFs, Word documents, PowerPoint presentations, Excel spreadsheets
  - **Images**: JPG, PNG, GIF, BMP with preview display
  - **Audio**: MP3, WAV, FLAC, M4A with automatic transcription
  - **Archives**: ZIP files with content extraction
  - **Web Content**: YouTube videos and general URLs
  - **Text Formats**: TXT, MD, JSON, CSV, XML
  - **E-books**: EPUB format
- **URL Processing**: Paste a URL to automatically extract and process its content
- **YouTube Integration**: Paste a YouTube URL to extract video transcription

### Using RAG
1. Select an embedding model from the dropdown
2. Click "Select RAG Files" to choose reference documents
4. Ask questions related to your documents
5. Click "Show RAG Visualization" to see which chunks were used to inform the response

### Working with Media and Web Content

#### Audio Files
1. Drag and drop an audio file (MP3, WAV, etc.) into the chat window to automatically transcribe the audio content
2. A preview of the transcription will be displayed in the chat
3. Ask questions about the transcribed content

#### YouTube Videos
1. Paste a YouTube URL directly into the chat input field and press Enter
2. The application will fetch the video's transcription
3. A preview with title, URL, and transcription excerpt will be displayed
4. Ask questions about the video content

#### Web Content
1. Paste any URL into the chat input field and press Enter
2. The application will extract the content from the webpage
3. Ask questions about the extracted content

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
- **models_manager.py**: Abstracts different model providers (Ollama, Google, Deepseek, Anthropic)
- **rag_module.py**: Implements retrieval-augmented generation
- **rag_visualizer.py**: Visualizes RAG process and results
- **error_handler.py**: Provides robust error management
- **html_text.py**: Handles HTML and Markdown rendering in the UI

### File Processing Architecture

The application uses the MarkItDown library to process various file types:

1. **File Detection**: Automatically identifies file types based on extension or URL pattern
2. **Content Extraction**: Uses MarkItDown to extract content from files in a consistent Markdown format
3. **Dependency Management**: Automatically installs required dependencies for specific file types
4. **Preview Generation**: Creates appropriate previews for different file types (images, audio, YouTube, etc.)
5. **Content Integration**: Seamlessly integrates extracted content into the conversation

## Requirements

### Core Dependencies
- **GUI**: tkinter, tkinterdnd2 (for drag-and-drop functionality)
- **LLM Integration**: ollama, google-generativeai, anthropic
- **RAG**: chromadb, sentence-transformers, nltk
- **Media Handling**: PIL/Pillow (for image handling)
- **File Processing**: markitdown with optional extensions

### MarkItDown Optional Dependencies
- **Document Processing**: [markitdown[pdf,docx,pptx,xlsx,xls]]
- **Audio Processing**: [markitdown[audio-transcription]]
- **YouTube Integration**: [markitdown[youtube-transcription]]
- **Advanced Document Analysis**: [markitdown[az-doc-intel]]

See requirements.txt for a complete list of dependencies.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
