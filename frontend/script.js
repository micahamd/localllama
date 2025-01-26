// DOM Elements
const chatDisplay = document.querySelector('.chat-display');
const inputField = document.querySelector('.input-field');
const sendButton = document.querySelector('.send-button');
const clearChatButton = document.getElementById('clear-chat');
const batchProcessButton = document.getElementById('batch-process');
const ragButton = document.getElementById('rag-button');
const stopButton = document.getElementById('stop-button');
const fileDropZone = document.getElementById('file-drop-zone');
const fileInput = document.getElementById('file-input');
const imagePreview = document.getElementById('image-preview');

// Abort controller for stopping requests
let currentController = null;

// Form Controls
const developerSelector = document.getElementById('developer-selector');
const modelSelector = document.getElementById('model-selector');
const embeddingSelector = document.getElementById('embedding-selector');
const systemText = document.getElementById('system-text');
const tempSlider = document.getElementById('temp-slider');
const contextSlider = document.getElementById('context-slider');
const chunkEntry = document.getElementById('chunk-entry');
const semanticChunkingCheckbox = document.getElementById('semantic-chunking');
const includeChatCheckbox = document.getElementById('include-chat');
const includeFileCheckbox = document.getElementById('include-file');

// Create floating display elements
const tempDisplay = document.createElement('span');
tempDisplay.classList.add('slider-display');
tempSlider.parentNode.insertBefore(tempDisplay, tempSlider.nextSibling);

const contextDisplay = document.createElement('span');
contextDisplay.classList.add('slider-display');
contextSlider.parentNode.insertBefore(contextDisplay, contextSlider.nextSibling);

// Update slider display values
const updateSliderDisplay = () => {
    tempDisplay.textContent = parseFloat(tempSlider.value).toFixed(2);
    contextDisplay.textContent = parseInt(contextSlider.value);
};

// Initial update
updateSliderDisplay();

// Event listeners for slider changes
tempSlider.addEventListener('input', updateSliderDisplay);
contextSlider.addEventListener('input', updateSliderDisplay);

// State
let currentFile = null;
let ragFiles = [];
let isProcessing = false;

// Initialize controls
const initializeControls = () => {
    // Developer options
    ['ollama', 'google'].forEach(dev => {
        const option = document.createElement('option');
        option.value = dev;
        option.textContent = dev;
        developerSelector.appendChild(option);
    });

    // Initialize temperature slider (0.0 to 1.0)
    tempSlider.type = 'range';
    tempSlider.min = 0;
    tempSlider.max = 1;
    tempSlider.step = 0.1;
    tempSlider.value = 0.4;
    tempDisplay.textContent = '0.40'; // Initial display

    // Initialize context window slider (1000 to 128000)
    contextSlider.type = 'range';
    contextSlider.min = 1000;
    contextSlider.max = 128000;
    contextSlider.step = 1000;
    contextSlider.value = 4096;
    contextDisplay.textContent = '4096'; // Initial display

    // Initialize chunk size
    chunkEntry.value = 128;

    // Set default system message and ensure it's trimmed
    const defaultSystemMsg = "You are a helpful AI assistant who only gives accurate and objective information.";
    systemText.value = defaultSystemMsg.trim();

    // Set default checkbox states
    includeFileCheckbox.checked = true;
    includeFileCheckbox.disabled = true;
};

// File handling
const handleFile = (file) => {
    currentFile = file;
    const fileType = file.type.startsWith('image/') ? 'image' : 'document';

    if (fileType === 'image') {
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = document.createElement('img');
            img.src = e.target.result;
            imagePreview.innerHTML = '';
            imagePreview.appendChild(img);
            currentFile = {
                type: 'image',
                name: file.name,
                content: e.target.result.split(',')[1] // Remove data URL prefix
            };
            appendMessage(`Image loaded: ${file.name}`, 'status');
        };
        reader.readAsDataURL(file);
    } else {
        const reader = new FileReader();
        reader.onload = (e) => {
            const content = e.target.result;
            const wordCount = content.trim().split(/\s+/).length;
            currentFile = {
                type: 'document',
                name: file.name,
                content: content,
                wordCount: wordCount
            };
            appendMessage(`File ${file.name} uploaded (${wordCount} words)`, 'status');
        };
        reader.readAsText(file);
    }

    includeFileCheckbox.disabled = false;
    includeFileCheckbox.checked = true;
};

