# Local(o)llama Chatbot - Tools & Functions Reference

**Version 2.0** | Complete Feature Reference

---

## Table of Contents

### Core Features
1. [Model Selection](#model-selection)
2. [Conversation Management](#conversation-management)
3. [Temperature & Context Controls](#temperature-context-controls)

### Agent System
4. [Agent Mode](#agent-mode)
5. [How Agent Mode Works](#how-agent-mode-works)
6. [Staging Agents](#staging-agents)
7. [Configuring Agents](#configuring-agents)
8. [Agent Communication](#agent-communication)
9. [Agent Execution Flow](#agent-execution-flow)

### Agent Tools (Per-Agent Configuration)
10. [Read File Tool](#read-file-tool)
11. [Write File Tool](#write-file-tool)
12. [Web Search Tool](#web-search-tool)

### File Processing Tools
13. [CSV Analysis Tool (Panda CSV)](#csv-analysis-tool)
14. [Document Upload & Processing](#document-upload-processing)
15. [Drag & Drop File Processing](#drag-drop-file-processing)
16. [Batch File Processing](#batch-file-processing)

### Advanced Systems
17. [Memory Control Program (MCP)](#memory-control-program)
18. [RAG System](#rag-system)
19. [Prompt Manager](#prompt-manager)

### Additional Features
20. [Image Processing](#image-processing)
21. [Audio Transcription](#audio-transcription)
22. [URL Content Extraction](#url-content-extraction)
23. [ZIP File Processing](#zip-file-processing)

### Troubleshooting
24. [Common Issues](#common-issues)
25. [File Write Problems](#file-write-problems)

---

## Model Selection

**Function:** Choose LLM provider and specific model

**Providers:**
- **Ollama** - Local models (llama3.2, mistral, codellama, etc.)
- **Google Gemini** - gemini-pro, gemini-1.5-pro, gemini-1.5-flash
- **Deepseek** - deepseek-chat, deepseek-coder
- **Anthropic Claude** - claude-3-opus, claude-3-sonnet, claude-3-haiku

**How to Use:**
1. Select provider from dropdown menu
2. Choose specific model from model list
3. Model switches immediately for next message
4. Different models can be used in same conversation

**Model Characteristics:**
- **Local (Ollama):** Fast, private, offline, requires installation
- **Cloud (Gemini/Deepseek/Claude):** Larger models, requires API key, internet connection

[Back to top](#table-of-contents)

---

## Conversation Management

**Function:** Save and load chat sessions

**Features:**
- **Save Conversation:** Stores current chat as JSON file
- **Load Conversation:** Restore previous session with full history
- **Auto-naming:** Suggests filename based on first message
- **Rename:** Change conversation file names
- **History:** All saved in `conversations/` folder

**How to Use:**
- **File → Save Conversation:** Enter name, saves current chat
- **File → Load Conversation:** Select file, restores conversation
- **File → Rename Conversation:** Change existing conversation name
- **File → New Conversation:** Clear current chat, start fresh

**Save Format:**
Clean JSON format with only user/assistant messages (excludes system/status messages)

[Back to top](#table-of-contents)

---

## Temperature & Context Controls

**Function:** Adjust model behavior in real-time

**Temperature Slider (0.0 - 2.0):**
- **Low (0.0-0.5):** Focused, deterministic, factual responses
- **Medium (0.5-1.0):** Balanced creativity and consistency
- **High (1.0-2.0):** Creative, varied, unpredictable outputs

**Context Size Slider:**
- Controls how much conversation history model remembers
- **Higher:** More context retained, slower responses
- **Lower:** Less memory, faster responses

**Other Parameters:**
- **Top-k:** Limits vocabulary choices (lower = more focused)
- **Top-p:** Nucleus sampling threshold
- **Repeat Penalty:** Reduces repetition (higher = more varied)

**When to Adjust:**
- Creative writing → High temperature
- Code/facts → Low temperature
- Long conversations → Increase context size
- Quick responses → Decrease context size

[Back to top](#table-of-contents)

---

## Agent Mode

**Function:** Create multi-agent workflows where agents execute sequentially

**What is Agent Mode?**
Sequential execution system that allows you to:
- Define multiple agents with different models and prompts
- Execute them in order automatically
- Pass data between agents
- Configure per-agent tool permissions (Read/Write/Web)
- Create complex workflows and pipelines

**Key Concepts:**
- **Staging:** Define agents while Agent Mode checkbox is ON
- **Configuration:** Manage agents before execution
- **Execution:** Run the complete sequence
- **Communication:** Agents reference each other using `{{Agent-X}}`

**Use Cases:**
- Research → Analysis → Report workflows
- Data extraction → Processing → Storage pipelines
- Multi-step content creation
- Iterative refinement processes

[See How Agent Mode Works →](#how-agent-mode-works)

[Back to top](#table-of-contents)

---

## How Agent Mode Works

**Complete Workflow:**

**1. Enable Agent Mode**
- Check the "Agent Tool" checkbox in sidebar
- Status bar shows "Agent Mode: Staging agents..."

**2. Stage Agents**
- Type each agent's prompt in chat input
- Press Send → Agent is staged (NOT executed yet)
- Current model + temperature + tool settings captured
- Repeat for each agent in your workflow

**3. Lock Sequence**
- Uncheck "Agent Tool" checkbox
- Sequence is locked and ready

**4. Configure (Optional)**
- Click "Configure Agents" button
- Review, edit, reorder, or delete agents
- Set loop limits if needed
- Save sequence for reuse

**5. Execute**
- Click "Run" in Configure Agents window
- Agents execute sequentially
- Real-time status updates shown
- Each agent's output available to next agent

**Agent Properties Captured:**
- Model selection (e.g., llama3.2, gemini-pro)
- Temperature setting
- System prompt (if any)
- Tool permissions (Read File, Write File, Web Search)
- User message/prompt

[See Staging Agents →](#staging-agents) | [See Configuring Agents →](#configuring-agents)

[Back to top](#table-of-contents)

---

## Staging Agents

**Function:** Create agent definitions during staging phase

**Steps:**

1. **☑️ Enable "Agent Tool" checkbox**
   - Located in sidebar under Tools section
   - Enables staging mode

2. **Enter Agent Prompts**
   - Type prompt in chat input
   - Press Send or Enter
   - Agent staged with current settings
   - Message NOT sent to model yet

3. **Repeat for Each Agent**
   - Change model/temperature if needed
   - Toggle tools on/off for this agent
   - Type next prompt
   - Press Send

4. **☐ Disable "Agent Tool" checkbox**
   - Locks the sequence
   - Ready for configuration or execution

**What Gets Captured:**
- Current selected model
- Current temperature value
- Tool checkbox states (Read/Write/Web)
- Your prompt text
- System prompt (if set)

**Example:**
```
[Agent Tool ☑️]
Model: llama3.2 | Temp: 0.3

User: "Analyze sales_data.csv and find top 3 trends"
→ Agent 1 staged (llama3.2, temp 0.3, no tools)

[Enable Read File tool]
Model: gemini-pro | Temp: 0.7

User: "Read <<sales_data.csv>> and extract key metrics"
→ Agent 2 staged (gemini-pro, temp 0.7, Read File enabled)

[Agent Tool ☐] → Sequence locked with 2 agents
```

**Important:**
- Agents are NOT executed during staging
- Each agent can have different settings
- Order matters - agents execute top to bottom
- Can stage up to 10 agents (configurable)

[See Configuring Agents →](#configuring-agents)

[Back to top](#table-of-contents)

---

## Configuring Agents

**Function:** Review, edit, reorder, and manage staged agents before execution

**Access:** Click "Configure Agents" button in sidebar

**Configuration Window Layout:**

**Left Panel: Agent List**
- Shows all staged agents
- Click to select and preview
- Displays agent number and title

**Right Panel: Preview**
- Shows selected agent details:
  - Model
  - Temperature
  - System prompt
  - Tools enabled
  - Message content

**Actions Available:**

**1. Edit Agent**
- Click "Edit" button
- Modify prompt, model, temperature, tools
- Save changes

**2. Reorder Agents**
- Select agent
- Click "Move Up" or "Move Down"
- Execution order changes

**3. Delete Agent**
- Select agent
- Click "Delete"
- Removes from sequence

**4. Set Loop Limit**
- Spinner control at bottom
- Default: 0 (no loops)
- Set > 0 for iterative execution

**5. Save Sequence**
- Click "Save Sequence"
- Enter name
- Saves to `agents/` folder as `.agent.json`
- Can reload later

**6. Load Sequence**
- Click "Load Sequence"
- Select saved sequence
- Replaces current agents

**7. Run Sequence**
- Click "Run" button
- Executes all agents in order
- Window stays open showing progress

**Agent Information Display:**
```
Agent-1
━━━━━━━━━━━━━━━━━━━━━━━━
Model: llama3.2:latest
Temperature: 0.7
System: You are a helpful assistant.

Tools:
✓ Read File
✗ Write File  
✗ Web Search

Message:
"Analyze the data and find trends"
```

[See Agent Execution Flow →](#agent-execution-flow)

[Back to top](#table-of-contents)

---

## Agent Communication

**Function:** Pass outputs between agents using placeholders

**Syntax:** `{{Agent-X}}` where X is the agent number (1, 2, 3, etc.)

**How It Works:**
1. Agent executes and produces output
2. Next agent's prompt contains `{{Agent-X}}`
3. Placeholder replaced with previous agent's response
4. New agent receives modified prompt

**Example Workflow:**

**Agent 1:** No tools
```
Prompt: "List the main features of Python 3.12"

Output: "1. Pattern matching improvements
2. Better type hints
3. Performance enhancements
4. New f-string syntax"
```

**Agent 2:** No tools
```
Prompt: "Explain {{Agent-1}} in detail for beginners"

What Agent 2 receives:
"Explain 1. Pattern matching improvements
2. Better type hints
3. Performance enhancements
4. New f-string syntax in detail for beginners"

Output: [Detailed explanation...]
```

**Agent 3:** Write File enabled
```
Prompt: "Create a tutorial guide about {{Agent-1}} and save to [[python312_guide.md]]"

What Agent 3 receives:
"Create a tutorial guide about 1. Pattern matching improvements... and save to [[python312_guide.md]]"

Output: [Tutorial content] [[python312_guide.md]]
Result: File written with tutorial
```

**Rules:**
- Can reference ANY previous agent (e.g., Agent 5 can use {{Agent-2}})
- Multiple placeholders allowed: `"Compare {{Agent-1}} with {{Agent-3}}"`
- Output truncated if > 500 characters (shows "...")
- Shows "[Agent-X output not available]" if agent hasn't executed
- Case-sensitive: Must be exact `{{Agent-X}}` format

**Complex Example:**
```
Agent 1: List topics
Agent 2: Explain {{Agent-1}}
Agent 3: Add examples to {{Agent-2}}
Agent 4: Compare {{Agent-1}} and {{Agent-3}}, then summarize
Agent 5: Save {{Agent-4}} to [[final_report.md]]
```

[See Agent Execution Flow →](#agent-execution-flow)

[Back to top](#table-of-contents)

---

## Agent Execution Flow

**Complete Order of Operations:**

**For Each Agent in Sequence:**

**1. Agent Definition Retrieved**
- Model, temperature, tools, prompt loaded

**2. Placeholder Resolution**
- `{{Agent-X}}` replaced with previous agent outputs
- Multiple placeholders resolved in order

**3. Read File Tool Processing** (if enabled)
- Finds all `<<filename>>` patterns
- Reads file contents
- Replaces pattern with file data
- Status: `[Agent-X] File read operations completed`

**4. Web Search Tool Processing** (if enabled)
- Uses prompt as search query
- Fetches web results
- Appends results to prompt
- Status: `[Agent-X] Searching the web...`
- Status: `[Agent-X] Web search completed`

**5. Message Sent to Model**
- Modified prompt sent to agent's selected model
- Uses agent's temperature and parameters

**6. Response Received**
- Streaming response collected
- Full response stored for next agents

**7. Write File Tool Processing** (if enabled)
- Scans response for `[[filename]]` patterns
- Extracts content (code blocks or nearby text)
- Writes files to disk
- Status: `[Agent-X] N file(s) written successfully`

**8. Response Displayed**
- Shows in chat: `🤖 Agent-X Response:`
- Full output visible

**9. Next Agent Starts**
- Previous agent's output now available as `{{Agent-X}}`
- Repeat steps 1-8

**Status Message Examples:**
```
[Agent-1] Starting execution...
[Agent-1] File read operations completed
[Agent-1] Response received (250 characters)

[Agent-2] Starting execution...
[Agent-2] Searching the web...
[Agent-2] Web search completed
[Agent-2] Response received (180 characters)

[Agent-3] Starting execution...
[Agent-3] Checking for file write requests...
[Agent-3] 2 file(s) written successfully
[Agent-3] Response received (520 characters)

🎉 Agent sequence completed successfully!
```

[See Read File Tool →](#read-file-tool) | [See Write File Tool →](#write-file-tool)

[Back to top](#table-of-contents)

---

## Read File Tool

**Function:** Inject file contents into agent prompts automatically

**Syntax:** `<<file_path>>`

**How It Works:**
1. Enable "Read File" checkbox for agent during staging
2. Include `<<filename>>` in agent prompt
3. Before model sees prompt, system:
   - Finds all `<<filename>>` patterns
   - Reads actual file contents
   - Replaces pattern with content
4. Model receives prompt with file data embedded

**Example:**

**Agent Prompt:**
```
Analyze the quarterly report in <<Q4_2024_report.pdf>> and identify key trends
```

**What Model Receives:**
```
Analyze the quarterly report in 

[Content from Q4_2024_report.pdf]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Q4 2024 Financial Report
Revenue: $2.5M (+15% YoY)
Expenses: $1.8M
Net Income: $700K
Key Metrics:
- Customer Growth: 25%
- Retention Rate: 92%
...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

and identify key trends
```

**Supported File Formats:**

**Text Files:**
- .txt, .md, .json, .csv, .xml, .html, .py, .js, .java, etc.

**Documents (via MarkItDown):**
- .pdf, .docx, .xlsx, .pptx, .epub

**Images (vision models only):**
- .jpg, .png, .gif, .bmp

**Audio (with transcription):**
- .mp3, .wav, .flac, .m4a, .ogg

**Path Formats:**

**Absolute paths:**
```
<<C:\Users\Documents\data.txt>>
<<"C:\Users\Documents\data.txt">>  (with quotes)
```

**Relative paths:**
```
<<data.txt>>  (current directory)
<<.\reports\data.txt>>
```

**Multiple Files:**
```
Compare <<file1.txt>> with <<file2.txt>> and summarize differences
```

**Status Messages:**
- ✅ `[Agent-1] File read operations completed`
- ✅ `[Agent-1] Read file: data.txt (1,523 characters)`
- ❌ `[Agent-1] File read error: File not found: data.txt`
- ❌ `[Agent-1] File read error: Permission denied`

**Important Notes:**
- File must exist and be readable
- Large files may hit context limits
- Binary files (images) require vision models
- Files read at execution time (not staging)

[See Write File Tool →](#write-file-tool)

[Back to top](#table-of-contents)

---

## Write File Tool

**Function:** Automatically save agent responses to files

**Syntax:** `[[file_path]]` in agent response

**How It Works:**
1. Enable "Write File" checkbox for agent during staging
2. Agent generates response containing `[[filename]]`
3. After model responds, system:
   - Detects `[[filename]]` patterns
   - Extracts content from response
   - Writes content to specified file
4. File created/overwritten on disk

**Content Extraction Methods:**

System tries these in order:

**1. Code Blocks (Preferred)**
````
Agent Response:
"Here's the Python script:

```python
def hello():
    print("Hello, World!")
    
hello()
```

[[hello.py]]"

→ File contains only the code inside ```
````

**2. Content After File Path**
```
Agent Response:
"I'll create the report:

[[report.md]]

# Sales Report
Q1 2024: $50,000
Q2 2024: $75,000"

→ File contains "# Sales Report..." onwards
```

**3. Content Before File Path**
```
Agent Response:
"Here's the summary:

Key Points:
- Revenue up 20%
- New customers: 150
- Retention: 95%

[[summary.txt]]"

→ File contains "Key Points:..." section
```

**Examples:**

**Example 1: Code Generation**
````
Agent Prompt (Write File enabled):
"Create a Python hello world script and save to [[hello.py]]"

Agent Response:
"Here's a simple hello world script:

```python
print("Hello, World!")
```

[[hello.py]]"

Result: ✅ hello.py created with: print("Hello, World!")
````

**Example 2: Report Generation**
```
Agent Prompt (Write File enabled):
"Analyze {{Agent-1}} and create a report. Save to [[analysis.md]]"

Agent Response:
"Based on the data, here's the report:

[[analysis.md]]

# Analysis Report

## Key Findings
1. Trend A shows 15% increase
2. Trend B indicates stability

## Recommendations
- Focus on Trend A
- Monitor Trend B"

Result: ✅ analysis.md created with full report
```

**Example 3: Multiple Files**
```
Agent Response:
"I've created two files:

[[config.json]]
```json
{"setting": "value"}
```

[[readme.md]]
```markdown
# Project
This is the readme.
```"

Result: ✅ Both files created
```

**Path Formats:**
```
[[output.txt]]                    (current directory)
[[C:\reports\output.txt]]         (absolute path)
[["C:\My Documents\file.txt"]]    (with quotes for spaces)
[[.\data\output.csv]]             (relative path)
```

**Status Messages:**
- ✅ `[Agent-2] 1 file(s) written successfully`
- ✅ `[Agent-2] Successfully wrote 150 characters to 'output.txt'`
- ⚠️ `[Agent-2] Skipping 'output.txt': No content extracted`
- ⚠️ `[Agent-2] File path found but no valid content extracted`
- ❌ `[Agent-2] Failed to write 'output.txt': Permission denied`

**Important Tips:**
- ✅ Use code blocks for code/data
- ✅ Clearly separate content from explanations
- ✅ Include file path in agent prompt instructions
- ❌ Avoid mixing AI commentary with file content
- ⚠️ Files are overwritten if they exist

**Troubleshooting:**

**Problem:** Files not created
**Solution:** Ensure agent response includes:
1. The `[[filename]]` pattern
2. Actual content (in code blocks or nearby)
3. Content is not just AI explanation

**Problem:** Wrong content in file
**Solution:** Use code blocks to clearly mark file content

[See File Write Problems →](#file-write-problems)

[Back to top](#table-of-contents)

---

## Web Search Tool

**Function:** Provide agents with current web information

**How It Works:**
1. Enable "Web Search" checkbox for agent during staging
2. Agent prompt is used as search query
3. Web search performed automatically
4. Results appended to prompt before sending to model
5. Model receives: `"[original prompt]\n\nWeb search results:\n[results]"`

**Example:**

**Agent Prompt:**
```
What are the latest features announced in Python 3.13?
```

**What Model Receives:**
```
What are the latest features announced in Python 3.13?

Web search results:

[1] Python 3.13 Release Notes - python.org
Released: October 2024
- Improved performance with JIT compiler
- New syntax for type parameters
- Enhanced error messages

[2] What's New in Python 3.13 - Real Python
- Free-threaded mode (no GIL)
- Better debugging tools
- Improved asyncio performance

[3] Python 3.13 Features - Dev.to
Key highlights include...
```

**Status Messages:**
- 🔍 `[Agent-3] Searching the web...`
- ✅ `[Agent-3] Web search completed`
- ⚠️ `[Agent-3] No web results found`
- ❌ `[Agent-3] Web search error: Connection timeout`

**Use Cases:**
- **Current Events:** "What happened today in tech news?"
- **Latest Documentation:** "Latest React 19 features"
- **Real-time Data:** "Current stock price of Tesla"
- **Fact-checking:** "Verify the release date of Python 3.12"
- **Research:** "Recent papers on quantum computing"

**Benefits:**
- ✅ Up-to-date information beyond model's training data
- ✅ Automatic integration into prompt
- ✅ No manual copy-paste needed
- ✅ Combines web knowledge with model intelligence

**Limitations:**
- Requires internet connection
- Results depend on search engine availability
- May increase response time
- Not all queries return useful results

**Combining with Other Tools:**
```
Agent 1 [Web Search]:
"Search for Python 3.13 release notes"

Agent 2 [Write File]:
"Summarize {{Agent-1}} and save to [[python_3_13_summary.md]]"
```

[Back to top](#table-of-contents)

---

## CSV Analysis Tool

**Function:** Process CSV files row-by-row with AI analysis

**Syntax:**
- `{CX}` = Read from column X (input)
- `{{CX}}` = Write to column X (output)
- `{RX}` or `{RX-Y}` = Specify rows to process

**Row Specification:**
```
{R1}        Only row 1
{R1-5}      Rows 1 through 5
{R1,3,5}    Rows 1, 3, and 5 only
{R5-}       Row 5 to end of file
{R-5}       Start to row 5
No {R...}   All rows (default)
```

**Complete Workflow:**

**1. Enable CSV Tool**
- ☑️ Check "CSV Tool" checkbox in sidebar

**2. Select CSV File**
- Click to open file dialog
- Choose your CSV file

**3. Write Prompt with Column References**
```
Grade this essay: {C2}
Score (0-100): {{C3}}
Feedback: {{C4}}
```

**4. Preview Results**
- Shows first 3 rows as examples
- Review to verify prompt is correct
- Shows how model will respond

**5. Confirm Processing**
- Type "ok" in chat to begin
- Or type anything else to cancel

**6. Processing Begins**
- Each row processed individually
- 1 row = 1 API call
- File auto-saves after each row
- Progress shown in real-time
- Stop button available anytime

**Example Usage:**

**CSV File: students.csv**
```
Name,Essay,Score,Feedback
John,"Python is great...",
Mary,"I like coding...",
Alice,"Functions are...",
```

**Prompt:**
```
{R1-3} Grade this essay: {C2}
Score (0-100): {{C3}}
Feedback: {{C4}}
```

**What Happens:**

**Row 1 (John):**
- Model receives: "Grade this essay: Python is great..."
- Model responds: "COLUMN_3: 85\nCOLUMN_4: Good introduction..."
- System writes: Score=85, Feedback="Good introduction..."

**Row 2 (Mary):**
- Model receives: "Grade this essay: I like coding..."
- Model responds: "COLUMN_3: 78\nCOLUMN_4: Needs more detail..."
- System writes: Score=78, Feedback="Needs more detail..."

**Row 3 (Alice):**
- Model receives: "Grade this essay: Functions are..."
- Model responds: "COLUMN_3: 92\nCOLUMN_4: Excellent explanation..."
- System writes: Score=92, Feedback="Excellent explanation..."

**Result CSV:**
```
Name,Essay,Score,Feedback
John,"Python is great...",85,"Good introduction..."
Mary,"I like coding...",78,"Needs more detail..."
Alice,"Functions are...",92,"Excellent explanation..."
```

**Model Response Format:**

Model MUST respond with this format:
```
COLUMN_3: value for column 3
COLUMN_4: value for column 4
COLUMN_5: value for column 5
```

**Rules:**
- Use `COLUMN_` prefix (case-insensitive)
- Column number matches your `{{CX}}` references
- One output per line
- Colon separator

**Important Notes:**

**Column Numbering:**
- Columns start at 1 (not 0)
- Column 1 = first column in CSV

**Input vs Output:**
- `{C2}` = Input (read) from column 2
- `{{C2}}` = Output (write) to column 2
- Can read and write same column: `Improve {C2} → {{C2}}`

**Empty Cells:**
- Empty input cells show as "[empty]" in prompt
- Can write to empty cells with `{{CX}}`

**Special Features:**
- **Auto-backup:** Creates `filename_backup_timestamp.csv`
- **Stop anytime:** Click Stop button to halt processing
- **Progress tracking:** Shows "Row X of Y"
- **Error handling:** Continues if one row fails

**Tips:**
- ✅ Test with `{R1-3}` (first 3 rows) before full run
- ✅ Use preview to verify before typing "ok"
- ✅ Keep prompts clear and specific
- ⚠️ Processing is SLOW (1 API call per row)
- ⚠️ No undo - rely on backup file
- ⚠️ No chat history during CSV processing

**Common Patterns:**

**Grading:**
```
{R1-10} Grade: {C2}
Score: {{C3}}
Feedback: {{C4}}
```

**Summarization:**
```
Summarize this text: {C1}
Summary: {{C2}}
```

**Translation:**
```
Translate to Spanish: {C2}
Translation: {{C3}}
```

**Sentiment Analysis:**
```
Analyze sentiment: {C1}
Sentiment (positive/negative/neutral): {{C2}}
Score (0-10): {{C3}}
```

**Data Extraction:**
```
Extract key points from: {C1}
Key points: {{C2}}
Categories: {{C3}}
```

[See CSV Tool Troubleshooting →](#common-issues)

[Back to top](#table-of-contents)

---

## Document Upload Processing

**Function:** Process various document types with AI

**Supported Formats:**

**Documents:**
- PDF (.pdf)
- Microsoft Word (.docx)
- Excel (.xlsx)
- PowerPoint (.pptx)
- EPUB (.epub)

**Text Files:**
- Plain text (.txt)
- Markdown (.md)
- JSON (.json)
- CSV (.csv)
- XML (.xml)
- HTML (.html)
- Source code (.py, .js, .java, etc.)

**Images:**
- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- BMP (.bmp)
- Requires vision-capable model

**Audio:**
- MP3 (.mp3)
- WAV (.wav)
- FLAC (.flac)
- M4A (.m4a)
- OGG (.ogg)
- Automatic transcription

**Archives:**
- ZIP (.zip)
- Auto-extracts and processes contents

**How to Use:**

**Single File:**
1. Click "Upload Document" button
2. Select file from file dialog
3. (Optional) Add processing prompt
4. File content processed with MarkItDown
5. Content appears in chat
6. Model can analyze/respond

**Multiple Files:**
1. Select multiple files in dialog (Ctrl+Click)
2. Enter processing prompt (applied to all)
3. Each file processed individually
4. Results shown sequentially

**Processing Flow:**
```
File Selected
    ↓
MarkItDown Conversion
    ↓
Markdown Content Generated
    ↓
Content Displayed in Chat
    ↓
Model Receives Content
    ↓
AI Analysis/Response
```

**Example:**

**Upload: report.pdf**

**Chat displays:**
```
📄 Document: report.pdf
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Q4 2024 Financial Report

## Revenue
- Q4: $2.5M (+15% YoY)
- Annual: $8.2M

## Expenses
- Operating: $1.8M
- Marketing: $500K
...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Then ask:**
```
User: "What are the key takeaways from this report?"

Model: "Based on the Q4 2024 Financial Report:
1. Revenue grew 15% year-over-year
2. Annual revenue reached $8.2M
3. Operating expenses were $1.8M
..."
```

**With Processing Prompt:**
```
Prompt: "Summarize this document in 3 bullet points"

Result: Model immediately provides summary for each file
```

[See Batch File Processing →](#batch-file-processing)

[Back to top](#table-of-contents)

---

## Drag Drop File Processing

**Function:** Quick file processing via drag-and-drop

**How to Use:**
1. Open file explorer
2. Select file(s)
3. Drag into chat window
4. Drop anywhere in chat area
5. Files processed automatically
6. Content appears in conversation

**Supported:**
- Same formats as Document Upload
- Single or multiple files
- Folders (processes all files inside)

**Advantages:**
- ✅ Faster than clicking Upload button
- ✅ Intuitive interface
- ✅ Can drop multiple files at once
- ✅ Visual feedback during drop

**Example:**

**Drag sales_report.pdf into chat:**
```
[File being processed...]

📄 sales_report.pdf

[Document content displayed]

Ready for your questions!
```

**Then:**
```
User: "What was the total revenue?"

Model: "According to the report, total revenue was..."
```

[Back to top](#table-of-contents)

---

## Batch File Processing

**Function:** Process multiple files with the same prompt

**How to Use:**

**Method 1: Upload Dialog**
1. Click "Upload Document"
2. Select multiple files (Ctrl+Click)
3. Enter processing prompt
4. Each file processed with same prompt

**Method 2: Drag & Drop**
1. Select multiple files in explorer
2. Drag all into chat window
3. Enter processing prompt when prompted

**Example:**

**Files:** report1.pdf, report2.pdf, report3.pdf

**Prompt:** "Summarize this document in 3 bullet points"

**Result:**
```
📄 report1.pdf
Summary:
• Point 1
• Point 2  
• Point 3

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 report2.pdf
Summary:
• Point 1
• Point 2
• Point 3

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 report3.pdf
Summary:
• Point 1
• Point 2
• Point 3
```

**Use Cases:**
- Summarizing multiple reports
- Extracting data from multiple documents
- Comparing multiple files
- Bulk document analysis
- Code review across multiple files

**Performance:**
- Files processed sequentially (one at a time)
- May take time for many files
- Stop button available during processing

[Back to top](#table-of-contents)

---

## Memory Control Program MCP

**Function:** Persistent knowledge base with automatic memory retrieval

**What It Does:**
- Automatically stores important information from conversations
- Retrieves relevant memories for future queries
- Maintains context across sessions
- Enhances responses with historical knowledge

**How It Works:**

**Memory Storage:**
- Important conversation snippets saved as "memories"
- Stored in `memories/` folder
- Indexed for semantic search
- Persists across app restarts

**Memory Retrieval:**
- When you ask a question, relevant memories retrieved
- Memories added to prompt context
- Model sees: `"[question]\n\nRelevant memories:\n[memory 1]\n[memory 2]..."`
- Response informed by past conversations

**How to Enable:**
1. ☑️ Check "MCP" checkbox in sidebar
2. Memories automatically managed
3. No additional configuration needed

**Example:**

**Session 1 (January):**
```
User: "I'm working on a Python project using FastAPI"
Model: "Great! FastAPI is excellent for APIs..."

→ Memory stored: "User working on Python project with FastAPI"
```

**Session 2 (February):**
```
User: "How do I add authentication?"
MCP retrieves: "User working on Python project with FastAPI"

Model receives:
"How do I add authentication?

Relevant memories:
- User is working on Python project with FastAPI

"

Model: "For FastAPI authentication, I recommend using OAuth2..."
```

**Benefits:**
- ✅ Continuity across sessions
- ✅ Personalized responses
- ✅ No manual memory management
- ✅ Relevant context automatically included

**Configuration:**
- Memory count: Adjustable (default: 5 memories per query)
- Memory relevance: Semantic similarity based
- Memory storage: Local filesystem

**Use Cases:**
- Long-term projects
- Recurring topics
- Personal preferences
- Historical reference
- Ongoing research

[See RAG System →](#rag-system)

[Back to top](#table-of-contents)

---

## RAG System

**Function:** Retrieve context from document collections

**What is RAG?**
Retrieval-Augmented Generation:
- Upload document corpus (collection of files)
- Documents split into chunks and embedded
- Queries retrieve most relevant chunks
- Retrieved chunks included in model context
- Model answers using document knowledge

**How It Works:**

**1. Document Indexing:**
- Upload documents to RAG system
- Documents split into chunks (configurable size)
- Each chunk converted to embedding vector
- Vectors stored in database (ChromaDB)

**2. Query Processing:**
- Your question converted to embedding
- Semantic similarity search in vector database
- Top N most relevant chunks retrieved
- Chunks ranked by relevance

**3. Response Generation:**
- Retrieved chunks added to prompt
- Model receives: `"[question]\n\nContext from documents:\n[chunks]"`
- Model generates answer using document knowledge

**Configuration Options:**

**Embedding Model:**
- Local models (via Ollama)
- Remote models (OpenAI, etc.)
- Affects retrieval quality

**Chunk Size:**
- Smaller (256-512): More precise, less context
- Larger (1024-2048): More context, less precise
- Default: 512 tokens

**Retrieval Count:**
- How many chunks to retrieve
- More chunks = more context, longer prompts
- Default: 3-5 chunks

**Similarity Threshold:**
- Minimum similarity score for retrieval
- Higher = more relevant but fewer results
- Lower = more results but less relevant

**How to Use:**

**1. Access RAG Panel:**
- Tools → RAG System

**2. Upload Documents:**
- Click "Add Documents"
- Select files or folder
- Supported: PDF, DOCX, TXT, MD, etc.

**3. Configure Settings:**
- Choose embedding model
- Set chunk size
- Set retrieval parameters

**4. Enable RAG:**
- ☑️ Enable RAG checkbox
- Ask questions in chat
- Relevant context automatically retrieved

**Example:**

**Documents Uploaded:**
- python_guide.pdf
- fastapi_tutorial.md
- best_practices.txt

**Query:**
```
User: "How do I handle errors in FastAPI?"
```

**RAG Retrieval:**
```
Chunk 1 (fastapi_tutorial.md, score: 0.89):
"FastAPI provides exception handlers...
Use @app.exception_handler decorator..."

Chunk 2 (best_practices.txt, score: 0.76):
"Error handling best practices:
1. Use HTTPException for API errors
2. Create custom exception handlers..."

Chunk 3 (python_guide.pdf, score: 0.65):
"Python exceptions can be caught with try/except..."
```

**Model Receives:**
```
How do I handle errors in FastAPI?

Context from documents:

[Chunk 1]
FastAPI provides exception handlers...
Use @app.exception_handler decorator...

[Chunk 2]
Error handling best practices:
1. Use HTTPException for API errors
2. Create custom exception handlers...

[Chunk 3]
Python exceptions can be caught with try/except...
```

**Model Response:**
```
Based on the documentation, here's how to handle errors in FastAPI:

1. Use HTTPException for standard API errors:
   [Example code]

2. Create custom exception handlers with @app.exception_handler:
   [Example code]

3. Follow best practices...
```

**Use Cases:**
- Technical documentation Q&A
- Research paper analysis
- Company knowledge base
- Legal document review
- Medical literature search
- Code repository analysis

**Benefits:**
- ✅ Accurate answers from your documents
- ✅ Source attribution (knows which doc)
- ✅ Handles large document collections
- ✅ Updates when you add new docs
- ✅ Works with any document format

**vs MCP:**
- **MCP:** Remembers conversation history
- **RAG:** Retrieves from uploaded documents
- **Both:** Can be used simultaneously

[Back to top](#table-of-contents)

---

## Prompt Manager

**Function:** Save and reuse common prompts

**Features:**
- Save frequently used prompts
- Organize prompts by category
- Quick insertion into chat
- Share prompts between sessions

**How to Use:**

**Save Prompt:**
1. Tools → Prompt Manager
2. Click "Save New Prompt"
3. Enter prompt text
4. Give it a descriptive name
5. (Optional) Add category/tags
6. Click Save

**Load Prompt:**
1. Tools → Prompt Manager
2. Browse saved prompts
3. Select prompt
4. Click "Insert" or double-click
5. Prompt appears in chat input

**Manage Prompts:**
- Edit existing prompts
- Delete unused prompts
- Organize by category
- Search prompts by keyword

**Example Prompts to Save:**

**Code Review:**
```
Review this code for:
1. Bugs and potential errors
2. Performance issues
3. Best practice violations
4. Security concerns
Provide specific recommendations.
```

**Technical Writing:**
```
Explain this concept:
- Use simple language
- Include examples
- Add analogies
- Format as tutorial
Target audience: Beginners
```

**Data Analysis:**
```
Analyze this data and provide:
1. Summary statistics
2. Key trends and patterns
3. Anomalies or outliers
4. Actionable insights
5. Visualizations (describe)
```

**Use Cases:**
- Complex multi-step instructions
- Role-playing scenarios
- Consistent formatting requirements
- Specialized analysis templates
- Standardized question formats

**Storage:**
- Prompts saved in `prompts/` folder
- JSON format for easy editing
- Portable between installations

[Back to top](#table-of-contents)

---

## Image Processing

**Function:** Analyze images with vision-capable models

**Supported Models:**
- **Google Gemini:** gemini-pro-vision, gemini-1.5-pro
- **Anthropic Claude:** claude-3-opus, claude-3-sonnet, claude-3-5-sonnet
- **Ollama Vision:** llava, bakllava, llava-phi3

**Supported Image Formats:**
- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- BMP (.bmp)
- WebP (.webp)

**How to Use:**

**1. Select Vision Model:**
- Choose vision-capable model from dropdown
- Examples: gemini-pro-vision, llava, claude-3-opus

**2. Upload Image:**
- Click "Upload Document"
- Select image file
- Or drag & drop image into chat

**3. Image Displayed:**
- Image preview shown in chat
- Ready for questions

**4. Ask Questions:**
- "What's in this image?"
- "Describe what you see"
- "Extract text from this image"
- "What objects are present?"

**Capabilities:**

**Object Detection:**
```
User: "What objects are in this image?"
Model: "I can see:
- A laptop on a desk
- Coffee mug
- Notebook and pen
- Desk lamp
- Window in background"
```

**Text Extraction (OCR):**
```
User: "Extract all text from this screenshot"
Model: "The text reads:
Title: Product Launch
Date: March 15, 2024
Location: Conference Room A
..."
```

**Scene Description:**
```
User: "Describe this scene in detail"
Model: "This is a modern office setting with natural lighting...
The workspace is organized with...
The atmosphere appears..."
```

**Image Comparison:**
```
User: [Upload image1.jpg]
User: [Upload image2.jpg]
User: "Compare these two images"

Model: "Comparing the images:

Similarities:
- Both show outdoor scenes
- Similar lighting conditions

Differences:
- Image 1 has more vegetation
- Image 2 shows urban setting
..."
```

**Code in Images:**
```
User: "Extract and explain this code snippet"
[Image of code]

Model: "The code shows a Python function:

```python
def calculate_total(items):
    return sum(item.price for item in items)
```

This function..."
```

**Diagram Analysis:**
```
User: "Explain this architecture diagram"
[Image of system diagram]

Model: "This diagram shows a microservices architecture:
- Frontend connects to API Gateway
- API Gateway routes to 3 services
- Services connect to database layer
..."
```

**Use Cases:**
- Screenshot analysis
- Document digitization
- Photo cataloging
- Diagram explanation
- Code extraction
- Product identification
- Medical image analysis (with appropriate model)
- Chart/graph interpretation

**Tips:**
- ✅ Use high-quality images for better results
- ✅ Ensure text is legible
- ✅ Good lighting improves accuracy
- ⚠️ Very large images may be resized
- ⚠️ Vision models typically cost more than text-only

[Back to top](#table-of-contents)

---

## Audio Transcription

**Function:** Convert audio to text automatically

**Supported Formats:**
- MP3 (.mp3)
- WAV (.wav)
- FLAC (.flac)
- M4A (.m4a)
- OGG (.ogg)

**How It Works:**
1. Upload audio file
2. Automatic transcription service processes audio
3. Text transcript appears in chat
4. Model can analyze transcript content

**Features:**
- Automatic language detection
- Speaker diarization (if available)
- Timestamp generation
- High accuracy transcription

**How to Use:**

**1. Upload Audio:**
- Click "Upload Document"
- Select audio file
- Or drag & drop audio file

**2. Processing:**
```
[Processing audio: meeting_recording.mp3...]
[Transcription in progress...]
```

**3. Transcript Displayed:**
```
🎵 Audio Transcript: meeting_recording.mp3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[00:00] Welcome everyone to today's meeting.
[00:15] Let's start with the project updates.
[00:32] John: Our Q4 goals are on track...
[01:20] Sarah: The new feature launched successfully...
[02:45] Next steps include...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Duration: 05:30
```

**4. Ask Questions:**
```
User: "Summarize the key decisions from this meeting"

Model: "Based on the transcript:
1. Q4 goals are on track
2. New feature launched successfully
3. Next steps include..."
```

**Use Cases:**
- Meeting transcription and summarization
- Interview analysis
- Lecture note-taking
- Podcast content extraction
- Voice memo processing
- Call recording analysis

**Advanced Analysis:**
```
User: "Extract action items and assign them to people"

Model: "Action items from meeting:
- John: Complete Q4 report by Friday
- Sarah: Schedule follow-up demo
- Team: Review feature feedback
..."
```

**Tips:**
- ✅ Clear audio produces better transcripts
- ✅ Minimize background noise
- ✅ Single speaker easier than multiple
- ⚠️ Very long audio may take time
- ⚠️ Heavy accents may affect accuracy

[Back to top](#table-of-contents)

---

## URL Content Extraction

**Function:** Extract and process web content directly from URLs

**Supported:**
- **Web pages:** HTML content extraction
- **YouTube videos:** Automatic transcript extraction
- **Online articles:** Clean text extraction
- **Documentation pages:** Formatted content
- **Blog posts:** Main content isolation

**How to Use:**

**Method 1: Paste URL in Chat**
```
User: "https://example.com/article"

[Extracting content from URL...]

📄 Content from: example.com/article
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Article Title]

[Extracted content in markdown format]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Method 2: URL with Question**
```
User: "Summarize https://example.com/article"

[Content extracted]

Model: "This article discusses...
Key points:
1. ...
2. ...
"
```

**YouTube Video Example:**
```
User: "https://youtube.com/watch?v=xxxxx"

[Extracting transcript...]

📺 YouTube Video: "Python Tutorial"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Transcript]
[00:00] Welcome to this Python tutorial
[00:15] Today we'll cover functions
[00:45] A function is defined using def keyword
...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User: "Summarize this video"

Model: "This tutorial covers Python functions:
- Function definition with def
- Parameters and arguments
- Return values
..."
```

**Use Cases:**
- Research article analysis
- YouTube video summarization
- Documentation quick reference
- News article processing
- Blog post extraction
- Tutorial content analysis

**Features:**
- ✅ Automatic content cleaning (removes ads, navigation)
- ✅ Markdown formatting
- ✅ Preserves structure (headings, lists)
- ✅ Code blocks extracted properly
- ⚠️ Requires internet connection
- ⚠️ Some sites may block scraping

[Back to top](#table-of-contents)

---

## ZIP File Processing

**Function:** Process multiple files from ZIP archives

**How It Works:**
1. Upload .zip file
2. Archive automatically extracted
3. Each file processed individually
4. Combined results displayed

**Supported ZIP Contents:**
- All document types (PDF, DOCX, etc.)
- Text files
- Images
- Code files
- Mixed file types

**How to Use:**

**1. Upload ZIP:**
- Click "Upload Document"
- Select .zip file
- Or drag & drop ZIP into chat

**2. Extraction:**
```
📦 Processing archive: project_files.zip
[Extracting files...]

Found 5 files:
- report.pdf
- data.csv
- image.png
- code.py
- notes.txt

[Processing each file...]
```

**3. Results:**
```
📄 report.pdf
[Content from report.pdf]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 data.csv
[Content from data.csv]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 image.png
[Image analysis if vision model selected]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[etc.]
```

**4. Ask Questions:**
```
User: "Summarize all files in the archive"

Model: "The archive contains:
1. Financial report (report.pdf) showing...
2. Sales data (data.csv) with...
3. Product image (image.png) depicting...
4. Python script (code.py) that...
5. Notes (notes.txt) outlining...
"
```

**Use Cases:**
- Project file analysis
- Batch document review
- Code repository analysis
- Multi-file reports
- Compressed data processing
- Backup file examination

**Advanced Example:**

**ZIP: website_backup.zip containing:**
- index.html
- style.css
- script.js
- images/logo.png

**Query:**
```
User: "Analyze this website structure and suggest improvements"

Model: "Website Analysis:

Structure:
- index.html: Main page with basic structure
- style.css: Styling includes...
- script.js: JavaScript adds interactivity...
- logo.png: Branding image

Suggestions:
1. Add responsive design to CSS
2. Optimize JavaScript for performance
3. Consider adding more pages
..."
```

[Back to top](#table-of-contents)

---

## Common Issues

### Agent Mode Not Working

**Problem:** Agents not executing or sequence doesn't run

**Solutions:**
1. **Ensure Agent Tool is OFF before running**
   - Agent Tool checkbox must be unchecked to lock sequence
   - Sequence only runs when locked

2. **Verify agents are staged**
   - Click "Configure Agents" to see staged agents
   - At least one agent must be present

3. **Check model selection**
   - Each agent needs a valid model
   - Verify model is available (for Ollama: check locally installed)

4. **Review error messages**
   - Check chat for error details
   - Status messages show which agent failed

### Model Not Responding

**Problem:** No response after sending message or long delays

**Solutions:**
1. **Check model is selected**
   - Ensure model is chosen from dropdown
   - Model name should be visible in sidebar

2. **Verify API keys (cloud models)**
   - Google Gemini: Check API key in gemini_api_config.py
   - Deepseek: Check API key in deepseek_api_config.py
   - Anthropic: Check API key in anthropic_api_config.py

3. **Ensure Ollama is running (local models)**
   - Start Ollama service
   - Verify with: `ollama list` in terminal
   - Check Ollama is accessible at localhost:11434

4. **Check internet connection (cloud models)**
   - Cloud models require active internet
   - Test with: `ping google.com`

5. **Try different model**
   - Some models may be unavailable
   - Switch to alternative model

6. **Check context size**
   - Very long conversations may exceed limits
   - Try clearing context or reducing size

### Temperature Changes Not Applied

**Problem:** Model behavior doesn't change when adjusting temperature

**Solutions:**
1. **Settings apply to NEXT message**
   - Changes take effect on subsequent messages
   - Not retroactive

2. **Some models ignore temperature**
   - Certain models have fixed temperature
   - Try different model if temperature control needed

3. **Try larger slider changes**
   - Subtle changes (0.7 → 0.8) may not be noticeable
   - Try extreme values: 0.1 vs 1.5

4. **Verify in agent configuration**
   - For agents: Check captured temperature in Configure Agents
   - Temperature locked when agent staged

### Files Not Uploading

**Problem:** Document upload fails or doesn't process

**Solutions:**
1. **Check file format**
   - Verify format is supported
   - See supported formats in [Document Upload](#document-upload-processing)

2. **Check file size**
   - Very large files (>10MB) may fail
   - Try compressing or splitting file

3. **Verify MarkItDown installed**
   - Required for document processing
   - Install: `pip install markitdown`

4. **Check file permissions**
   - Ensure file is readable
   - Not locked by another program

5. **Try different file**
   - Test with simple .txt file
   - Isolate if issue is file-specific

### CSV Tool Not Working

**Problem:** CSV processing fails or produces incorrect results

**Solutions:**
1. **Check CSV format**
   - Must be valid CSV with comma delimiters
   - No malformed rows
   - Headers in first row (recommended)

2. **Verify column numbers**
   - Columns start at 1 (not 0)
   - Count from left: A=1, B=2, C=3, etc.

3. **Check syntax**
   - Input: `{C1}` (single braces)
   - Output: `{{C2}}` (double braces)
   - Case-insensitive: `{C1}` or `{c1}` both work

4. **Test with preview**
   - Always review preview before confirming
   - Shows how first 3 rows will be processed

5. **Verify model response format**
   - Model must respond with: `COLUMN_X: value`
   - Check model is following format

6. **Check file not open elsewhere**
   - Close file in Excel/other programs
   - CSV must be writable

[Back to top](#table-of-contents)

---

## File Write Problems

### Files Not Being Written in Agent Mode

**Problem:** Agent has Write File tool enabled but no files created

**Causes & Solutions:**

**1. No file path pattern in response**

**Cause:** Model didn't include `[[filename]]` in response

**Solution:** Explicitly instruct model:
```
Bad Prompt:
"Create a report about sales data"

Good Prompt:
"Create a sales report and save it to [[sales_report.md]]"

Better Prompt:
"Analyze sales data and save your report to [[sales_report.md]]. 
Use markdown format with headers and bullet points."
```

**2. Content not extracted**

**Cause:** Content not clearly delimited or in proper format

**Solution:** Use code blocks:
```
Instruct model:
"Create a Python script and save to [[script.py]]. 
Put the code in a code block like this:

```python
[your code here]
```

[[script.py]]"
```

**3. AI explanation mixed with content**

**Problem Response:**
```
Model: "I'll create that file for you! Here's what I'll include:
[[output.txt]]
I hope this helps! Let me know if you need changes."

→ No actual content, just explanation
```

**Good Response:**
```
Model: "Here's the content:

```
Line 1 of actual data
Line 2 of actual data
Line 3 of actual data
```

[[output.txt]]"

→ Clear content in code block
```

**4. Invalid file path**

**Causes:**
- Path contains invalid characters: `< > | * ?`
- Directory doesn't exist
- No write permissions

**Solutions:**
- Use valid Windows paths: `C:\folder\file.txt`
- Or relative paths: `output\file.txt`
- Create directory first if needed
- Check folder permissions

**5. Content too short or empty**

**Problem:** Model generates minimal content

**Status Message:**
```
⚠️ Skipping 'output.txt': Content too short (2 chars)
```

**Solution:** Instruct model to generate substantial content:
```
"Create a detailed report (at least 200 words) about {{Agent-1}} 
and save to [[report.md]]"
```

### Empty Files Created

**Problem:** Files created but contain no content or wrong content

**Solutions:**

**1. Use code blocks for structured content**
````
Prompt: "Create a JSON config file:

```json
{
  "setting1": "value1",
  "setting2": "value2"
}
```

Save to [[config.json]]"
````

**2. Separate content from instructions**
```
Bad:
"I'll create the file with the following data: 
Line 1, Line 2, Line 3 [[output.txt]]"

Good:
"Content for the file:

Line 1 of data
Line 2 of data  
Line 3 of data

[[output.txt]]"
```

**3. Check extraction in status messages**
```
Look for:
✅ "Successfully wrote 150 characters to 'output.txt'"

Not:
⚠️ "Skipping 'output.txt': No content extracted"
```

### Testing File Write

**Test with Simple Example:**

**Agent Configuration:**
- Model: Any model
- Tools: Write File ☑️
- Prompt: 
```
Create a hello world Python script. Put the code in a code block:

```python
print("Hello, World!")
```

[[hello.py]]
```

**Expected Result:**
```
[Agent-1] Checking for file write requests...
[Agent-1] 1 file(s) written successfully
✅ Successfully wrote 22 characters to 'hello.py'
```

**Verify:**
- File `hello.py` exists
- Contains: `print("Hello, World!")`
- No extra text or explanations

### Advanced Troubleshooting

**Enable debug output:**
1. Check console/terminal for debug messages
2. Look for content extraction details
3. Verify file paths are detected

**Status Message Guide:**
```
✅ "1 file(s) written successfully"
   → File created successfully

⚠️ "File path found but no valid content extracted"
   → [[file]] detected but content extraction failed
   → Check content is in code blocks or clearly marked

⚠️ "Skipping 'file.txt': No content extracted"
   → No content found before or after [[file]]
   → Add content in response

⚠️ "Skipping 'file.txt': Content too short (3 chars)"
   → Content detected but insufficient
   → Generate more substantial content

⚠️ "Skipping 'file.txt': Content appears to be explanation"
   → Detected AI commentary instead of file data
   → Separate explanations from actual content

❌ "Failed to write 'file.txt': Permission denied"
   → Folder/file permissions issue
   → Check write access to directory

❌ "Failed to write 'file.txt': Path too long"
   → File path exceeds 260 characters (Windows)
   → Use shorter path
```

**Best Practices:**
- ✅ Always use code blocks for code/data
- ✅ Include file path in prompt instructions
- ✅ Test with simple files first
- ✅ Check status messages after execution
- ✅ Separate AI explanations from file content
- ✅ Use clear content delimiters
- ❌ Don't rely on model to guess content boundaries
- ❌ Don't mix instructions with file content

[Back to top](#table-of-contents)

---

**End of Help Documentation**

For additional support or questions, please refer to the README.md file or contact support.

Version 2.0 | © 2025
