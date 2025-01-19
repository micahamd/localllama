# Local(o)llama chatbot

A feature-rich Python application for seamlessly interacting with local Ollama and Google's Gemini models. For Gemini functionality, ensure to include a GOOGLE_API_KEY in the .env file.

## Features

### Core Functionality
- 💬 Real-time chat interface with streaming responses
- 🔄 Comprehensive chat history support with optional inclusion
- 🤖 Support for both Ollama and Gemini models
- 🎯 Precise parameter controls:
  - Temperature adjustment (0.0 to 1.0) for response creativity
  - Context window size (1000 to 128000 tokens)
  - Customizable system instructions

### File Handling
- 📁 Drag-and-drop support for multiple file types:
  - Documents (.docx, .pdf, .txt, .csv)
  - Images (for visual analysis)
- 📋 Optional file content inclusion in prompts
- 🗑️ Easy file clearing and management

### Advanced Features
- 📊 RAG (Retrieval-Augmented Generation):
  - Vector embeddings stored in Chroma DB
  - Configurable chunk sizes
  - Optional semantic chunking (more accurate but more resource-heavy)
  - Support for multiple embedding models
- 📦 Batch file processing capabilities
- ⚡ Streaming responses for real-time interaction

## Prerequisites

- Python 3.x
- Ollama (for local models)
- Google API Key (for Gemini models)
- Windows/Linux/MacOS

## Quick Start

To get started with the application, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/micahamd/localllama.git
    cd localllama
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up environment variables:**
    -   Create a `.env` file in the root directory of the project.
    -   Add your Google API key if you plan to use Gemini models:
        ```
        GOOGLE_API_KEY=your_api_key_here
        ```

4.  **Run the server:**
    ```bash
    python server.py
    ```

5.  **Open the application in your browser:**
    - Navigate to `frontend/index.html` in your browser.

## Usage Guide

### Model Selection
- Choose between Ollama or Google (Gemini) models.
- Select your preferred LLM model.
- For RAG, choose an embedding model (automatically set for Gemini).

### Chat Controls
- Adjust temperature for response creativity.
- Set context window size for longer conversations.
- Customize system instructions for specific behaviors.
- Toggle chat history inclusion.

### File Operations
- Drag and drop files into the interface.
- Use the "Include file content?" checkbox to control file inclusion.
- Clear files using the "Clear File" button.
- Process multiple files in batch mode.

### RAG Functionality
- Click the RAG button to select reference documents.
- Adjust chunk size and semantic chunking settings.
- RAG context will automatically be included in relevant queries.

## License

Distributed under the MIT License.

## Acknowledgements

Special thanks to Ollama and Google for making this possible.
