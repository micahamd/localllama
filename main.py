import tkinter as tk
from tkinter import scrolledtext, filedialog, StringVar, Menu, messagebox
from tkinter import ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import threading
import time
from PIL import Image, ImageTk
import re
import markdown
from markitdown import MarkItDown

# Import our custom modules
from settings import Settings
from conversation import ConversationManager, Message, Conversation
from rag_module import RAG
from rag_visualizer import RAGVisualizerPanel
from models_manager import create_model_manager, OllamaManager, GeminiManager
from error_handler import error_handler, safe_execute

class OllamaChat:
    """Main application class for Ollama Chat."""
    
    def __init__(self, root):
        """Initialize the application and all its components."""
        self.root = root
        self.root.title("Enhanced LLM Chat")
        self.root.geometry("1000x800")  # Larger default window size

        # Set 90s style theme
        self.root.tk_setPalette(
            background="#d9d9d9",  # Light gray background
            foreground="black",
            activeBackground="#ececec",
            activeForeground="black",
            highlightColor="black",
            highlightBackground="#d9d9d9"
        )
        self.root.option_add("*Font", "TkFixedFont") # Use system fixed font


        # Initialize components
        self.settings = Settings()
        self.conversation_manager = ConversationManager()

        # Create minimal UI elements required for error display
        self.create_main_frame()
        self.create_chat_display()  # Create chat display FIRST for error handling

        # Now setup error handler with display callback
        self.setup_error_handler()

        # Continue with the rest of initialization
        self.init_variables()
        self.create_menu()
        self.create_sidebar()
        self.create_input_area()
        self.create_status_bar()
        self.configure_tags()
        self.setup_rag()
        self.load_models()
        self.bind_events()

        # Apply saved settings
        self.apply_settings()

        # Show welcome message
        self.display_message("Welcome to Enhanced LLM Chat!\n", "status")
        self.display_message("Drop files here or type a message to begin.\n", "status")

    def create_main_frame(self):
        """Create the main application frame."""
        self.main_frame = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)  # Use PanedWindow
        self.main_frame.pack(fill=tk.BOTH, expand=True)

    def setup_error_handler(self):
        """Configure the error handler with a display callback."""
        error_handler.set_display_callback(self.display_error_message)
    
    def display_error_message(self, message, tag):
        """Callback for the error handler to display errors."""
        self.display_message(f"\nError: {message}\n", tag)
    
    @safe_execute("Initializing variables")
    def init_variables(self):
        """Initialize application variables."""
        # Core variables
        self.file_img = None
        self.file_content = None
        self.file_type = None
        self.word_count = 0
        self.selected_model = None
        self.selected_embedding_model = None
        self.developer = StringVar(value=self.settings.get("developer", "ollama"))
        self.temperature = tk.DoubleVar(value=self.settings.get("temperature", 0.7))
        self.context_size = tk.IntVar(value=self.settings.get("context_size", 4096))
        self.chunk_size = tk.IntVar(value=self.settings.get("chunk_size", 128))
        self.semantic_chunking_var = tk.BooleanVar(value=self.settings.get("semantic_chunking", False))
        self.include_chat_var = tk.BooleanVar(value=self.settings.get("include_chat", False))
        self.show_image_var = tk.BooleanVar(value=self.settings.get("show_image", True))
        self.include_file_var = tk.BooleanVar(value=self.settings.get("include_file", True))
        
        # Processing control
        self.is_processing = False
        self.active_stream = None
        self.stop_event = threading.Event()
        self.rag_files = []
        
        # RAG visualization
        self.rag_visualizer = None
    
    def create_menu(self):
        """Create the application menu."""
        self.menu_bar = Menu(self.root)
        self.root.config(menu=self.menu_bar)
        
        # File menu
        file_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Conversation", command=self.new_conversation)
        file_menu.add_command(label="Save Conversation", command=self.save_conversation)
        file_menu.add_command(label="Load Conversation", command=self.load_conversation)
        file_menu.add_separator()
        file_menu.add_command(label="Select RAG Files", command=self.select_rag_files)
        file_menu.add_command(label="Clear RAG Files", command=self.clear_rag_files)
        file_menu.add_separator()
        file_menu.add_command(label="Save Settings", command=self.save_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Edit menu
        edit_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Copy", command=self.copy_selection)
        edit_menu.add_command(label="Clear Chat", command=self.clear_chat)
        edit_menu.add_command(label="Clear File", command=self.clear_file)
        
        # View menu
        view_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Show RAG Visualization", command=self.show_rag_visualization)
        view_menu.add_checkbutton(label="Show Image Preview", variable=self.show_image_var, 
                                  command=self.on_show_image_toggle)
        
        # API menu
        api_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="API", menu=api_menu)
        api_menu.add_command(label="Configure Gemini API Key", command=self.prompt_for_api_key)
        api_menu.add_command(label="Reset Gemini API Key", command=self.reset_api_key)
        api_menu.add_separator()
        api_menu.add_command(label="Configure DeepSeek API Key", command=self.prompt_for_deepseek_api_key)
        api_menu.add_command(label="Reset DeepSeek API Key", command=self.reset_deepseek_api_key)

        # Help menu
        help_menu = Menu(self.menu_bar, tearoff=0)
        help_menu.add_cascade(label="Help", menu=help_menu)
    
    def create_sidebar(self):
        """Create the sidebar with settings and model selection."""
        self.sidebar_frame = ttk.Frame(self.main_frame)  # Sidebar is now part of main_frame
        # self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y) # Pack sidebar on the left, taking full vertical space
        self.main_frame.add(self.sidebar_frame)  # Add to PanedWindow
        
        # Sidebar title
        sidebar_title = ttk.Label(self.sidebar_frame, text="Settings", font=("Arial", 14, "bold"))
        sidebar_title.pack(pady=10)
        
        # Models settings frame
        model_frame = ttk.LabelFrame(self.sidebar_frame, text="Models")
        model_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Developer selector
        ttk.Label(model_frame, text="Developer:").pack(anchor="w", padx=5, pady=2)
        developer_selector = ttk.Combobox(model_frame, textvariable=self.developer,
                                         values=['ollama', 'google', 'deepseek'], state='readonly')  # Added 'deepseek'
        developer_selector.pack(fill=tk.X, padx=5, pady=2)
        developer_selector.bind('<<ComboboxSelected>>', self.on_developer_changed)
        
        # LLM Model selector
        ttk.Label(model_frame, text="LLM Model:").pack(anchor="w", padx=5, pady=2)
        self.model_selector = ttk.Combobox(model_frame, state='readonly')
        self.model_selector.pack(fill=tk.X, padx=5, pady=2)
        self.model_selector.bind('<<ComboboxSelected>>', self.on_model_selected)
        
        # Embedding Model selector
        ttk.Label(model_frame, text="Embedding Model:").pack(anchor="w", padx=5, pady=2)
        self.embedding_selector = ttk.Combobox(model_frame, state='readonly')
        self.embedding_selector.pack(fill=tk.X, padx=5, pady=2)
        self.embedding_selector.bind('<<ComboboxSelected>>', self.on_embedding_model_selected)
        
        # Parameters settings frame
        params_frame = ttk.LabelFrame(self.sidebar_frame, text="Parameters")
        params_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Temperature control
        ttk.Label(params_frame, text="Temperature:").pack(anchor="w", padx=5, pady=2)
        temp_frame = ttk.Frame(params_frame)
        temp_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.temp_slider = ttk.Scale(
            temp_frame,
            from_=0.0,
            to=2.0,
            orient='horizontal',
            variable=self.temperature,
            command=self.on_temp_change
        )
        self.temp_slider.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        self.temp_label = ttk.Label(temp_frame, text=f"{self.temperature.get():.2f}")
        self.temp_label.pack(side=tk.RIGHT, padx=5)
        
        # Context size control
        ttk.Label(params_frame, text="Context Size:").pack(anchor="w", padx=5, pady=2)
        context_frame = ttk.Frame(params_frame)
        context_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.context_slider = ttk.Scale(
            context_frame,
            from_=1000,
            to=128000,
            orient='horizontal',
            variable=self.context_size,
            command=self.on_context_change
        )
        self.context_slider.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        self.context_label = ttk.Label(context_frame, text=str(self.context_size.get()))
        self.context_label.pack(side=tk.RIGHT, padx=5)
        
        # RAG settings frame
        rag_frame = ttk.LabelFrame(self.sidebar_frame, text="RAG Settings")
        rag_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Chunk size
        ttk.Label(rag_frame, text="Chunk Size:").pack(anchor="w", padx=5, pady=2)
        self.chunk_entry = ttk.Entry(rag_frame, textvariable=self.chunk_size, width=5)
        self.chunk_entry.pack(anchor="w", padx=5, pady=2)
        
        # Semantic chunking checkbox
        semantic_chunking_checkbox = ttk.Checkbutton(
            rag_frame,
            text="Use Semantic Chunking (Slow)",
            variable=self.semantic_chunking_var
        )
        semantic_chunking_checkbox.pack(anchor="w", padx=5, pady=2)
        
        # Options frame
        options_frame = ttk.LabelFrame(self.sidebar_frame, text="Options")
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Include chat history
        include_chat_checkbox = ttk.Checkbutton(
            options_frame, 
            text="Include chat history",
            variable=self.include_chat_var
        )
        include_chat_checkbox.pack(anchor="w", padx=5, pady=2)
        
        # Show image preview
        show_image_checkbox = ttk.Checkbutton(
            options_frame, 
            text="Show image preview",
            variable=self.show_image_var,
            command=self.on_show_image_toggle
        )
        show_image_checkbox.pack(anchor="w", padx=5, pady=2)
        
        # Include file content
        self.include_file_checkbox = ttk.Checkbutton(
            options_frame,
            text="Include file content",
            variable=self.include_file_var
        )
        self.include_file_checkbox.pack(anchor="w", padx=5, pady=2)
        
        # Conversations section
        conversations_frame = ttk.LabelFrame(self.sidebar_frame, text="Conversations")
        conversations_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Conversation buttons
        conv_buttons_frame = ttk.Frame(conversations_frame)
        conv_buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(conv_buttons_frame, text="New", command=self.new_conversation).pack(side=tk.LEFT, padx=2)
        ttk.Button(conv_buttons_frame, text="Save", command=self.save_conversation).pack(side=tk.LEFT, padx=2)
        ttk.Button(conv_buttons_frame, text="Load", command=self.load_conversation).pack(side=tk.LEFT, padx=2)
        
        # Recent conversations list
        ttk.Label(conversations_frame, text="Recent:").pack(anchor="w", padx=5)
        self.conversations_listbox = tk.Listbox(conversations_frame, height=5)
        self.conversations_listbox.pack(fill=tk.X, padx=5, pady=2)
        self.conversations_listbox.bind("<Double-1>", self.on_conversation_selected)
        
        # Update the conversations list
        self.update_conversations_list()
    
    def create_chat_display(self):
        """Create the chat display area."""
        # Create a frame for the chat and input areas
        self.chat_input_frame = ttk.Frame(self.main_frame)
        self.main_frame.add(self.chat_input_frame)
        
        # Chat area - now directly in main_frame, below sidebar
        chat_frame = ttk.Frame(self.chat_input_frame) 
        chat_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5) # Pack below sidebar
        
        # System instructions area
        system_frame = ttk.LabelFrame(chat_frame, text="System Instructions")
        system_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.system_text = scrolledtext.ScrolledText(
            system_frame, 
            height=2, 
            wrap=tk.WORD,
            font=("Arial", 11)
        )
        self.system_text.pack(fill=tk.X, padx=5, pady=5)
        self.system_text.insert('1.0', self.settings.get("system_prompt", "You are a helpful AI assistant who only gives accurate and objective information."))
        
        # Main chat display
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=("Arial", 12),
            bg="#1E1E1E",
            fg="#FFFFFF",
            insertbackground="#FFFFFF"
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Make chat display read-only but allow selection
        self.chat_display.config(state=tk.DISABLED)
        
        # Image preview
        self.image_preview = ttk.Label(chat_frame)
        self.image_preview.pack(padx=5, pady=5)
    
    def create_input_area(self):
        """Create the input area for user messages."""
        # Input area - now directly in main_frame, below chat display
        input_frame = ttk.Frame(self.chat_input_frame)
        input_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5) # Pack below chat display
        
        # Input field with scrollbar
        self.input_field = scrolledtext.ScrolledText(
            input_frame,
            wrap=tk.WORD,
            height=4,
            font=("Arial", 12),
            padx=5,
            pady=5
        )
        self.input_field.pack(side=tk.TOP, fill=tk.X, expand=True)
        
        # Button frame
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        # RAG indicator and button
        self.rag_indicator = ttk.Label(
            button_frame, 
            text="RAG: Not Active",
            foreground="grey"
        )
        self.rag_indicator.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="Select RAG Files", 
            command=self.select_rag_files
        ).pack(side=tk.LEFT, padx=2)
        
        # Spacer
        ttk.Frame(button_frame).pack(side=tk.LEFT, expand=True)
        
        # Action buttons
        ttk.Button(
            button_frame, 
            text="Clear Chat", 
            command=self.clear_chat
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            button_frame, 
            text="Clear File", 
            command=self.clear_file
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            button_frame, 
            text="Batch Process", 
            command=self.start_batch_process
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            button_frame, 
            text="Stop", 
            command=self.stop_processing
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            button_frame, 
            text="Send", 
            command=self.send_message
        ).pack(side=tk.LEFT, padx=2)
    
    def create_status_bar(self):
        """Create the status bar at the bottom of the application."""
        self.status_bar = ttk.Label(
            self.root, 
            text="Ready", 
            relief=tk.SUNKEN, 
            anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def configure_tags(self):
        """Configure text tags for styling chat messages."""
        self.chat_display.tag_configure('user', foreground='#6699CC')
        self.chat_display.tag_configure('assistant', foreground='#99CC99')
        self.chat_display.tag_configure('system', foreground='#CC9999')
        self.chat_display.tag_configure('error', foreground='#FF6666')
        self.chat_display.tag_configure('status', foreground='#999999')
        self.chat_display.tag_configure('code', font=("Consolas", 12), background="#2A2A2A", foreground="#E0E0E0")
    
    def bind_events(self):
        """Bind events to widgets."""
        # Bind Ctrl+Enter AND Enter to send message
        self.input_field.bind('<Control-Return>', lambda e: self.send_message())
        self.input_field.bind('<Return>', lambda e: self.send_message() if not e.state & 0x0001 else None)
        # Don't trigger on Shift+Enter to allow for multi-line input
        
        # Bind drop for file handling
        self.chat_display.drop_target_register(DND_FILES)
        self.chat_display.dnd_bind('<<Drop>>', self.handle_drop)
        
        # Allow Copy in chat display
        self.chat_display.bind("<Control-c>", lambda e: self.chat_display.event_generate("<<Copy>>"))
        
        # Handle application close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    @safe_execute("Setting up RAG")
    def setup_rag(self):
        """Initialize the RAG system."""
        embedding_model = self.settings.get("embedding_model", "")
        chunk_size = self.settings.get("chunk_size", 128)
        semantic_chunking = self.settings.get("semantic_chunking", False)
        
        self.rag = RAG(
            embedding_model_name=embedding_model,
            chunk_size=chunk_size,
            use_semantic_chunking=semantic_chunking
        )
        
        # Create RAG visualizer
        self.rag_visualizer = RAGVisualizerPanel(self.root)
    
    @safe_execute("Loading models")
    def load_models(self):
        """Load and initialize the AI models."""
        self.model_manager = create_model_manager(self.developer.get())
        self.update_model_list()
        
        # Check if using Google and show API key dialog if needed
        if self.developer.get().lower() == "google" and not self.model_manager.api_config.is_configured():
            self.prompt_for_api_key()
    
    def prompt_for_api_key(self):
        """Prompt the user to enter their Google Gemini API key if not configured."""
        from tkinter import simpledialog

        api_key = simpledialog.askstring(
            "Google Gemini API Key",
            "Enter your Google Gemini API key (will be saved securely):",
            show='*'  # Show asterisks for security
        )

        if api_key:
            success = self.model_manager.save_api_key(api_key)
            if success:
                self.display_message("\nAPI key saved successfully.\n", "status")
            else:
                self.display_message("\nFailed to save API key. Check permissions.\n", "error")

    def prompt_for_deepseek_api_key(self):
        """Prompt the user to enter their DeepSeek API key if not configured."""
        from tkinter import simpledialog

        api_key = simpledialog.askstring(
            "DeepSeek API Key",
            "Enter your DeepSeek API key (will be saved securely):",
            show='*'
        )

        if api_key:
            success = self.model_manager.save_api_key(api_key)
            if success:
                self.display_message("\nAPI key saved successfully.\n", "status")
            else:
                self.display_message("\nFailed to save API key. Check permissions.\n", "error")

    @safe_execute("Applying settings")
    def apply_settings(self):
        """Apply saved settings to the UI components."""
        # Set model selections if available
        llm_model = self.settings.get("llm_model", "")
        if llm_model and llm_model in self.model_selector["values"]:
            self.model_selector.set(llm_model)
            self.selected_model = llm_model
        
        embedding_model = self.settings.get("embedding_model", "")
        if embedding_model and embedding_model in self.embedding_selector["values"]:
            self.embedding_selector.set(embedding_model)
            self.selected_embedding_model = embedding_model
            
            # Update RAG with the selected embedding model
            if self.rag:
                self.rag.update_embedding_function(embedding_model)
        
        # Update chunk size trace
        self.chunk_size.trace_add("write", self.update_rag_chunk_size)
        
        # Update semantic chunking trace
        self.semantic_chunking_var.trace_add("write", self.update_rag_semantic_chunking)
    
    def update_rag_chunk_size(self, *args):
        """Update RAG chunk size when the setting changes."""
        if hasattr(self, 'rag'):
            self.rag.chunk_size = self.chunk_size.get()
    
    def update_rag_semantic_chunking(self, *args):
        """Update RAG semantic chunking setting when the checkbox changes."""
        if hasattr(self, 'rag'):
            self.rag.use_semantic_chunking = self.semantic_chunking_var.get()
            
            # Re-initialize the sentence transformer if semantic chunking is enabled
            if self.rag.use_semantic_chunking:
                try:
                    from sentence_transformers import SentenceTransformer
                    self.rag.sentence_transformer = SentenceTransformer('all-mpnet-base-v2')
                except Exception as e:
                    error_handler.handle_error(e, "Loading sentence transformer")
                    self.rag.sentence_transformer = None
            else:
                self.rag.sentence_transformer = None
    
    def on_developer_changed(self, event):
        """Handle developer selection change."""
        developer = self.developer.get()
        self.model_manager = create_model_manager(developer)
        self.update_model_list()
        self.display_message(f"\nSwitched to {developer} models\n", "status")
        
        # Check if API key is needed for Google
        if developer.lower() == "google" and not self.model_manager.api_config.is_configured():
            self.prompt_for_api_key()
    
    def on_model_selected(self, event):
        """Handle model selection change."""
        self.selected_model = self.model_selector.get()
        self.display_message(f"\nSwitched to model: {self.selected_model}\n", "status")
    
    def on_embedding_model_selected(self, event):
        """Handle embedding model selection change."""
        self.selected_embedding_model = self.embedding_selector.get()
        self.display_message(f"\nSwitched to embedding model: {self.selected_embedding_model}\n", "status")
        
        # Update the embedding function in the RAG class
        if hasattr(self, 'rag'):
            self.rag.update_embedding_function(self.selected_embedding_model)
    
    def on_temp_change(self, value):
        """Update temperature label when slider moves."""
        self.temp_label.config(text=f"{float(value):.2f}")
    
    def on_context_change(self, value):
        """Update context window label when slider moves."""
        self.context_label.config(text=f"{int(float(value))}")
    
    def on_show_image_toggle(self):
        """Show or hide the image preview depending on the checkbox."""
        if self.show_image_var.get() and self.file_type == 'image' and self.file_img:
            pil_img = Image.open(self.file_img)
            pil_img.thumbnail((300, 300))
            self.preview_image = ImageTk.PhotoImage(pil_img)
            self.image_preview.config(image=self.preview_image)
        else:
            self.image_preview.config(image="")
    
    def handle_drop(self, event):
        """Handle file drop event."""
        file_path = event.data.strip('{}')
        self.file_type = self.get_file_type(file_path)
        
        # Enable the include file checkbox
        self.include_file_checkbox.state(['!disabled'])
        self.include_file_var.set(True)
        
        if self.file_type == 'image':
            self.file_img = file_path
            self.file_content = None
            if self.show_image_var.get():
                pil_img = Image.open(file_path)
                pil_img.thumbnail((300, 300))
                self.preview_image = ImageTk.PhotoImage(pil_img)
                self.image_preview.config(image=self.preview_image)
        else:
            self.file_img = None
            self.file_content = self.extract_content(file_path)
            if self.file_content:
                self.word_count = len(re.findall(r'\w+', self.file_content))
        
        self.update_status()
    
    def get_file_type(self, file_path):
        """Determine the file type from its extension."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            return 'image'
        return 'document'
    
    def extract_content(self, file_path):
        """Extract text content from a file."""
        try:
            if self.get_file_type(file_path) == 'document':
                md = MarkItDown()
                result = md.convert(file_path)
                return result.text_content
            return None
        except Exception as e:
            error_handler.handle_error(e, "Extracting file content")
            return None
    
    def update_status(self):
        """Update status bar with current file information."""
        if self.file_img and self.file_type == 'image':
            self.status_bar["text"] = f"Image loaded: {os.path.basename(self.file_img)}"
        elif self.file_content:
            self.status_bar["text"] = f"Document loaded: {self.word_count} words"
        else:
            self.status_bar["text"] = "Ready"
    
    @safe_execute("Sending message")
    def send_message(self):
        """Process and send the user's message."""
        user_input = self.input_field.get("1.0", tk.END).strip()
        if not user_input:
            return
        
        # Add to conversation manager
        self.conversation_manager.add_message_to_active("user", user_input)
        
        # Display user message
        self.display_message("\n", 'user')
        self.display_message(f"{user_input}\n", 'user')
        
        self.input_field.delete("1.0", tk.END)
        
        # Prepare message content
        content = user_input
        
        # Include file content based on the checkbox
        if self.include_file_var.get() and self.file_content:
            content += f"\n\nDocument content:\n{self.file_content}"
        
        # Include chat history if selected
        if self.include_chat_var.get():
            chat_history = self.get_chat_history()
            content += f"\n\nChat history:\n{chat_history}"
        
        # Include RAG context if available
        rag_results = []
        if hasattr(self, 'rag') and self.rag_files:
            rag_start_time = time.time()
            rag_context = self.rag.retrieve_context(query=user_input)
            rag_end_time = time.time()
            
            if rag_context and rag_context != "No context retrieved":
                content += f"\n\nRelevant context:\n{rag_context}"
                
                # Store RAG results for visualization
                rag_results = self.get_rag_chunks(user_input)
                
                # Update RAG visualizer
                if self.rag_visualizer:
                    self.rag_visualizer.update_chunks(rag_results)
                    self.rag_visualizer.update_metrics({
                        "processing_time": (rag_end_time - rag_start_time) * 1000,  # ms
                        "embedding_model": self.selected_embedding_model
                    })
        
        # Prepare message
        message = {
            'role': 'user',
            'content': content
        }
        
        # Add image if available and included
        if self.include_file_var.get() and self.file_img and self.file_type == 'image':
            with open(self.file_img, 'rb') as img_file:
                message['images'] = [img_file.read()]
        
        # Send message in separate thread
        threading.Thread(target=self.get_response, args=(message, rag_results)).start()
    
    def get_chat_history(self):
        """Get formatted chat history for context."""
        history = []
        for msg in self.conversation_manager.active_conversation.messages:
            if msg.role in ['user', 'assistant']:
                history.append(f"{msg.role.capitalize()}: {msg.content}")
        return "\n\n".join(history)
    
    def get_rag_chunks(self, query):
        """Get RAG chunks with metadata for visualization."""
        if not hasattr(self, 'rag') or not self.rag_files:
            return []
            
        try:
            # Get chunks and their scores from the RAG module
            results = self.rag.collection.query(
                query_texts=[query], 
                n_results=5,
                include=['documents', 'distances', 'metadatas']
            )
            
            chunks = []
            if results and 'documents' in results and len(results['documents']) > 0:
                for i, (doc, score) in enumerate(zip(results['documents'][0], results['distances'][0])):
                    # Convert distance to similarity score (1 - normalized_distance)
                    similarity = 1.0 - min(1.0, score / 2.0)  # Simple normalization
                    
                    # Extract source file if available in metadata
                    source = "Unknown"
                    if 'metadatas' in results and len(results['metadatas']) > 0:
                        if len(results['metadatas'][0]) > i:
                            metadata = results['metadatas'][0][i]
                            if metadata and 'source' in metadata:
                                source = metadata['source']
                    
                    chunks.append({
                        'text': doc,
                        'score': similarity,
                        'source': source,
                        'total_chunks': len(self.rag.collection.get()['documents'])
                    })
            
            return chunks
        except Exception as e:
            error_handler.handle_error(e, "Getting RAG chunks")
            return []
    
    @safe_execute("Getting model response")
    def get_response(self, message, rag_results=None):
        """Get a response from the selected model and process it."""
        self.stop_event.clear()
        self.is_processing = True
        self.status_bar["text"] = "Processing..."
        
        try:
            self.display_message("\n", 'assistant')
            
            # Get system instructions
            system_msg = self.system_text.get('1.0', tk.END).strip()
            
            # Create messages array with system message first
            messages = []
            if system_msg:
                messages.append({
                    'role': 'system',
                    'content': system_msg
                })
            
            messages.append(message)
            
            # Create a response position mark
            self.chat_display["state"] = "normal"
            response_position = self.chat_display.index(tk.END + "-1c")
            self.chat_display["state"] = "disabled"
            
            full_response = ""
            
            # Get streaming response from model manager
            stream = self.model_manager.get_response(
                messages=messages,
                model=self.selected_model,
                temperature=self.temperature.get(),
                context_size=self.context_size.get()
            )
            
            self.active_stream = stream
            
            try:
                for chunk in stream:
                    if self.stop_event.is_set():
                        break
                    
                    if chunk and 'message' in chunk and 'content' in chunk['message']:
                        content = chunk['message']['content']
                        
                        # Only append new content
                        if content:
                            full_response += content
                            
                            # Insert only the new chunk, not the full response
                            self.chat_display["state"] = "normal"
                            self.chat_display.insert(tk.END, content, 'assistant')
                            self.chat_display["state"] = "disabled"
                            self.chat_display.see(tk.END)
            finally:
                self.active_stream = None
                
                # Add the completed response to conversation history
                if full_response:
                    self.conversation_manager.add_message_to_active("assistant", full_response)
                    
                    # If RAG was used, highlight relevant chunks
                    if self.rag_visualizer and rag_results:
                        self.rag_visualizer.highlight_rag_matches(self.chat_display, message['content'], rag_results)
                        
                        # Update sources in RAG visualizer
                        source_data = self.prepare_source_data(rag_results)
                        self.rag_visualizer.update_sources(source_data)
                
                self.is_processing = False
                self.status_bar["text"] = "Ready"
                
        except Exception as e:
            error_msg = error_handler.handle_error(e, "Getting response")
            self.display_message(f"\nError: {error_msg}\n", 'error')
            self.is_processing = False
            self.status_bar["text"] = "Error"
    
    def prepare_source_data(self, rag_results):
        """Prepare source data from RAG results for the visualizer."""
        sources = {}
        
        # Group chunks by source
        for chunk in rag_results:
            source = chunk.get('source', 'Unknown')
            if source not in sources:
                sources[source] = {
                    'file': source,
                    'chunk_count': 1,
                    'relevance': chunk.get('score', 0)
                }
            else:
                sources[source]['chunk_count'] += 1
                sources[source]['relevance'] += chunk.get('score', 0)
        
        # Calculate average relevance
        for source in sources.values():
            if source['chunk_count'] > 0:
                source['relevance'] /= source['chunk_count']
        
        return list(sources.values())
    
    def display_message(self, message, tag=None):
        """Display a message in the chat window with optional tags."""
        self.chat_display["state"] = "normal"
        
        if tag == 'assistant':
            # Process potential code blocks in assistant responses
            parts = message.split('```')
            for i, part in enumerate(parts):
                if i % 2 == 0:  # Regular text
                    self.chat_display.insert(tk.END, part, 'assistant')
                else:  # Code block
                    self.chat_display.insert(tk.END, '\n', 'assistant')  # Newline before code
                    self.chat_display.insert(tk.END, part.strip(), 'code')  # Code with code tag
                    self.chat_display.insert(tk.END, '\n', 'assistant')  # Newline after code
        else:
            self.chat_display.insert(tk.END, message, tag)
        
        self.chat_display["state"] = "disabled"
        self.chat_display.see(tk.END)
    
    def save_settings(self):
        """Save current settings to the settings file."""
        settings_data = {
            "developer": self.developer.get(),
            "llm_model": self.selected_model,
            "embedding_model": self.selected_embedding_model,
            "temperature": self.temperature.get(),
            "context_size": self.context_size.get(),
            "chunk_size": self.chunk_size.get(),
            "semantic_chunking": self.semantic_chunking_var.get(),
            "include_chat": self.include_chat_var.get(),
            "show_image": self.show_image_var.get(),
            "include_file": self.include_file_var.get(),
            "system_prompt": self.system_text.get('1.0', tk.END).strip()
        }
        
        self.settings.update(settings_data)
        self.settings.save_settings()
        self.display_message("\nSettings saved successfully.\n", "status")
    
    def new_conversation(self):
        """Start a new conversation."""
        # Ask for confirmation if there are messages in the current conversation
        if self.conversation_manager.active_conversation.messages:
            confirm = messagebox.askyesno(
                "New Conversation", 
                "Starting a new conversation will clear the current chat. Continue?"
            )
            if not confirm:
                return
        
        # Create a new conversation
        self.conversation_manager.new_conversation(model=self.selected_model)
        
        # Clear the chat display
        self.clear_chat()
        
        # Update conversations list
        self.update_conversations_list()
        
        # Show status message
        self.display_message("Started a new conversation.\n", "status")
    
    def save_conversation(self):
        """Save the current conversation."""
        if not self.conversation_manager.active_conversation.messages:
            messagebox.showinfo("Save Conversation", "No messages to save.")
            return
        
        result = self.conversation_manager.save_conversation()
        self.display_message(f"\n{result}\n", "status")
        
        # Update conversations list
        self.update_conversations_list()
    
    def load_conversation(self):
        """Load a saved conversation."""
        # Get list of conversation files
        files = self.conversation_manager.list_conversations()
        
        if not files:
            messagebox.showinfo("Load Conversation", "No saved conversations found.")
            return
        
        # File dialog to select the conversation to load
        filepath = filedialog.askopenfilename(
            title="Select Conversation File",
            initialdir=self.conversation_manager.conversations_dir,
            filetypes=[("JSON files", "*.json")]
        )
        
        if not filepath:
            return
            
        # Load the selected conversation
        conversation = self.conversation_manager.load_conversation(filepath)
        
        if conversation:
            # Update model if it was saved with the conversation
            if conversation.model and conversation.model in self.model_selector["values"]:
                self.model_selector.set(conversation.model)
                self.selected_model = conversation.model
            
            # Render the conversation in the chat display
            self.conversation_manager.render_conversation(self.chat_display, {
                'user': {'foreground': '#6699CC'},
                'assistant': {'foreground': '#99CC99'},
                'system': {'foreground': '#CC9999'},
                'error': {'foreground': '#FF6666'},
                'status': {'foreground': '#999999'},
                'code': {'font': ('Consolas', 12), 'background': '#2A2A2A', 'foreground': '#E0E0E0'}
            })
            
            self.display_message(f"\nLoaded conversation: {conversation.title}\n", "status")
    
    def update_conversations_list(self):
        """Update the list of recent conversations in the sidebar."""
        # Clear current list
        self.conversations_listbox.delete(0, tk.END)
        
        # Get list of conversation files
        files = self.conversation_manager.list_conversations()
        
        # Sort by modification time (newest first)
        files.sort(key=lambda f: os.path.getmtime(os.path.join(
            self.conversation_manager.conversations_dir, f)), reverse=True)
        
        # Add to listbox (only most recent 10)
        for filename in files[:10]:
            self.conversations_listbox.insert(tk.END, filename)
    
    def on_conversation_selected(self, event):
        """Handle selection of a conversation from the listbox."""
        selection = event.widget.curselection()
        if selection:
            filename = event.widget.get(selection[0])
            filepath = os.path.join(self.conversation_manager.conversations_dir, filename)
            
            if os.path.exists(filepath):
                # Ask for confirmation
                confirm = messagebox.askyesno(
                    "Load Conversation", 
                    f"Load conversation '{filename}'? This will replace the current conversation."
                )
                
                if confirm:
                    self.conversation_manager.load_conversation(filepath)
                    
                    # Render the conversation in the chat display
                    self.conversation_manager.render_conversation(self.chat_display, {
                        'user': {'foreground': '#6699CC'},
                        'assistant': {'foreground': '#99CC99'},
                        'system': {'foreground': '#CC9999'},
                        'error': {'foreground': '#FF6666'},
                        'status': {'foreground': '#999999'},
                        'code': {'font': ('Consolas', 12), 'background': '#2A2A2A', 'foreground': '#E0E0E0'}
                    })
    
    def show_rag_visualization(self):
        """Show the RAG visualization panel."""
        if self.rag_visualizer:
            self.rag_visualizer.show()
    
    def update_model_list(self):
        """Update the model selection dropdown with available models."""
        try:
            # Get LLM models
            llm_models = self.model_manager.get_llm_models()
            
            # Update the LLM combobox
            self.model_selector['values'] = llm_models or []
            if llm_models:
                if self.selected_model in llm_models:
                    self.model_selector.set(self.selected_model)
                else:
                    self.model_selector.set(llm_models[0])
                    self.selected_model = llm_models[0]
            
            # Get embedding models
            embedding_models = self.model_manager.get_embedding_models()
            
            # Update the embedding combobox
            self.embedding_selector['state'] = 'readonly'
            self.embedding_selector['values'] = embedding_models or []
            if embedding_models:
                if self.selected_embedding_model in embedding_models:
                    self.embedding_selector.set(self.selected_embedding_model)
                else:
                    self.embedding_selector.set(embedding_models[0])
                    self.selected_embedding_model = embedding_models[0]
            
            if not llm_models:
                self.display_message("\nNo models found. Please check if the selected provider is available.\n", "error")
                
        except Exception as e:
            error_handler.handle_error(e, "Updating model list")
    
    def select_rag_files(self):
        """Open file dialog to select files for RAG."""
        selected_files = filedialog.askopenfilenames(title="Select Files for RAG")
        
        if not selected_files:
            return
        
        # Clear any previous RAG cache
        self.rag.clear_db()
        self.rag_files = selected_files
        
        # Update RAG indicator
        self.rag_indicator.config(text=f"RAG: Active ({len(self.rag_files)} files)", foreground="green")
        
        # Show status message
        self.display_message(f"\nProcessing {len(self.rag_files)} files for RAG...\n", "status")
        
        # Process files in a separate thread to avoid freezing the UI
        threading.Thread(target=self._process_rag_files).start()
    
    def _process_rag_files(self):
        """Process the selected RAG files in a background thread."""
        try:
            self.rag.ingest_data(self.rag_files)
            
            # Update the UI from the main thread
            self.root.after(0, lambda: self.display_message(f"\nRAG processing complete. Ready to use with {len(self.rag_files)} files.\n", "status"))
        except Exception as e:
            error_msg = error_handler.handle_error(e, "Processing RAG files")
            # Update the UI from the main thread
            self.root.after(0, lambda: self.display_message(f"\nError processing RAG files: {error_msg}\n", "error"))
    
    def clear_rag_files(self):
        """Clear the RAG database and selected files."""
        if hasattr(self, 'rag'):
            self.rag.clear_db()
            
        self.rag_files = []
        self.rag_indicator.config(text="RAG: Not Active", foreground="grey")
        self.display_message("\nRAG database cleared.\n", "status")
    
    def start_batch_process(self):
        """Start batch processing on multiple files."""
        if not self.input_field.get("1.0", tk.END).strip():
            self.display_message("\nPlease enter a prompt first.\n", "error")
            return
        
        if not self.selected_model:
            self.display_message("\nNo model selected!\n", "error")
            return
        
        files = filedialog.askopenfilenames(title="Select Files for Batch Processing")
        if files:
            threading.Thread(target=self.process_files, args=(files,)).start()
    
    def process_files(self, files):
        """Process multiple files with the same prompt."""
        base_prompt = self.input_field.get("1.0", tk.END).strip()
        self.display_message(f"\nStarting batch processing of {len(files)} files\n", "status")
        
        for idx, file_path in enumerate(files, 1):
            if self.stop_event.is_set():
                break
            
            self.display_message(f"\nProcessing file {idx}/{len(files)}: {os.path.basename(file_path)}\n", "status")
            
            file_type = self.get_file_type(file_path)
            content = base_prompt  # base prompt for each file
            
            if file_type == 'image':
                with open(file_path, 'rb') as img_file:
                    file_data = img_file.read()
                message = {
                    'role': 'user',
                    'content': content,
                    'images': [file_data]
                }
            else:
                file_content = self.extract_content(file_path)
                if file_content:
                    word_count = len(re.findall(r'\w+', file_content))
                    self.display_message(f"\nFile has {word_count} words\n", "status")
                    content += f"\n\nDocument content:\n{file_content}\n\nFile path: {file_path}"
                message = {'role': 'user', 'content': content}
            
            # Get system instructions
            system_msg = self.system_text.get("1.0", tk.END).strip()
            messages = []
            if system_msg:
                messages.append({'role': 'system', 'content': system_msg})
            messages.append(message)
            
            self.display_message(f"\nAssistant (for {os.path.basename(file_path)}): ", 'assistant')
            
            # Get streaming response
            stream = self.model_manager.get_response(
                messages=messages,
                model=self.selected_model,
                temperature=self.temperature.get(),
                context_size=self.context_size.get()
            )
            self.active_stream = stream
            
            full_response = ""
            try:
                for chunk in stream:
                    if self.stop_event.is_set():
                        break
                    
                    if chunk and 'message' in chunk and 'content' in chunk['message']:
                        content = chunk['message']['content']
                        full_response += content
                        self.display_message(content, 'assistant')
            finally:
                self.active_stream = None
                
                # Add to conversation history
                if full_response:
                    batch_msg = f"Batch result for {os.path.basename(file_path)}: {full_response}"
                    self.conversation_manager.add_message_to_active("assistant", batch_msg)
            
            self.display_message(f"\nCompleted processing file {idx}/{len(files)}\n", "status")
        
        self.display_message("\nBatch processing completed.\n", "status")
    
    def clear_chat(self):
        """Clear the chat display."""
        self.chat_display["state"] = "normal"
        self.chat_display.delete(1.0, tk.END)
        self.chat_display["state"] = "disabled"
        self.status_bar["text"] = "Ready"
    
    def clear_file(self):
        """Clear the uploaded file or image from memory."""
        # Clear file-related variables
        self.file_content = None
        self.file_img = None
        self.file_type = None
        self.word_count = 0
        
        # Clear image preview
        self.image_preview.config(image="")
        self.preview_image = None  # Clear reference to prevent memory leaks
        
        # Disable file checkbox
        self.include_file_var.set(False)
        
        # Update status
        self.status_bar["text"] = "Ready"
        self.display_message("\nFile cleared.\n", "status")
    
    def copy_selection(self):
        """Copy selected text to clipboard."""
        try:
            selected_text = self.chat_display.get("sel.first", "sel.last")
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            self.status_bar["text"] = "Text copied to clipboard"
        except tk.TclError:
            # No selection
            self.status_bar["text"] = "No text selected"
    
    def show_about(self):
        """Show about dialog."""
        messagebox.showinfo(
            "About Enhanced LLM Chat",
            "Enhanced LLM Chat\n\n"
            "A modular chat interface for interacting with various LLMs.\n"
            "Supports RAG, conversation management, and multiple model providers."
        )
    
    def on_closing(self):
        """Handle application closing."""
        # Save settings before closing
        self.save_settings()
        
        # Ask to save conversation if there are unsaved messages
        if self.conversation_manager.active_conversation.messages:
            save = messagebox.askyesnocancel(
                "Save Conversation", 
                "Do you want to save the current conversation before exiting?"
            )
            
            if save is None:  # Cancel
                return
            elif save:  # Yes
                self.save_conversation()
        
        # Close application
        self.root.destroy()
    
    def stop_processing(self):
        """Stop any ongoing model generation or processing."""
        self.stop_event.set()
        if self.active_stream:
            try:
                # Attempt to close the stream if possible
                if hasattr(self.active_stream, 'close'):
                    self.active_stream.close()
            except Exception:
                pass
            self.active_stream = None
        
        self.is_processing = False
        self.status_bar["text"] = "Processing stopped"
        self.display_message("\nProcessing stopped by user.\n", "status")
    
    def reset_api_key(self):
        """Reset the Gemini API key."""
        self.reset_generic_api_key("gemini")
    
    def reset_deepseek_api_key(self):
        """Reset the DeepSeek API key"""
        self.reset_generic_api_key("deepseek")

    def reset_generic_api_key(self, provider):
        """Generic function to reset API key for a given provider"""
        if hasattr(self, 'model_manager') and hasattr(self.model_manager, 'api_config'):
            confirm = messagebox.askyesno(
                "Reset API Key",
                f"Are you sure you want to reset your {provider.capitalize()} API key? This cannot be undone."
            )
            if confirm:
                try:
                    self.model_manager.api_config.clear_api_key()
                    self.display_message(f"\n{provider.capitalize()} API key has been reset.\n", "status")
                    if provider == "gemini":
                        self.prompt_for_api_key()
                    elif provider == "deepseek":
                        self.prompt_for_deepseek_api_key()
                except Exception as e:
                    error_handler.handle_error(e, f"Resetting {provider} API key")

        else:
            self.display_message(f"\nAPI configuration not available for {provider}.\n", "error")
    
    @safe_execute("Loading models")
    def load_models(self):
        """Load and initialize the AI models."""
        self.model_manager = create_model_manager(self.developer.get())
        self.update_model_list()
        
        # Check if using Google and show API key dialog if needed
        if self.developer.get().lower() == "google" and not self.model_manager.api_config.is_configured():
            self.prompt_for_api_key()
        # Check if using Deepseek
        if self.developer.get().lower() == "deepseek" and not self.model_manager.api_config.is_configured():
            self.prompt_for_deepseek_api_key()

    def on_developer_changed(self, event):
        """Handle developer selection change."""
        developer = self.developer.get()
        self.model_manager = create_model_manager(developer)
        self.update_model_list()
        self.display_message(f"\nSwitched to {developer} models\n", "status")

        # Check if API key is needed for Google
        if developer.lower() == "google" and not self.model_manager.api_config.is_configured():
            self.prompt_for_api_key()
        
        # Check if API key is needed for Deepseek
        if developer.lower() == "deepseek" and not self.model_manager.api_config.is_configured():
            self.prompt_for_deepseek_api_key()

def main():
    """Main entry point for the application."""
    # Create TkinterDnD root window
    root = TkinterDnD.Tk()
    
    # Create the application instance
    app = OllamaChat(root)
    
    # Start the main event loop
    root.mainloop()


if __name__ == "__main__":
    main()