// File drop zone events
fileDropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    fileDropZone.classList.add('drag-over');
});

fileDropZone.addEventListener('dragleave', () => {
    fileDropZone.classList.remove('drag-over');
});

fileDropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    fileDropZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
});

fileDropZone.addEventListener('click', () => {
    fileInput.click();
});

fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) handleFile(file);
});

// Initialize and fetch models
initializeControls();
fetch('http://localhost:5001/models?developer=ollama')
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        populateModels(data, 'ollama');
    })
    .catch(error => {
        console.error('Error fetching models:', error);
    });

// Event Listeners
developerSelector.addEventListener('change', () => {
    const developer = developerSelector.value;
    embeddingSelector.disabled = developer === 'google';
    fetch(`http://localhost:5001/models?developer=${developer}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            populateModels(data, developer);
        })
        .catch(error => {
            console.error('Error fetching models:', error);
        });
});

// Model population
const populateModels = (data, developer) => {
    console.log('populateModels called with data:', data, 'and developer:', developer);
    modelSelector.innerHTML = '';
    embeddingSelector.innerHTML = '';
    
    if (data && data.llm_models) {
        data.llm_models.forEach(model => {
            const option = document.createElement('option');
            option.value = model;
            option.textContent = model;
            modelSelector.appendChild(option);
        });
    } else {
        console.error('No llm_models found in data:', data);
    }
    
    if (data && data.embedding_models) {
        data.embedding_models.forEach(model => {
            const option = document.createElement('option');
            option.value = model;
            option.textContent = model;
            embeddingSelector.appendChild(option);
        });
    } else {
        console.error('No embedding_models found in data:', data);
    }
    
    if (developer === 'google') {
        embeddingSelector.disabled = true;
        embeddingSelector.value = 'models/text-embedding-004';  // Set Google's embedding model
    } else {
        embeddingSelector.disabled = false;
        if (embeddingSelector.options.length > 0) {
            embeddingSelector.value = embeddingSelector.options[0].value;  // Set first Ollama embedding model
        }
    }
}

// Message handling
const appendMessage = (message, role) => {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', role);
    
    if (role === 'assistant') {
        // Split message into paragraphs
        const paragraphs = message.split('\n\n');
        
        paragraphs.forEach(paragraph => {
            if (paragraph.trim()) {
                if (paragraph.startsWith('```')) {
                    // Code block with language detection
                    const match = paragraph.match(/```(\w+)?\n([\s\S]*?)```/);
                    if (match) {
                        const [, lang, code] = match;
                        const pre = document.createElement('pre');
                        const codeEl = document.createElement('code');
                        if (lang) {
                            codeEl.classList.add(`language-${lang}`);
                        }
                        codeEl.textContent = code.trim();
                        pre.appendChild(codeEl);
                        messageDiv.appendChild(pre);
                        // Apply syntax highlighting
                        hljs.highlightElement(codeEl);
                    }
                } else if (paragraph.startsWith('$') && paragraph.endsWith('$')) {
                    // Math equation
                    const mathDiv = document.createElement('div');
                    mathDiv.classList.add('math');
                    try {
                        katex.render(paragraph.slice(1, -1).trim(), mathDiv, {
                            throwOnError: false,
                            displayMode: true
                        });
                    } catch (e) {
                        mathDiv.textContent = paragraph.slice(1, -1).trim();
                    }
                    messageDiv.appendChild(mathDiv);
                } else {
                    // Regular paragraph with inline code, math, and special characters
                    const p = document.createElement('p');
                    let text = paragraph;
                    
                    // Handle inline code
                    text = text.replace(/`([^`]+)`/g, (_, code) => {
                        const codeEl = document.createElement('code');
                        codeEl.textContent = code;
                        return codeEl.outerHTML;
                    });
                    
                    // Handle inline math
                    text = text.replace(/\$([^$]+)\$/g, (_, math) => {
                        try {
                            const span = document.createElement('span');
                            katex.render(math, span, {
                                throwOnError: false,
                                displayMode: false
                            });
                            return span.outerHTML;
                        } catch (e) {
                            return math;
                        }
                    });
                    
                    p.innerHTML = text;
                    messageDiv.appendChild(p);
                }
            }
        });
    } else {
        const p = document.createElement('p');
        p.textContent = message;
        messageDiv.appendChild(p);
    }
    
    chatDisplay.appendChild(messageDiv);
    chatDisplay.scrollTop = chatDisplay.scrollHeight;
};

// Batch processing
batchProcessButton.addEventListener('click', async () => {
    const prompt = inputField.value.trim();
    if (!prompt) {
        appendMessage('Please enter a prompt first.', 'error');
        return;
    }

    const input = document.createElement('input');
    input.type = 'file';
    input.multiple = true;
    input.onchange = async (e) => {
        const files = Array.from(e.target.files);
        appendMessage(`Starting batch processing of ${files.length} files`, 'status');
        
        for (const file of files) {
            if (isProcessing) break;
            
            appendMessage(`Processing: ${file.name}`, 'status');
            const formData = new FormData();
            formData.append('file', file);
            formData.append('prompt', prompt);
            
            try {
                // Add system message, temperature, and context size to form data
                formData.append('system_msg', systemText.value.trim());
                formData.append('temperature', tempSlider.value);
                formData.append('context_size', contextSlider.value);
                
                const response = await fetch('http://localhost:5001/batch', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                appendMessage(`Result for ${file.name}: ${data.response}`, 'assistant');
            } catch (error) {
                appendMessage(`Error processing ${file.name}: ${error.message}`, 'error');
            }
        }
        
        appendMessage('Batch processing completed.', 'status');
    };
    input.click();
});

// RAG functionality
ragButton.addEventListener('click', () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.multiple = true;
    input.onchange = async (e) => {
        const files = Array.from(e.target.files);
        if (files.length === 0) {
            // Clear RAG if no files selected
            ragFiles = [];
            ragButton.textContent = 'RAG';
            appendMessage('RAG cleared', 'status');
            return;
        }

        ragFiles = files;
        ragButton.textContent = `RAG (${files.length})`;
        
        const formData = new FormData();
        files.forEach(file => formData.append('files', file));
        
        try {
            appendMessage('Ingesting RAG files...', 'status');
            await fetch('http://localhost:5001/rag/ingest', {
                method: 'POST',
                body: formData
            });
            appendMessage(`RAG initialized with ${files.length} files`, 'status');
        } catch (error) {
            appendMessage(`Error ingesting RAG files: ${error.message}`, 'error');
            ragFiles = [];
            ragButton.textContent = 'RAG';
        }
    };
    input.click();
});

// Clear functionality
clearChatButton.addEventListener('click', () => {
    chatDisplay.innerHTML = '';
    if (currentFile) {
        // Re-display file status after clearing chat
        if (currentFile.type === 'image') {
            appendMessage(`Image loaded: ${currentFile.name}`, 'status');
        } else {
            appendMessage(`File ${currentFile.name} uploaded (${currentFile.wordCount} words)`, 'status');
        }
    }
});

// Clear file functionality
const clearFile = () => {
    currentFile = null;
    imagePreview.innerHTML = '';
    includeFileCheckbox.disabled = true;
    includeFileCheckbox.checked = false;
    
    // Remove file status messages
    const messages = chatDisplay.getElementsByClassName('message');
    Array.from(messages).forEach(msg => {
        if (msg.classList.contains('status') && 
            (msg.textContent.includes('Image loaded:') || 
             msg.textContent.includes('File') && msg.textContent.includes('uploaded'))) {
            msg.remove();
        }
    });
};

// Add clear file button event listener
document.getElementById('clear-file').addEventListener('click', clearFile);

// Stop functionality
stopButton.addEventListener('click', async () => {
    if (currentController) {
        currentController.abort();
        currentController = null;
        
        // Also notify server to stop processing
        try {
            await fetch('http://localhost:5001/stop', {
                method: 'POST'
            });
        } catch (error) {
            console.error('Error stopping server:', error);
        }
        
        appendMessage('Stopped response generation.', 'status');
    }
});

// Send message function
const sendMessage = async () => {
    const message = inputField.value.trim();
    if (message) {
        // Abort any existing request
        if (currentController) {
            currentController.abort();
        }
        
        // Create new controller for this request
        currentController = new AbortController();
        
        appendMessage(message, 'user');
        inputField.value = '';
        
        const developer = developerSelector.value;
        const systemMsg = systemText.value;
        const includeChat = includeChatCheckbox.checked;
        const includeFile = includeFileCheckbox.checked;
        const temperature = parseFloat(tempSlider.value);
        const contextSize = parseInt(contextSlider.value);
        const chunk_size = parseInt(chunkEntry.value);
        const semantic_chunking = semanticChunkingCheckbox.checked;
        
        try {
            // Set model first
            await fetch('http://localhost:5001/set_model', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    model: modelSelector.value,
                    embedding_model: embeddingSelector.value,
                    chunk_size: chunk_size,
                    semantic_chunking: semantic_chunking
                })
            });
            
            // Create message div for assistant's response
            const messageDiv = document.createElement('div');
            messageDiv.classList.add('message', 'assistant');
            chatDisplay.appendChild(messageDiv);
            
            // Create SSE connection for streaming response
            const response = await fetch('http://localhost:5001/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                signal: currentController.signal,
                body: JSON.stringify({
                    message: message,
                    developer: developer,
                    system_msg: systemMsg,
                    include_chat: includeChat,
                    include_file: includeFile,
                    temperature: temperature,
                    context_size: contextSize,
                    file: currentFile,
                    chat_history: includeChat ? chatDisplay.innerText : null,
                    rag_files: ragFiles.length > 0 ? true : null
                })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const {value, done} = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, {stream: true});
                const lines = buffer.split('\n');
                
                // Process all complete lines
                buffer = lines.pop() || ''; // Keep the last incomplete line in buffer
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const content = line.slice(6); // Remove 'data: ' prefix
                        if (content.startsWith('Error: ')) {
                            messageDiv.innerHTML = content;
                            messageDiv.classList.add('error');
                        } else {
                            messageDiv.innerHTML += content;
                        }
                        chatDisplay.scrollTop = chatDisplay.scrollHeight;
                    }
                }
            }
            
            // Process any remaining content in buffer
            if (buffer) {
                const lines = buffer.split('\n');
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const content = line.slice(6);
                        if (content.startsWith('Error: ')) {
                            messageDiv.innerHTML = content;
                            messageDiv.classList.add('error');
                        } else {
                            messageDiv.innerHTML += content;
                        }
                    }
                }
            }
            
            chatDisplay.scrollTop = chatDisplay.scrollHeight;
        } catch (error) {
            if (error.name === 'AbortError') {
                // Don't show error message for intentional stops
                return;
            }
            appendMessage('Error: ' + error.message, 'error');
        } finally {
            currentController = null;
        }
    }
};

// Event listeners for sending messages
sendButton.addEventListener('click', sendMessage);
inputField.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
        e.preventDefault();
        sendMessage();
    }
});
