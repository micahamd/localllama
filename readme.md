# Local(o)llama chatbot

A modular, feature-rich Python-based chat interface for interacting with local (Ollama) and proprietary (Google, Gemini, Deepseek, Anthropic) large language models.

## Features

### Core Capabilities
- **Multiple LLM Providers**: Switch between Ollama, Google Gemini, Deepseek, or Anthropic models within a single session
- **RAG (Retrieval-Augmented Generation)**: Use local/remote embedding models with customizable chunk sizes to retrieve document context
- **Conversation Management**: Save and load chat sessions as JSON files with full history preservation
- **Temperature and Context Customization**: Real-time sliders to manage model parameters directly in the UI

### Agent Mode (Multi-Agent Workflows)
- **Sequential Agent Execution**: Stage multiple agents with different models, prompts, and tools
- **Agent-to-Agent Communication**: Use `{{Agent-X}}` placeholders to pass outputs between agents
- **Per-Agent Tool Configuration**: Each agent can have independent Read File, Write File, and Web Search tools
- **Loop Control**: Configure loop limits for iterative agent sequences
- **Save/Load Agent Sequences**: Persist reusable workflows to `agents/` directory
- **Real-Time Execution Monitoring**: Live status updates for each agent in the sequence

### File Processing Tools
- **Panda CSV Analysis Tool**: Row-by-row CSV processing with dynamic column referencing and LLM-powered analysis
- **MarkItDown Integration**: Process documents, images, audio, and more into ML-readable markdown
- **Batch Processing**: Process multiple files with the same prompt
- **ZIP File Processing**: Extract and process content from ZIP archives
- **Drag-and-Drop Support**: Simply drop files into the chat for instant processing

### Advanced Tools
- **Read File Tool**: Reference files in prompts using `<<filename>>` syntax - content automatically injected
- **Write File Tool**: AI can create files with `[[filename]]` syntax - content automatically saved
- **Web Search Integration**: Real-time web search using crawl4ai for up-to-date information
- **Memory Control Program (MCP)**: Persistent knowledge base with automatic memory retrieval
- **URL Content Extraction**: Process web pages and YouTube videos directly from URLs

### Media Support
- **Images**: JPG, PNG, GIF, BMP with preview display
- **Audio**: MP3, WAV, FLAC, M4A with automatic transcription
- **Video**: YouTube transcription support
- **Documents**: PDF, Word, Excel, PowerPoint, EPUB, and more
- **Text Formats**: TXT, MD, JSON, CSV, XML, HTML

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
cd localllama
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
1. Select a model provider (Ollama, Google, Deepseek, or Anthropic)
2. Choose a specific model from the dropdown
3. Type your message and press Send or Enter
4. Optionally enable MCP for enhanced responses with relevant memories

### Agent Mode - Multi-Agent Workflows

Agent Mode allows you to create sophisticated multi-step workflows where each agent can have different models, tools, and prompts. Agents execute sequentially and can pass data to each other.

#### Staging Agents
1. **Enable Agent Mode**: Check the **"Agent Tool"** checkbox in the sidebar
2. **Enter Agent Prompts**: Type each agent's instructions and press Send
   - The system captures the agent definition instead of executing immediately
   - Each agent saves the current model, temperature, and tool settings
3. **Stage Multiple Agents**: Repeat step 2 for each agent in your workflow
4. **Disable Agent Mode**: Uncheck **"Agent Tool"** when done staging

#### Configuring Agents
1. Click **"Configure Agents"** to open the management window
2. **Review Agents**: See all staged agents with their settings
3. **Reorder**: Drag agents to change execution order
4. **Edit**: Modify agent prompts, models, or tool settings
5. **Set Loop Limits**: Configure how many times an agent can loop (default: 0 = no loops)
6. **Delete**: Remove unwanted agents
7. **Save/Load**: Persist sequences to `agents/` directory for reuse

#### Agent-to-Agent Communication
- Use `{{Agent-1}}`, `{{Agent-2}}`, etc. to reference previous agent outputs
- Example workflow:
  ```
  Agent 1: "Summarize this document: <<report.pdf>>"
  Agent 2: "Based on {{Agent-1}}, identify key recommendations"
  Agent 3: "Create action items from {{Agent-2}} and save to [[action_items.txt]]"
  ```

#### Agent Tools (Per-Agent Configuration)
Each agent can independently enable:
- **Read File**: Use `<<filename>>` to inject file content into prompts
- **Write File**: Model can save files with `[[filename]]` in response
- **Web Search**: Automatic web search for current information

**Important**: Tools are opt-in only. Check the tool boxes when staging each agent to enable them.

#### Execution
1. Click **"Run Agent"** to start the sequence
2. Monitor real-time progress in the chat display
3. Each agent shows:
   - Status updates (file reads, web searches, file writes)
   - Model responses
   - Tool execution results
4. Final outputs are displayed and can be referenced in subsequent runs

#### Example Workflows

**Research & Documentation Pipeline:**
```
Agent 1 [Web Search ✓]: "Search for Python 3.12 new features"
Agent 2 [Write File ✓]: "Create guide from {{Agent-1}} in [[py312_guide.md]]"
Agent 3 [Read File ✓]: "Read <<py312_guide.md>> and add code examples"
Agent 4 [Write File ✓]: "Save enhanced version to [[py312_final.md]]"
```

**Data Analysis Workflow:**
```
Agent 1 [Read File ✓]: "Analyze data in <<sales.csv>> and find trends"
Agent 2 [Web Search ✓]: "Find industry benchmarks for {{Agent-1}} metrics"
Agent 3 [Write File ✓]: "Compare findings and save report to [[analysis.txt]]"
```

For detailed agent documentation, see: `AGENT_TOOLS_INTEGRATION.md` and `AGENT_TOOLS_QUICKREF.md`

---

### Panda CSV Analysis Tool

Process CSV files row-by-row with LLM-powered analysis using dynamic column referencing.

#### Quick Start
1. **Enable the Tool**: Check **"Panda CSV Analysis Tool"** in the Tools section
2. **Select CSV File**: Choose your CSV file in the file picker
3. **Write Your Prompt**: Use special syntax to reference columns:
   - `{C1}`, `{C2}`, `{C3}` - Read from columns 1, 2, 3...
   - `{{C4}}`, `{{C5}}` - Write to new columns 4, 5...
   - `{R1}`, `{R1-10}`, `{R1,3,5}` - Process specific rows (optional)

#### Example: Essay Grading
```prompt
Grade the student essay in {C2} and provide feedback.

Output format:
COLUMN_3: [score 0-10]
COLUMN_4: [brief feedback comment]
```

#### Features
- **Preview Mode**: Test on first 3 rows before full processing
- **Row Specification**: Process specific rows or ranges
- **Dynamic Columns**: Create new output columns automatically
- **Save-After-Each-Row**: Incremental saves for safety
- **Uses Chat Settings**: Respects current model, temperature, etc.

**Important**: CSV Tool cannot be used simultaneously with Agent Mode due to architectural constraints.

For comprehensive CSV tool documentation, see: `PANDA_CSV_GUIDE.md` and `PANDA_CSV_QUICKREF.md`

---

### Working with Files

The chatbot supports comprehensive file processing using Microsoft's MarkItDown library.

#### Drag-and-Drop Support
- Simply drag files directly into the chat window
- Automatic file type detection and processing
- Preview generation for images, audio, and documents

#### Supported File Types
- **Documents**: PDF, DOCX, DOC, PPTX, PPT, XLSX, XLS with full content extraction
- **Images**: JPG, PNG, GIF, BMP with inline preview and analysis
- **Audio**: MP3, WAV, FLAC, M4A with automatic transcription (uses Whisper)
- **Archives**: ZIP files with content extraction and processing
- **Web Content**: Direct URL processing for webpages and YouTube videos
- **Text Formats**: TXT, MD, JSON, CSV, XML, HTML
- **E-books**: EPUB format support

#### Batch Processing
1. Select multiple files using the file picker
2. Enter a common prompt to apply to all files
3. Process files individually with the same instruction
4. Results displayed sequentially in chat

#### URL Processing
- Paste any URL directly into the chat input
- Automatic webpage content extraction using crawl4ai
- YouTube video transcription support
- Extracted content becomes part of conversation context

---

### File Tools (Read & Write)

#### Read File Tool
Automatically inject file content into your prompts.

**How to Use:**
1. Enable **"Read File"** in the Tools section
2. Reference files using `<<filename>>` syntax in your messages
3. File content is automatically read and injected before sending to model

**Examples:**
```
"Analyze the data in <<sales_report.csv>>"
"Following instructions in <<guide.docx>>, process <<input.pdf>>"
"Compare <<version1.txt>> with <<version2.txt>>"
```

**Supports**: All MarkItDown formats (DOCX, PDF, images, audio, etc.)

#### Write File Tool  
Let the AI create and save files automatically.

**How to Use:**
1. Enable **"Write File"** in the Tools section
2. Ask AI to save content and specify path with `[[filename]]` syntax
3. AI includes `[[path/to/file.ext]]` in response to trigger file creation

**Examples:**
```
"Create a summary report and save as [[./reports/summary.txt]]"
"Generate Python script and save as [[scripts/data_processor.py]]"
"Write JSON config and save as [[config/settings.json]]"
```

**Features:**
- Automatic content extraction from code blocks
- Safety checks and backups
- Support for all text-based formats
- Error handling with detailed feedback

**Syntax Reference:**
- Read: `<<filename>>` (angle brackets)
- Write: `[[filename]]` (square brackets)

---

### Web Search Integration

Enable real-time web search to enhance AI responses with current information.

1. Enable **"Web Search"** in the Tools section
2. Ask questions requiring up-to-date information
3. The system automatically searches using crawl4ai
4. Search results are appended to your prompt before sending to model
5. Model provides informed answers based on current web data

**Best for**: Current events, recent news, latest documentation, trending topics

---

### Using RAG (Retrieval-Augmented Generation)

Enhance responses with relevant context from your documents.

1. Select an embedding model from the dropdown
2. Click **"Select RAG Files"** to choose reference documents
3. Ask questions related to your documents
4. Click **"Show RAG Visualization"** to see which chunks informed the response

**Features:**
- Customizable chunk sizes
- Multiple embedding model options
- Visual chunk relevance display
- Seamless integration with chat context

---

### Managing Conversations
- **New Conversation**: Start a fresh chat session
- **Save Conversation**: Save current conversation to JSON file
- **Load Conversation**: Restore previously saved conversations
- **Recent Conversations**: Quick access via sidebar (double-click to load)
- **Auto-Save**: Conversations persist across sessions

### Customization Options
- **Temperature**: Control model creativity (0.0 = deterministic, 2.0 = very creative)
- **Context Size**: Adjust context window (model-dependent)
- **System Instructions**: Set custom behavior instructions for the model
- **Model Selection**: Switch providers and models mid-conversation

---

### Memory Control Program (MCP)

A persistent knowledge base that enhances AI responses with relevant stored information.

#### Getting Started
1. Open MCP panel from Tools menu
2. Click **"Start Server"** to activate memory system
3. Add memories manually or import from files
4. MCP automatically retrieves relevant memories during conversations

#### Adding Memories
- **Manual Entry**: Click **"Add Memory"** to enter text directly
- **File Import**: Click **"Import File"** to convert documents to memories using MarkItDown
- **Automatic**: Conversations auto-saved as memories when server is running

#### Importing Files as Memories
1. Click **"Import File"** in MCP panel
2. Select any supported file type (documents, code, images, audio, etc.)
3. File converted to markdown automatically
4. Edit title, content, and tags before saving
5. Split large files into multiple memories for better retrieval

#### Memory Organization
- **Tags**: Categorize and organize with custom tags
- **Search**: Find specific memories using search box
- **Edit/Delete**: Full memory management capabilities
- **Relevance**: Top 3 most relevant memories included in model context

#### How It Works
- MCP searches memories when you ask questions
- Relevant memories automatically included in context
- Start/stop server to control memory usage
- Improves AI responses with personalized knowledge base

---

## Architecture & File Structure

The application uses a modular architecture for easy maintenance and extensibility.

### Core Modules
- **main.py**: Entry point, UI coordination, and main application logic
- **settings.py**: Persistent user preferences and configuration management
- **conversation.py**: Chat history and conversation state management
- **models_manager.py**: Unified interface for multiple LLM providers (Ollama, Google, Deepseek, Anthropic)
- **error_handler.py**: Centralized error handling and logging

### Feature Modules
- **rag_module.py**: Retrieval-Augmented Generation implementation
- **rag_visualizer.py**: Visual representation of RAG chunk selection
- **mcp_server.py**: Memory Control Program server implementation
- **mcp_ui.py**: MCP user interface components
- **mcp_file_import.py**: File-to-memory conversion using MarkItDown
- **html_text.py**: HTML and Markdown rendering in chat display

### Agent System
- **agent_sequence_store.py**: Persists agent sequences to `agents/*.agent.json` with metadata
- **agent_cache.py**: Temporary cache for staging agents (survives until cleared)

### Tool Modules  
- **panda_csv_tool.py**: Standalone CSV processing with dynamic column referencing
- **prompt_manager.py**: Prompt template management and utilities

### API Configuration
- **anthropic_api_config.py**: Anthropic Claude API integration
- **gemini_api_config.py**: Google Gemini API integration
- **deepseek_api_config.py**: Deepseek API integration

### Data Directories
- **agents/**: Saved agent sequence definitions (`.agent.json` files)
- **conversations/**: Saved conversation history (`.json` files)
- **memories/**: MCP memory storage
- **chroma_db/**: ChromaDB vector database for RAG
- **generated_images/**: Generated/stored images
- **prompts/**: Custom prompt templates

### File Processing Pipeline

The application leverages Microsoft's MarkItDown library for unified file processing:

1. **Automatic Detection**: Identifies file types by extension or URL pattern
2. **Content Extraction**: Converts files to consistent Markdown format
3. **Smart Dependencies**: Auto-installs required packages on-demand (audio, YouTube, etc.)
4. **Preview Generation**: Creates type-appropriate previews (thumbnails, waveforms, etc.)
5. **Context Integration**: Seamlessly merges extracted content into conversations

---

## Requirements & Dependencies

### Core Dependencies
- **GUI**: `tkinter`, `tkinterdnd2` (drag-and-drop support)
- **LLM Integration**: `ollama`, `google-generativeai`, `anthropic`, `openai`
- **RAG**: `chromadb`, `sentence-transformers`, `nltk`
- **Data Processing**: `pandas` (CSV tool), `numpy`
- **Media**: `Pillow` (image processing)
- **Web**: `crawl4ai` (web search and content extraction)
- **File Processing**: `markitdown` (base + optional extensions)

### MarkItDown Optional Extensions
Install as needed for specific file types:
- **Documents**: `pip install markitdown[pdf,docx,pptx,xlsx,xls]`
- **Audio Transcription**: `pip install markitdown[audio-transcription]`
- **YouTube Videos**: `pip install markitdown[youtube-transcription]`
- **Advanced OCR**: `pip install markitdown[az-doc-intel]`

### Installation
```bash
# Basic installation
pip install -r requirements.txt

# Install all optional extensions
pip install markitdown[pdf,docx,pptx,xlsx,xls,audio-transcription,youtube-transcription]
```

**Note**: The application automatically detects and installs missing dependencies when needed.

---

## Documentation

### Feature Guides
- **Agent Mode**: See `AGENT_TOOLS_INTEGRATION.md` and `AGENT_TOOLS_QUICKREF.md`
- **CSV Tool**: See `PANDA_CSV_GUIDE.md` and `PANDA_CSV_QUICKREF.md`
- **Testing**: See `TESTING_GUIDE.md`
- **Architecture**: See `Agent_Mode_Implementation_Strategy.md`

### Quick Reference
- Agent syntax: `{{Agent-X}}` for outputs, `<<file>>` for reads, `[[file]]` for writes
- CSV syntax: `{CX}` for read columns, `{{CX}}` for write columns, `{RX}` for rows
- All tool checkboxes are **opt-in only** - tools don't activate unless explicitly enabled

---

## Contributing

Contributions welcome! Key areas for contribution:
- Additional file format support
- New tool integrations
- UI/UX improvements
- Performance optimizations
- Documentation enhancements

Please submit Pull Requests to the main repository.

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Version**: 2.0.0  
**Last Updated**: October 6, 2025  
**Status**: Production Ready
