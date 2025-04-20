import tkinter as tk
from tkinter import scrolledtext, filedialog, StringVar, Menu, messagebox
from tkinter import ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import threading
import time
from PIL import Image, ImageTk
from PIL import Image as PILImage
from io import BytesIO
import re
import markdown
from markitdown import MarkItDown
from typing import Optional, List, Dict, Any
import webbrowser

# Import custom HTML/Markdown renderer
from html_text import HTMLText, HTMLTextParser

# Import our custom modules
from settings import Settings
from conversation import ConversationManager, Message, Conversation
from prompt_manager import PromptManager, Prompt
from rag_module import RAG
from rag_visualizer import RAGVisualizerPanel
from models_manager import create_model_manager, OllamaManager, GeminiManager
from error_handler import error_handler, safe_execute

class OllamaChat:
    """Main application class for Ollama Chat."""

    # Define color scheme as class variables - improved for better aesthetics
    bg_color = "#1E1E2E"  # Darker, more pleasant background
    fg_color = "#F5F5F5"  # Brighter text for better contrast
    accent_color = "#89B4FA"  # Softer blue accent
    secondary_bg = "#313244"  # Medium contrast for secondary elements
    tertiary_bg = "#181825"  # Darker background for some elements
    subtle_accent = "#74C7EC"  # Lighter blue for highlights
    success_color = "#A6E3A1"  # Soft green for success messages
    error_color = "#F38BA8"  # Softer red for errors
    warning_color = "#FAB387"  # Peach for warnings
    border_color = "#45475A"  # Border color for elements

    def __init__(self, root):
        """Initialize the application and all its components."""
        self.root = root
        self.root.title("Local(o)llama Chat")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)

        # Set up a modern theme
        self.setup_theme()

    def setup_theme(self):
        """Set up a modern theme for the application."""
        # Configure ttk styles
        style = ttk.Style()

        # Try to use a modern theme if available
        try:
            style.theme_use("clam")  # More modern than default
        except tk.TclError:
            pass  # Use default theme if clam is not available

        # Configure ttk styles with improved aesthetics
        style.configure("TFrame", background=self.bg_color, borderwidth=1, relief="solid", bordercolor=self.border_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color, font=("Segoe UI", 10))

        # Create a frame style with no border
        style.configure("NoBorder.TFrame", background=self.bg_color, borderwidth=0, relief="flat")

        # Create a frame style with subtle border
        style.configure("SubtleBorder.TFrame", background=self.bg_color, borderwidth=1, relief="solid", bordercolor=self.border_color)

        # Button styling with rounded corners effect
        style.configure("TButton",
                      background=self.secondary_bg,
                      foreground=self.fg_color,
                      borderwidth=1,
                      relief="flat",
                      font=("Segoe UI", 10))
        style.map("TButton",
                 background=[("active", self.subtle_accent), ("pressed", self.accent_color)],
                 foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")],
                 relief=[("pressed", "sunken")])

        # Checkbox styling
        style.configure("TCheckbutton",
                      background=self.bg_color,
                      foreground=self.fg_color,
                      font=("Segoe UI", 10))
        style.map("TCheckbutton",
                 background=[("active", self.bg_color)],
                 foreground=[("active", self.accent_color)])

        # Radio button styling
        style.configure("TRadiobutton",
                      background=self.bg_color,
                      foreground=self.fg_color,
                      font=("Segoe UI", 10))
        style.map("TRadiobutton",
                 background=[("active", self.bg_color)],
                 foreground=[("active", self.accent_color)])

        # Dropdown styling
        style.configure("TCombobox",
                      fieldbackground=self.secondary_bg,
                      background=self.secondary_bg,
                      foreground=self.fg_color,
                      arrowcolor=self.accent_color,
                      font=("Segoe UI", 10))
        style.map("TCombobox",
                 fieldbackground=[("readonly", self.secondary_bg)],
                 background=[("readonly", self.secondary_bg)],
                 foreground=[("readonly", self.fg_color)],
                 selectbackground=[("readonly", self.subtle_accent)],
                 selectforeground=[("readonly", "#FFFFFF")])

        # Other widget styling
        style.configure("TPanedwindow", background=self.bg_color, sashrelief="flat")
        style.configure("TSizegrip", background=self.bg_color)

        # LabelFrame styling - improved with better borders and padding
        style.configure("TLabelframe",
                      background=self.bg_color,
                      foreground=self.fg_color,
                      borderwidth=1,
                      relief="solid",
                      bordercolor=self.border_color,
                      padding=5)
        style.configure("TLabelframe.Label",
                      background=self.bg_color,
                      foreground=self.accent_color,
                      font=("Segoe UI", 10, "bold"))

        # Configure root window
        self.root.configure(background=self.bg_color)

        # Set default font to a modern font
        self.root.option_add("*Font", ("Segoe UI", 10))


        # Initialize components
        self.settings = Settings()
        self.conversation_manager = ConversationManager()
        self.prompt_manager = PromptManager()

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
        self.display_message("Welcome to Loca(o)llama chat!\n", "status")
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
        self.current_file_path = None  # Store the current file path
        self.selected_model = None
        self.selected_embedding_model = None
        self.developer = StringVar(value=self.settings.get("developer"))
        self.temperature = tk.DoubleVar(value=self.settings.get("temperature"))
        self.context_size = tk.IntVar(value=self.settings.get("context_size"))
        self.chunk_size = tk.IntVar(value=self.settings.get("chunk_size"))
        self.include_chat_var = tk.BooleanVar(value=self.settings.get("include_chat"))
        self.show_image_var = tk.BooleanVar(value=self.settings.get("show_image"))
        self.include_file_var = tk.BooleanVar(value=self.settings.get("include_file"))
        self.web_access_var = tk.BooleanVar(value=self.settings.get("web_access", False))
        self.advanced_web_access_var = tk.BooleanVar(value=self.settings.get("advanced_web_access", False))

        # Processing control
        self.is_processing = False
        self.active_stream = None
        self.stop_event = threading.Event()
        self.rag_files = []
        self._web_search_failures = 0  # Counter for basic web search failures
        self._advanced_web_search_failures = 0  # Counter for advanced web search failures

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
        file_menu.add_command(label="Clear all RAG Files", command=self.clear_rag_files)
        file_menu.add_command(label="Clear individual RAG File", command=self.clear_rag_file)
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
        edit_menu.add_separator()
        edit_menu.add_command(label="Prompt History", command=self.show_prompt_history)

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
        api_menu.add_separator()
        api_menu.add_command(label="Configure Anthropic API Key", command=self.prompt_for_anthropic_api_key)
        api_menu.add_command(label="Reset Anthropic API Key", command=self.reset_anthropic_api_key)

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
                                         values=['ollama', 'google', 'deepseek', 'anthropic'], state='readonly')  # Added 'deepseek'
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

        # No semantic chunking options - removed for better performance

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

        # Generate image checkbox removed - functionality not working

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

        # Tools section
        tools_frame = ttk.LabelFrame(self.sidebar_frame, text="Tools")
        tools_frame.pack(fill=tk.X, padx=5, pady=5)

        # Web Search (Basic) checkbox
        self.web_access_var = tk.BooleanVar(value=self.settings.get("web_access", False))
        web_access_checkbox = ttk.Checkbutton(
            tools_frame,
            text="Web Search (Basic)",
            variable=self.web_access_var,
            command=self.on_web_access_toggle
        )
        web_access_checkbox.pack(anchor="w", padx=5, pady=2)

        # Web Search (Advanced) checkbox
        self.advanced_web_access_var = tk.BooleanVar(value=self.settings.get("advanced_web_access", False))
        advanced_web_access_checkbox = ttk.Checkbutton(
            tools_frame,
            text="Web Search (Advanced)",
            variable=self.advanced_web_access_var,
            command=self.on_advanced_web_access_toggle
        )
        advanced_web_access_checkbox.pack(anchor="w", padx=5, pady=2)

        # Conversations section
        conversations_frame = ttk.LabelFrame(self.sidebar_frame, text="Conversations")
        conversations_frame.pack(fill=tk.X, padx=5, pady=5)

        # Conversation buttons
        conv_buttons_frame = ttk.Frame(conversations_frame)
        conv_buttons_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(conv_buttons_frame, text="New", command=self.new_conversation).pack(side=tk.LEFT, padx=2)
        ttk.Button(conv_buttons_frame, text="Save", command=self.save_conversation).pack(side=tk.LEFT, padx=2)
        ttk.Button(conv_buttons_frame, text="Load", command=self.load_conversation).pack(side=tk.LEFT, padx=2)

        # Prompt History button
        ttk.Button(conv_buttons_frame, text="Prompt History", command=self.show_prompt_history).pack(side=tk.LEFT, padx=2)

        # Recent conversations list
        ttk.Label(conversations_frame, text="Recent:").pack(anchor="w", padx=5)
        self.conversations_listbox = tk.Listbox(conversations_frame, height=5)
        self.conversations_listbox.pack(fill=tk.X, padx=5, pady=2)
        self.conversations_listbox.bind("<Double-1>", self.on_conversation_selected)

        # Update the conversations list
        self.update_conversations_list()

    def create_chat_display(self):
        """Create the chat display area."""
        # Create a frame for the chat and input areas with padding
        self.chat_input_frame = ttk.Frame(self.main_frame, padding=(10, 10, 10, 10))
        self.main_frame.add(self.chat_input_frame)

        # Chat area - now directly in main_frame, below sidebar
        chat_frame = ttk.Frame(self.chat_input_frame)
        chat_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5) # Pack below sidebar

        # System instructions area with improved styling
        system_frame = ttk.LabelFrame(chat_frame, text="System Instructions", padding=(10, 10, 10, 10))
        system_frame.pack(fill=tk.X, padx=10, pady=10)

        self.system_text = scrolledtext.ScrolledText(
            system_frame,
            height=2,
            wrap=tk.WORD,
            font=("Segoe UI", 11),  # Slightly larger font
            bg=self.secondary_bg,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            padx=15,  # Increased horizontal padding
            pady=15,  # Increased vertical padding
            borderwidth=1,  # Subtle border
            highlightthickness=1,
            highlightcolor=self.subtle_accent,
            highlightbackground=self.border_color,
            relief="solid"  # Solid border for better definition
        )
        self.system_text.pack(fill=tk.X, padx=5, pady=5)
        self.system_text.insert('1.0', self.settings.get("system_prompt", "Respond honestly, objectively and concisely."))

        # Main chat display - using custom HTMLText widget with enhanced styling
        self.chat_display = HTMLText(
            chat_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 12),
            bg=self.tertiary_bg,  # Darker background for better contrast
            fg=self.fg_color,
            insertbackground=self.fg_color,
            padx=20,  # Increased padding for better readability
            pady=20,  # Increased padding for better readability
            borderwidth=1,  # Subtle border
            highlightthickness=1,
            highlightcolor=self.subtle_accent,
            highlightbackground=self.border_color,
            cursor="arrow",  # Use arrow cursor for better UX
            relief="solid"  # Solid border for better definition
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Make chat display read-only but allow selection
        self.chat_display.config(state=tk.DISABLED)
        # Removed dedicated image preview label

    # New helper: display the uploaded image in the chat area
    def display_uploaded_image(self):
        """Display the uploaded image inline in the chat display.
        If image preview is disabled, display the file path instead."""
        if self.file_type != 'image' or not self.file_img:
            return
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "\n")
        if self.show_image_var.get():
            try:
                from PIL import Image, ImageTk
                # Open image with reduced size to save memory
                pil_img = Image.open(self.file_img)
                # Calculate aspect ratio
                width, height = pil_img.size
                max_size = 300
                scale = min(max_size/width, max_size/height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                # Use LANCZOS resampling for better quality with less memory
                pil_img = pil_img.resize((new_width, new_height), Image.LANCZOS)
                # Convert to RGB if it's RGBA to reduce memory usage
                if pil_img.mode == 'RGBA':
                    pil_img = pil_img.convert('RGB')
                self.preview_image = ImageTk.PhotoImage(pil_img)
                self.chat_display.image_create(tk.END, image=self.preview_image)
                self.chat_display.insert(tk.END, "\n")
            except Exception as e:
                self.display_message(f"\nError displaying image: {e}\n", 'error')
        else:
            self.chat_display.insert(tk.END, f"Image file: {self.file_img}\n", 'assistant')
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def create_input_area(self):
        """Create the input area for user messages."""
        # Input area - now directly in main_frame, below chat display
        input_frame = ttk.Frame(self.chat_input_frame)
        input_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5) # Pack below chat display

        # Input field with scrollbar - make it resizable
        input_pane = ttk.PanedWindow(input_frame, orient=tk.VERTICAL)
        input_pane.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Create a frame for the input field
        input_field_frame = ttk.Frame(input_pane)
        input_pane.add(input_field_frame, weight=1)

        # Add the input field to the frame with enhanced styling
        self.input_field = scrolledtext.ScrolledText(
            input_field_frame,
            wrap=tk.WORD,
            height=4,
            font=("Segoe UI", 12),
            padx=20,  # Increased padding for better readability
            pady=20,  # Increased padding for better readability
            bg=self.secondary_bg,
            fg=self.fg_color,
            insertbackground=self.accent_color,  # Colored cursor for better visibility
            borderwidth=1,  # Subtle border
            highlightthickness=1,
            highlightcolor=self.subtle_accent,
            highlightbackground=self.border_color,
            insertwidth=2,  # Wider cursor for better visibility
            relief="solid"  # Solid border for better definition
        )

        # Add placeholder text that disappears on focus
        self.input_field.insert("1.0", "Type your message here...")
        self.input_field.bind("<FocusIn>", self.on_input_focus_in)
        self.input_field.bind("<FocusOut>", self.on_input_focus_out)
        self.input_placeholder_visible = True
        self.input_field.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Add a grip for resizing
        grip = ttk.Sizegrip(input_field_frame)
        grip.place(relx=1.0, rely=1.0, anchor="se")

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
        # Configure message tags with softer colors
        self.chat_display.tag_configure('user', foreground='#9CDCFE')  # Soft blue for user
        self.chat_display.tag_configure('assistant', foreground='#6A9955')  # Soft green for assistant
        self.chat_display.tag_configure('system', foreground='#CE9178')  # Soft orange for system
        self.chat_display.tag_configure('error', foreground=self.error_color)  # Red for errors
        self.chat_display.tag_configure('warning', foreground='#FFCC00')  # Yellow for warnings
        self.chat_display.tag_configure('status', foreground='#999999')  # Gray for status

        # Configure additional tags for rich text formatting
        self.chat_display.tag_configure('user_label', foreground='#9CDCFE', font=("Segoe UI", 12, "bold"))
        self.chat_display.tag_configure('assistant_label', foreground='#6A9955', font=("Segoe UI", 12, "bold"))
        self.chat_display.tag_configure('warning_label', foreground='#FFCC00', font=("Segoe UI", 12, "bold"))
        self.chat_display.tag_configure('system_label', foreground='#CE9178', font=("Segoe UI", 12, "bold"))
        self.chat_display.tag_configure('error_label', foreground=self.error_color, font=("Segoe UI", 12, "bold"))
        self.chat_display.tag_configure('status_label', foreground='#999999', font=("Segoe UI", 12, "bold"))

        # Configure file preview tags
        self.chat_display.tag_configure('file_label', foreground='#DCDCAA', font=("Segoe UI", 12, "bold"))  # Gold for file name
        self.chat_display.tag_configure('file_info', foreground='#4EC9B0', font=("Segoe UI", 11))  # Teal for file info

        # Configure link tag for clickable links
        self.chat_display.tag_configure('link', foreground=self.subtle_accent, underline=1)
        self.chat_display.tag_bind('link', '<Button-1>', lambda e: self.open_url_from_text())

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
        """Initialize the RAG system with lazy loading."""
        # Store RAG parameters but don't initialize yet
        self._rag_params = {
            "embedding_model_name": self.settings.get("embedding_model", ""),
            "chunk_size": self.settings.get("chunk_size", 128)
        }

        # Set rag to None - will be initialized on first use
        self.rag = None

        # Create RAG visualizer (lightweight)
        self.rag_visualizer = RAGVisualizerPanel(self.root)

    def _ensure_rag_initialized(self):
        """Ensure RAG is initialized when needed."""
        if self.rag is None:
            self.display_message("\nInitializing RAG system...\n", "status")
            self.rag = RAG(**self._rag_params)
            self.display_message("\nRAG system initialized.\n", "status")

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
        # Check if using Anthropic
        if self.developer.get().lower() == "anthropic" and not self.model_manager.api_config.is_configured():
            self.prompt_for_anthropic_api_key()

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

    def prompt_for_anthropic_api_key(self):
        """Prompt the user to enter their Anthropic API key if not configured."""
        from tkinter import simpledialog

        api_key = simpledialog.askstring(
            "Anthropic API Key",
            "Enter your Anthropic API key (will be saved securely):",
            show='*'  # Show asterisks for security
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

    def update_rag_chunk_size(self, *args):
        """Update RAG chunk size when the setting changes."""
        if hasattr(self, 'rag'):
            try:
                value = self.chunk_size.get()
                self.rag.chunk_size = value
            except (tk.TclError, ValueError):
                # Handle empty or invalid input
                self.chunk_size.set(128)  # Reset to default
                self.rag.chunk_size = 128

    # Semantic chunking methods removed for better performance

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

        elif developer.lower() == "anthropic" and not self.model_manager.api_config.is_configured():
            self.prompt_for_anthropic_api_key()

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
        """Update inline image display based on the checkbox."""
        if self.file_type == 'image' and self.file_img:
            self.display_uploaded_image()

    def on_web_access_toggle(self):
        """Handle basic web access toggle."""
        web_access = self.web_access_var.get()
        self.settings.set("web_access", web_access)

        # If enabling basic web search, disable advanced web search
        if web_access and self.advanced_web_access_var.get():
            self.advanced_web_access_var.set(False)
            self.settings.set("advanced_web_access", False)

        if web_access:
            self.display_message("\nBasic web search enabled. The chatbot can now search the web for information.\n", "status")
        else:
            self.display_message("\nBasic web search disabled.\n", "status")

    def on_advanced_web_access_toggle(self):
        """Handle advanced web access toggle."""
        advanced_web_access = self.advanced_web_access_var.get()
        self.settings.set("advanced_web_access", advanced_web_access)

        # If enabling advanced web search, disable basic web search
        if advanced_web_access and self.web_access_var.get():
            self.web_access_var.set(False)
            self.settings.set("web_access", False)

        if advanced_web_access:
            # Check if crawl4ai is installed
            try:
                import crawl4ai
                self.display_message("\nAdvanced web search enabled. The chatbot can now crawl websites for detailed information.\n", "status")

                # Check if Playwright needs to be installed
                self.display_message("\nChecking Playwright installation...\n", 'status')
                try:
                    import subprocess
                    import sys

                    # Get the Python executable path
                    python_exe = sys.executable

                    # Run playwright install command with the full Python path
                    self.display_message("\nInstalling Playwright browsers (this may take a few minutes)...\n", 'status')
                    subprocess.check_call([python_exe, "-m", "playwright", "install", "--with-deps"])
                    self.display_message("\nPlaywright browsers installed successfully.\n", "status")
                except Exception as e:
                    error_msg = error_handler.handle_error(e, "Installing Playwright browsers")
                    self.display_message(f"\nWarning: Playwright browsers installation failed: {error_msg}\n", 'warning')
                    self.display_message("\nTo use advanced web search, please run the following command in your terminal:\n\n", 'warning')
                    self.display_message("python -m playwright install --with-deps\n\n", 'warning')
                    # Continue anyway as the main package is installed

            except ImportError:
                self.display_message("\nInstalling crawl4ai for advanced web search...\n", 'status')
                try:
                    import subprocess
                    subprocess.check_call(["pip", "install", "crawl4ai"])
                    self.display_message("\nAdvanced web search enabled. The chatbot can now crawl websites for detailed information.\n", "status")

                    # Also install Playwright browsers
                    self.display_message("\nInstalling Playwright browsers (this may take a few minutes)...\n", 'status')
                    try:
                        import sys
                        python_exe = sys.executable
                        subprocess.check_call([python_exe, "-m", "playwright", "install", "--with-deps"])
                        self.display_message("\nPlaywright browsers installed successfully.\n", "status")
                    except Exception as e:
                        error_msg = error_handler.handle_error(e, "Installing Playwright browsers")
                        self.display_message(f"\nWarning: Playwright browsers installation failed: {error_msg}\n", 'warning')
                        self.display_message("\nTo use advanced web search, please run the following command in your terminal:\n\n", 'warning')
                        self.display_message("python -m playwright install --with-deps\n\n", 'warning')
                        # Continue anyway as the main package is installed

                except Exception as e:
                    error_msg = error_handler.handle_error(e, "Installing crawl4ai")
                    self.display_message(f"\nError installing crawl4ai: {error_msg}\n", 'error')
                    self.advanced_web_access_var.set(False)
                    self.settings.set("advanced_web_access", False)
        else:
            self.display_message("\nAdvanced web search disabled.\n", "status")

    def perform_web_search(self, query):
        """Perform a web search using requests and BeautifulSoup as a fallback.

        Args:
            query: The search query

        Returns:
            str: Formatted search results or None if search failed
        """
        # First try using a direct web search approach
        try:
            import requests
            from bs4 import BeautifulSoup
            import urllib.parse

            # Format the search query for URL
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://www.google.com/search?q={encoded_query}"

            # Set a user agent to avoid being blocked
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            # Make the request
            response = requests.get(search_url, headers=headers)
            response.raise_for_status()  # Raise an exception for HTTP errors

            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract search results
            search_results = []
            for result in soup.select('div.g')[:5]:  # Limit to 5 results
                title_element = result.select_one('h3')
                link_element = result.select_one('a')
                snippet_element = result.select_one('div.VwiC3b')

                if title_element and link_element and snippet_element:
                    title = title_element.get_text()
                    url = link_element.get('href')
                    if url.startswith('/url?q='):
                        url = url.split('/url?q=')[1].split('&')[0]
                    snippet = snippet_element.get_text()

                    search_results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet
                    })

            # Format results
            if not search_results:
                self.display_message("\nNo search results found. Try a different query.\n", 'status')
                return None

            formatted_results = ""
            for i, result in enumerate(search_results, 1):
                title = result.get('title', 'No title')
                url = result.get('url', 'No URL')
                snippet = result.get('snippet', 'No snippet available')

                formatted_results += f"Result {i}:\n"
                formatted_results += f"Title: {title}\n"
                formatted_results += f"URL: {url}\n"
                formatted_results += f"Snippet: {snippet}\n\n"

            return formatted_results

        except ImportError:
            # If BeautifulSoup is not available, try to install it
            self.display_message("\nInstalling required packages for web search...\n", 'status')
            try:
                import subprocess
                subprocess.check_call(["pip", "install", "requests beautifulsoup4"])
                # Try again after installation
                return self.perform_web_search(query)
            except Exception as e:
                error_msg = error_handler.handle_error(e, "Installing web search dependencies")
                self.display_message(f"\nError installing dependencies: {error_msg}\n", 'error')
                self.display_message("\nWeb search is currently unavailable. Please install 'requests' and 'beautifulsoup4' packages manually.\n", 'error')
                # Disable web access to prevent loops
                self.web_access_var.set(False)
                self.settings.set("web_access", False)
                return None

        except Exception as e:
            error_msg = error_handler.handle_error(e, "Web search")
            self.display_message(f"\nError during web search: {error_msg}\n", 'error')
            return None

    def handle_drop(self, event):
        """Handle file drop event."""
        file_path = event.data.strip('{}')
        self.file_type = self.get_file_type(file_path)
        self.current_file_path = file_path  # Store the file path for reference

        # Enable the include file checkbox
        self.include_file_checkbox.state(['!disabled'])
        self.include_file_var.set(True)

        # Handle based on file type
        if self.file_type == 'image':
            self.file_img = file_path
            self.file_content = None
            # Display the image inline
            self.display_uploaded_image()
        elif self.file_type == 'audio':
            self.file_img = None
            # Extract audio content with transcription
            self.file_content = self.extract_content(file_path)
            self.preserved_file_content = self.file_content
            if self.file_content:
                self.word_count = len(re.findall(r'\w+', self.file_content))
                # Display audio preview in chat
                self.display_audio_preview(file_path, self.file_content)
        elif self.file_type == 'youtube' or self.file_type == 'url':
            self.file_img = None
            # Extract content from URL
            self.file_content = self.extract_content(file_path)
            self.preserved_file_content = self.file_content
            if self.file_content:
                self.word_count = len(re.findall(r'\w+', self.file_content))
                # Display YouTube preview in chat
                if self.file_type == 'youtube':
                    self.display_youtube_preview(file_path, self.file_content)
                else:
                    self.display_file_preview(file_path, self.file_content)
        elif self.file_type == 'zip':
            self.file_img = None
            # Extract content from ZIP
            self.file_content = self.extract_content(file_path)
            self.preserved_file_content = self.file_content
            if self.file_content:
                self.word_count = len(re.findall(r'\w+', self.file_content))
                # Display ZIP preview in chat
                self.display_file_preview(file_path, self.file_content)
        else:  # document or unknown
            self.file_img = None
            self.file_content = self.extract_content(file_path)
            # Add this line to preserve file content
            self.preserved_file_content = self.file_content
            if self.file_content:
                self.word_count = len(re.findall(r'\w+', self.file_content))
                # Display file preview in chat
                self.display_file_preview(file_path, self.file_content)

        self.update_status()

    def get_file_type(self, file_path):
        """Determine the file type from its extension or URL pattern."""
        # Check if it's a URL
        if file_path.startswith(('http://', 'https://')):
            if any(pattern in file_path.lower() for pattern in ['youtube.com/watch', 'youtu.be/']):
                return 'youtube'
            return 'url'

        # Check file extension
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            return 'image'
        elif ext in ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac']:
            return 'audio'
        elif ext == '.zip':
            return 'zip'
        elif ext in ['.pdf', '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls', '.txt', '.md', '.json', '.csv', '.html', '.epub']:
            return 'document'
        return 'unknown'

    def extract_content(self, file_path):
        """Extract text content from a file or URL."""
        try:
            file_type = self.get_file_type(file_path)
            md = MarkItDown()

            # Install optional dependencies if needed
            if file_type == 'audio' and not self._check_audio_dependencies():
                self.display_message("\nInstalling audio transcription dependencies...\n", 'status')
                self._install_dependencies(['markitdown[audio-transcription]'])

            if file_type == 'youtube' and not self._check_youtube_dependencies():
                self.display_message("\nInstalling YouTube transcription dependencies...\n", 'status')
                self._install_dependencies(['markitdown[youtube-transcription]'])

            # Process based on file type
            if file_type in ['document', 'audio', 'youtube', 'url', 'zip']:
                # Show status message for potentially longer operations
                if file_type == 'audio':
                    self.display_message("\nTranscribing audio file...\n", 'status')
                elif file_type == 'youtube':
                    self.display_message("\nFetching YouTube content...\n", 'status')
                elif file_type == 'zip':
                    self.display_message("\nProcessing ZIP archive...\n", 'status')

                # Convert the file
                result = md.convert(file_path)

                # For ZIP files, add a header
                if file_type == 'zip':
                    zip_summary = f"# ZIP Archive: {os.path.basename(file_path)}\n\n"
                    zip_summary += result.text_content
                    return zip_summary

                return result.text_content
            return None
        except Exception as e:
            error_msg = error_handler.handle_error(e, "Extracting file content")
            self.display_message(f"\nError extracting content: {error_msg}\n", 'error')
            return None

    def _check_audio_dependencies(self):
        """Check if audio transcription dependencies are installed."""
        try:
            import whisper
            return True
        except ImportError:
            return False

    def _check_youtube_dependencies(self):
        """Check if YouTube transcription dependencies are installed."""
        try:
            import youtube_transcript_api
            return True
        except ImportError:
            return False

    def _install_dependencies(self, packages):
        """Install required dependencies."""
        try:
            import subprocess
            for package in packages:
                subprocess.check_call(["pip", "install", package])
            return True
        except Exception as e:
            error_msg = error_handler.handle_error(e, "Installing dependencies")
            self.display_message(f"\nError installing dependencies: {error_msg}\n", 'error')
            return False

    def display_audio_preview(self, file_path, file_content):
        """Display an audio file preview in the chat with an icon and transcription."""
        if not file_path or not file_content:
            return

        # Get file name
        file_name = os.path.basename(file_path)

        # Display the audio preview in the chat
        self.chat_display["state"] = "normal"

        # Add a separator
        self.chat_display.insert(tk.END, "\n", 'status')

        # Add audio icon and name
        icon = "🔊"  # Audio file icon
        self.chat_display.insert(tk.END, f"{icon} Audio: {file_name}\n", 'file_label')

        # Add transcription preview
        self.chat_display.insert(tk.END, "Transcription:\n", 'file_info')

        # Show first few lines of transcription
        lines = file_content.split('\n')
        preview_lines = lines[:5]
        preview_text = '\n'.join(preview_lines)

        # Add ellipsis if there are more lines
        if len(lines) > 5:
            preview_text += '\n...'

        self.chat_display.insert(tk.END, preview_text, 'code')
        self.chat_display.insert(tk.END, "\n", 'status')

        # Add word count
        word_count = len(re.findall(r'\w+', file_content))
        self.chat_display.insert(tk.END, f"Word count: {word_count}\n", 'file_info')

        # Add duration if available
        if "Duration:" in file_content:
            duration_match = re.search(r"Duration: ([0-9:.]+)", file_content)
            if duration_match:
                duration = duration_match.group(1)
                self.chat_display.insert(tk.END, f"Duration: {duration}\n", 'file_info')

        # Add a separator
        self.chat_display.insert(tk.END, "\n", 'status')

        self.chat_display["state"] = "disabled"
        self.chat_display.see(tk.END)

    def display_youtube_preview(self, url, content):
        """Display a YouTube video preview in the chat with thumbnail and transcription."""
        if not url or not content:
            return

        # Extract video ID from URL
        video_id = None
        if "youtube.com/watch?v=" in url:
            video_id = url.split("youtube.com/watch?v=")[1].split("&")[0]
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1].split("?")[0]

        self.chat_display["state"] = "normal"

        # Add a separator
        self.chat_display.insert(tk.END, "\n", 'status')

        # Add YouTube icon and title
        icon = "▶️"  # YouTube icon

        # Extract title if available
        title = url
        title_match = re.search(r"Title: (.+)", content)
        if title_match:
            title = title_match.group(1)

        self.chat_display.insert(tk.END, f"{icon} YouTube: {title}\n", 'file_label')

        # Add URL as clickable link
        self.chat_display.insert(tk.END, "URL: ", 'file_info')
        link_start = self.chat_display.index(tk.END)
        self.chat_display.insert(tk.END, url)
        link_end = self.chat_display.index(tk.END)
        self.chat_display.tag_add('link', link_start, link_end)
        self.chat_display.insert(tk.END, "\n", 'status')

        # Add transcription preview
        self.chat_display.insert(tk.END, "Transcription:\n", 'file_info')

        # Show first few lines of transcription
        lines = content.split('\n')
        # Skip metadata lines
        content_lines = [line for line in lines if not line.startswith("Title:") and not line.startswith("Duration:")]
        preview_lines = content_lines[:5]
        preview_text = '\n'.join(preview_lines)

        # Add ellipsis if there are more lines
        if len(content_lines) > 5:
            preview_text += '\n...'

        self.chat_display.insert(tk.END, preview_text, 'code')
        self.chat_display.insert(tk.END, "\n", 'status')

        # Add word count
        word_count = len(re.findall(r'\w+', content))
        self.chat_display.insert(tk.END, f"Word count: {word_count}\n", 'file_info')

        # Add duration if available
        if "Duration:" in content:
            duration_match = re.search(r"Duration: ([0-9:.]+)", content)
            if duration_match:
                duration = duration_match.group(1)
                self.chat_display.insert(tk.END, f"Duration: {duration}\n", 'file_info')

        # Add a separator
        self.chat_display.insert(tk.END, "\n", 'status')

        self.chat_display["state"] = "disabled"
        self.chat_display.see(tk.END)

    def handle_url_input(self, url):
        """Handle URL input, particularly YouTube URLs.

        Args:
            url: The URL to process

        Returns:
            bool: True if URL was handled successfully, False otherwise
        """
        # Determine URL type
        if "youtube.com" in url or "youtu.be" in url:
            self.file_type = "youtube"
        else:
            self.file_type = "url"

        try:
            # Show loading indicator
            self.status_bar["text"] = f"Fetching content from {self.file_type}..."

            # Store the URL as the current file path
            self.current_file_path = url

            # Use MarkItDown to extract content
            self.file_content = self.extract_content(url)
            self.preserved_file_content = self.file_content

            if self.file_content:
                self.word_count = len(re.findall(r'\w+', self.file_content))

                # Display appropriate preview in chat
                if self.file_type == "youtube":
                    self.display_youtube_preview(url, self.file_content)
                else:
                    self.display_file_preview(url, self.file_content)

                # Enable the include file checkbox
                self.include_file_checkbox.state(['!disabled'])
                self.include_file_var.set(True)

                self.update_status()
                return True
            else:
                self.display_message(f"\nCould not extract content from {url}\n", 'error')
                return False

        except Exception as e:
            error_msg = error_handler.handle_error(e, f"Fetching content from {url}")
            self.display_message(f"\nError: {error_msg}\n", 'error')
            return False

    def update_status(self):
        """Update status bar with current file information."""
        if self.file_img and self.file_type == 'image':
            self.status_bar["text"] = f"Image loaded: {os.path.basename(self.file_img)}"
        elif self.file_type == 'audio':
            self.status_bar["text"] = f"Audio loaded: {os.path.basename(self.current_file_path)} - {self.word_count} words"
        elif self.file_type == 'youtube':
            self.status_bar["text"] = f"YouTube content loaded: {self.word_count} words"
        elif self.file_type == 'url':
            self.status_bar["text"] = f"URL content loaded: {self.word_count} words"
        elif self.file_type == 'zip':
            self.status_bar["text"] = f"ZIP archive loaded: {os.path.basename(self.current_file_path)} - {self.word_count} words"
        elif self.file_content:
            self.status_bar["text"] = f"Document loaded: {self.word_count} words"
        else:
            self.status_bar["text"] = "Ready"

    def on_input_focus_in(self, event):
        """Handle input field focus in - clear placeholder text."""
        if hasattr(self, 'input_placeholder_visible') and self.input_placeholder_visible:
            self.input_field.delete("1.0", tk.END)
            self.input_placeholder_visible = False

    def on_input_focus_out(self, event):
        """Handle input field focus out - restore placeholder if empty."""
        if not self.input_field.get("1.0", tk.END).strip():
            self.input_field.delete("1.0", tk.END)
            self.input_field.insert("1.0", "Type your message here...")
            self.input_placeholder_visible = True

    @safe_execute("Sending message")
    def send_message(self):
        """Process and send the user's message."""
        user_input = self.input_field.get("1.0", tk.END).strip()
        if not user_input or user_input == "Type your message here...":
            return

        # Check if input is a URL
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
        urls = re.findall(url_pattern, user_input)

        if urls and len(urls) == 1 and urls[0] == user_input.strip():
            # If the entire input is just a URL, try to handle it
            if self.handle_url_input(user_input):
                # Clear input field if URL was handled
                self.input_field.delete("1.0", tk.END)
                return

        # Debug statement to check file content
        print(f"File content exists: {self.file_content is not None}")
        print(f"Preserved file content exists: {hasattr(self, 'preserved_file_content') and self.preserved_file_content is not None}")
        print(f"Include file checkbox: {self.include_file_var.get()}")

        # Add to conversation manager
        self.conversation_manager.add_message_to_active("user", user_input)

        # Display user message
        self.display_message("\n", 'user')
        self.display_message(f"{user_input}\n", 'user')

        self.input_field.delete("1.0", tk.END)

        # Prepare message content
        content = user_input

        # Add web search results if web access is enabled
        if self.web_access_var.get():
            self.display_message("\nSearching the web for information (basic)...\n", 'status')
            try:
                # Perform basic web search with a timeout to prevent hanging
                search_results = self.perform_web_search(user_input)
                if search_results:
                    content += f"\n\nWeb search results:\n{search_results}"
                    self.display_message("\nBasic web search completed.\n", 'status')
                else:
                    # If search failed but didn't raise an exception, show a message
                    self.display_message("\nNo relevant web results found.\n", 'status')
                    # Disable web access if it's causing problems
                    if hasattr(self, '_web_search_failures'):
                        self._web_search_failures += 1
                        if self._web_search_failures >= 3:
                            self.display_message("\nBasic web search is being disabled due to repeated failures.\n", 'error')
                            self.web_access_var.set(False)
                            self.settings.set("web_access", False)
                            self._web_search_failures = 0
                    else:
                        self._web_search_failures = 1
            except Exception as e:
                error_msg = error_handler.handle_error(e, "Basic web search")
                self.display_message(f"\nError during basic web search: {error_msg}\n", 'error')
                # Disable web access if it's causing errors
                self.web_access_var.set(False)
                self.settings.set("web_access", False)

        # Add advanced web search results if enabled
        elif self.advanced_web_access_var.get():
            self.display_message("\nSearching the web for information (advanced)...\n", 'status')
            try:
                # Perform advanced web search using crawl4ai
                search_results = self.perform_advanced_web_search(user_input)
                if search_results:
                    content += f"\n\nAdvanced web search results:\n{search_results}"
                    self.display_message("\nAdvanced web search completed.\n", 'status')
                else:
                    # If search failed but didn't raise an exception, show a message
                    self.display_message("\nNo relevant advanced web results found.\n", 'status')
                    # Disable advanced web access if it's causing problems
                    if hasattr(self, '_advanced_web_search_failures'):
                        self._advanced_web_search_failures += 1
                        if self._advanced_web_search_failures >= 3:
                            self.display_message("\nAdvanced web search is being disabled due to repeated failures.\n", 'error')
                            self.advanced_web_access_var.set(False)
                            self.settings.set("advanced_web_access", False)
                            self._advanced_web_search_failures = 0
                    else:
                        self._advanced_web_search_failures = 1
            except Exception as e:
                error_msg = error_handler.handle_error(e, "Advanced web search")
                self.display_message(f"\nError during advanced web search: {error_msg}\n", 'error')
                # Disable advanced web access if it's causing errors
                self.advanced_web_access_var.set(False)
                self.settings.set("advanced_web_access", False)

        # Include file content based on the checkbox - MODIFIED
        if self.include_file_var.get():
            content_to_use = self.file_content or getattr(self, 'preserved_file_content', None)
            if content_to_use:
                content += f"\n\nDocument content:\n{content_to_use}"

        # Rest of the method remains unchanged...
        # Include chat history if selected
        if self.include_chat_var.get():
            chat_history = self.get_chat_history()
            content += f"\n\nChat history:\n{chat_history}"

        # Include RAG context if available
        rag_results = []
        if self.rag_files:
            # Ensure RAG is initialized if files are available
            self._ensure_rag_initialized()

            # Start timing RAG processing
            rag_start_time = time.time()

            # Get RAG context
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
                        "embedding_model": self.selected_embedding_model,
                        "cache_stats": self.rag.get_cache_stats() if hasattr(self.rag, 'get_cache_stats') else {}
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

        # Image generation functionality removed
        # Send message in separate thread
        threading.Thread(target=self.get_response, args=(message, rag_results)).start()

    # Image generation functionality removed - not working

    def get_chat_history(self):
        """Get formatted chat history for context."""
        history = []
        for msg in self.conversation_manager.active_conversation.messages:
            if msg.role in ['user', 'assistant']:
                history.append(f"{msg.role.capitalize()}: {msg.content}")
        return "\n\n".join(history)

    def get_rag_chunks(self, query):
        """Get RAG chunks with metadata for visualization."""
        if not self.rag_files:
            return []

        # Ensure RAG is initialized
        self._ensure_rag_initialized()

        try:
            # Get chunks and their scores from the RAG module
            results = self.rag.collection.query(
                query_texts=[query],
                n_results=5,
                include=['documents', 'distances', 'metadatas']
            )

            chunks = []
            if results and 'documents' in results and len(results['documents']) > 0:
                # Get collection info once for efficiency
                collection_info = self.rag.collection.get()
                total_chunks = len(collection_info.get('documents', [])) if collection_info else 0

                # Process all chunks in a single loop for better performance
                documents = results['documents'][0]
                distances = results['distances'][0]
                metadatas = results['metadatas'][0] if 'metadatas' in results and results['metadatas'] else []

                for i in range(len(documents)):
                    # Convert distance to similarity score (1 - normalized_distance)
                    similarity = 1.0 - min(1.0, distances[i] / 2.0)  # Simple normalization

                    # Extract source file if available in metadata
                    source = "Unknown"
                    if metadatas and i < len(metadatas):
                        metadata = metadatas[i]
                        if metadata and 'source' in metadata:
                            source = metadata['source']

                    chunks.append({
                        'text': documents[i],
                        'score': similarity,
                        'source': source,
                        'total_chunks': total_chunks
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

                    # Update RAG visualizer with source data if available
                    if self.rag_visualizer and rag_results:
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
        """Display a message in the chat window with optional tags and markdown rendering."""
        self.chat_display["state"] = "normal"

        # Add role label if it's a new message
        if message.startswith('\n') and tag in ['user', 'assistant', 'system', 'error', 'status', 'warning']:
            label_tag = f"{tag}_label"
            if tag == 'user':
                self.chat_display.insert(tk.END, "\n🧑 You: ", label_tag)
            elif tag == 'assistant':
                self.chat_display.insert(tk.END, "\n🤖 Assistant: ", label_tag)
            elif tag == 'system':
                self.chat_display.insert(tk.END, "\n⚙️ System: ", label_tag)
            elif tag == 'error':
                self.chat_display.insert(tk.END, "\n⚠️ Error: ", 'error_label')
            elif tag == 'warning':
                self.chat_display.insert(tk.END, "\n⚡ Warning: ", 'warning_label')
            elif tag == 'status':
                self.chat_display.insert(tk.END, "\n💬 Status: ", 'status_label')

            # Remove the leading newline from the message
            message = message[1:]

        # Process the message based on the tag
        if tag == 'assistant':
            # Use markdown rendering for assistant messages
            try:
                # Save the current position to insert markdown content
                current_pos = self.chat_display.index(tk.END)

                # Process potential code blocks and render markdown
                # We don't call clear() on chat_display because we want to append, not replace
                html = markdown.markdown(
                    message,
                    extensions=['extra', 'codehilite', 'nl2br', 'sane_lists']
                )

                # Create a parser and feed the HTML
                parser = HTMLTextParser(self.chat_display)
                parser.feed(html)

            except Exception as e:
                print(f"Error rendering markdown: {e}")
                # Fallback to original method if markdown rendering fails
                parts = message.split('```')
                for i, part in enumerate(parts):
                    if i % 2 == 0:  # Regular text
                        self.chat_display.insert(tk.END, part, 'assistant')
                    else:  # Code block
                        self.chat_display.insert(tk.END, '\n', 'assistant')  # Newline before code
                        self.chat_display.insert(tk.END, part.strip(), 'code')  # Code with code tag
                        self.chat_display.insert(tk.END, '\n', 'assistant')  # Newline after code
        else:
            # For other message types, just insert with the tag
            self.chat_display.insert(tk.END, message, tag)

        self.chat_display["state"] = "disabled"
        self.chat_display.see(tk.END)

    def open_url_from_text(self):
        """Open URL from clicked text."""
        try:
            # Get the text with the 'link' tag at the current mouse position
            index = self.chat_display.index("@%d,%d" % (self.root.winfo_pointerx(), self.root.winfo_pointery()))
            url = self.chat_display.get(index + " linestart", index + " lineend")

            # Extract URL using regex
            url_match = re.search(r'https?://[^\s]+', url)
            if url_match:
                webbrowser.open(url_match.group(0))
        except Exception as e:
            self.display_message(f"\nError opening URL: {e}\n", 'error')

    def perform_advanced_web_search(self, query):
        """Perform an advanced web search using crawl4ai.

        Args:
            query: The search query

        Returns:
            str: Extracted content in markdown format or None if search failed
        """
        try:
            import asyncio
            import crawl4ai
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

            self.display_message("\nPerforming advanced web search with crawl4ai...\n", 'status')

            # Define an async function to run the crawler
            async def run_crawler():
                # Configure the browser
                browser_config = BrowserConfig(
                    headless=True,  # Run in headless mode
                    verbose=False    # Don't show verbose logs
                )

                # Configure the crawler
                run_config = CrawlerRunConfig(
                    cache_mode="ENABLED"  # Enable caching for better performance
                )

                # Create search URL from query
                search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"

                # Initialize the crawler
                async with AsyncWebCrawler(config=browser_config) as crawler:
                    # First, get search results
                    search_result = await crawler.arun(
                        url=search_url,
                        config=run_config
                    )

                    # Extract top result URLs from the search results
                    import re
                    urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s"\'\\\/]*', search_result.markdown.fit_markdown)

                    # Filter out Google URLs and duplicates
                    filtered_urls = []
                    for url in urls:
                        if not any(domain in url for domain in ['google.com', 'gstatic.com', 'youtube.com/watch']) and url not in filtered_urls:
                            filtered_urls.append(url)

                    # Limit to top 3 results
                    top_urls = filtered_urls[:3]

                    if not top_urls:
                        return f"Search results for '{query}' did not yield any useful links."

                    # Crawl each top result
                    results = []
                    for i, url in enumerate(top_urls, 1):
                        try:
                            # Crawl the URL
                            result = await crawler.arun(
                                url=url,
                                config=run_config
                            )

                            # Extract a summary (first 1000 characters)
                            content = result.markdown.fit_markdown
                            summary = content[:1000] + "..." if len(content) > 1000 else content

                            # Add to results
                            results.append(f"Source {i}: {url}\n\n{summary}\n\n")
                        except Exception as e:
                            results.append(f"Source {i}: {url}\n\nError crawling this URL: {str(e)}\n\n")

                    # Combine results
                    return f"Advanced search results for '{query}':\n\n" + "\n".join(results)

            # Run the async crawler
            return asyncio.run(run_crawler())

        except ImportError:
            # If crawl4ai is not available, try to install it
            self.display_message("\nInstalling crawl4ai for advanced web search...\n", 'status')
            try:
                import subprocess
                subprocess.check_call(["pip", "install", "crawl4ai"])
                # Try again after installation
                return self.perform_advanced_web_search(query)
            except Exception as e:
                error_msg = error_handler.handle_error(e, "Installing crawl4ai")
                self.display_message(f"\nError installing crawl4ai: {error_msg}\n", 'error')
                # Disable advanced web access
                self.advanced_web_access_var.set(False)
                self.settings.set("advanced_web_access", False)
                return None

        except Exception as e:
            error_msg = error_handler.handle_error(e, "Advanced web search")

            # Check if the error is related to missing Playwright browsers
            if "Executable doesn't exist" in str(e) and "chrome-win" in str(e):
                self.display_message("\nPlaywright browsers are not installed properly.\n", 'error')
                self.display_message("\nTo use advanced web search, please run the following command in your terminal:\n\n", 'warning')
                self.display_message("python -m playwright install --with-deps\n\n", 'warning')

                # Try to install Playwright browsers automatically
                try:
                    import sys
                    import subprocess
                    python_exe = sys.executable
                    self.display_message("\nAttempting to install Playwright browsers automatically...\n", 'status')
                    subprocess.check_call([python_exe, "-m", "playwright", "install", "--with-deps"])
                    self.display_message("\nPlaywright browsers installed successfully. Please try your search again.\n", 'status')
                    return None
                except Exception as install_error:
                    install_error_msg = error_handler.handle_error(install_error, "Installing Playwright browsers")
                    self.display_message(f"\nAutomatic installation failed: {install_error_msg}\n", 'error')
                    # Disable advanced web access to prevent further errors
                    self.advanced_web_access_var.set(False)
                    self.settings.set("advanced_web_access", False)
                    return None
            else:
                self.display_message(f"\nError during advanced web search: {error_msg}\n", 'error')
                return None

    def save_settings(self):
        """Save current settings to the settings file."""
        settings_data = {
            "developer": self.developer.get(),
            "llm_model": self.selected_model,
            "embedding_model": self.selected_embedding_model,
            "temperature": self.temperature.get(),
            "context_size": self.context_size.get(),
            "chunk_size": self.chunk_size.get(),
            "include_chat": self.include_chat_var.get(),
            "show_image": self.show_image_var.get(),
            "include_file": self.include_file_var.get(),
            "web_access": self.web_access_var.get(),
            "advanced_web_access": self.advanced_web_access_var.get(),
            "system_prompt": self.system_text.get('1.0', tk.END).strip()
            # generate_image_var removed - functionality not working
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

            # If using Google, add image generation models
            if self.developer.get().lower() == "google" and hasattr(self.model_manager, 'api_config'):
                image_gen_models = self.model_manager.api_config.get_image_generation_models()
                # Make sure we don't add duplicates
                for model in image_gen_models:
                    if model not in llm_models:
                        llm_models.append(model)

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

        # Ensure RAG is initialized
        self._ensure_rag_initialized()

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
        if self.rag is not None:
            self.rag.clear_db()

        self.rag_files = []
        self.rag_indicator.config(text="RAG: Not Active", foreground="grey")
        self.display_message("\nRAG database cleared.\n", "status")

        # Reset RAG to None to free memory
        self.rag = None

    def clear_rag_file(self):
        """Clear a specific file from RAG."""
        filepath = filedialog.askopenfilename(title="Select RAG File to Clear")
        if filepath:
            if filepath in self.rag_files:
                try:
                    # Ensure RAG is initialized
                    self._ensure_rag_initialized()

                    # Clear the file content
                    with open(filepath, 'w') as f:
                        f.write("")  # Clear the file

                    # Remove the file from the RAG database
                    self.rag.clear_db()
                    self.rag_files.remove(filepath)

                    # Re-ingest the remaining files if any
                    if self.rag_files:
                        self._process_rag_files()
                        self.rag_indicator.config(text=f"RAG: Active ({len(self.rag_files)} files)", foreground="green")
                    else:
                        # No files left, reset RAG to free memory
                        self.rag = None
                        self.rag_indicator.config(text="RAG: Not Active", foreground="grey")

                    self.display_message(f"\nCleared RAG file: {os.path.basename(filepath)}\n", "status")
                except Exception as e:
                    error_handler.handle_error(e, "Clearing RAG file")
                    self.display_message(f"\nError clearing RAG file: {e}\n", "error")
            else:
                self.display_message("\nFile is not in the RAG file list.\n", "error")

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

    def display_file_preview(self, file_path, file_content):
        """Display a file preview in the chat with an icon and the first 5 lines."""
        if not file_path or not file_content:
            return

        # Get file name and extension
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_name)[1].lower()

        # Create a preview of the first 5 lines
        lines = file_content.split('\n')
        preview_lines = lines[:5]
        preview_text = '\n'.join(preview_lines)

        # Add ellipsis if there are more lines
        if len(lines) > 5:
            preview_text += '\n...'  # Add ellipsis to indicate more content

        # Display the file preview in the chat
        self.chat_display["state"] = "normal"

        # Add a separator
        self.chat_display.insert(tk.END, "\n", 'status')

        # Add file icon and name
        icon = "📄"  # Default file icon
        if file_ext in ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c']:
            icon = "📜"  # Code file
        elif file_ext in ['.txt', '.md', '.rst', '.tex']:
            icon = "📝"  # Text file
        elif file_ext in ['.pdf', '.doc', '.docx', '.odt']:
            icon = "📑"  # Document file
        elif file_ext in ['.csv', '.xlsx', '.xls']:
            icon = "📊"  # Data file

        # Create a file info frame with icon and name
        self.chat_display.insert(tk.END, f"{icon} File: {file_name}\n", 'file_label')

        # Add file preview with code formatting
        self.chat_display.insert(tk.END, "Preview:\n", 'file_info')
        self.chat_display.insert(tk.END, preview_text, 'code')
        self.chat_display.insert(tk.END, "\n", 'status')

        # Add word count
        word_count = len(re.findall(r'\w+', file_content))
        self.chat_display.insert(tk.END, f"Word count: {word_count}\n", 'file_info')

        # Add a separator
        self.chat_display.insert(tk.END, "\n", 'status')

        self.chat_display["state"] = "disabled"
        self.chat_display.see(tk.END)

    def clear_file(self):
        """Clear the current file."""
        print("clear_file method called")
        self.file_img = None
        self.file_content = None
        # Keep preserved copy even when clearing
        # self.preserved_file_content = None  # Don't clear this
        self.file_type = None
        self.word_count = 0
        self.current_file_path = None  # Clear the file path
        self.update_status()

        # No need to clear a separate image preview label now
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
            "About Local(o)llama Chat",
            "Python-based LLM Chat\n\n"
            "A modular chat interface for interacting with various LLMs.\n"
            "Supports RAG, conversation management, and multiple model providers."
        )

    def show_prompt_history(self):
        """Show the prompt history window."""
        # Create a new top-level window
        prompt_window = tk.Toplevel(self.root)
        prompt_window.title("Prompt History")
        prompt_window.geometry("600x500")
        prompt_window.minsize(500, 400)
        prompt_window.configure(background=self.bg_color)

        # Make it modal
        prompt_window.transient(self.root)
        prompt_window.grab_set()

        # Create main frame
        main_frame = ttk.Frame(prompt_window, padding=(10, 10, 10, 10))
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 10))

        # Add buttons
        ttk.Button(buttons_frame, text="Add Prompt", command=lambda: self.add_prompt(prompt_window, prompt_listbox)).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Delete Prompt", command=lambda: self.delete_prompt(prompt_listbox)).pack(side=tk.LEFT, padx=5)

        # Create prompt list frame
        list_frame = ttk.LabelFrame(main_frame, text="Saved Prompts")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Add listbox for prompts
        prompt_listbox = tk.Listbox(list_frame, font=("Segoe UI", 11), bg=self.secondary_bg, fg=self.fg_color)
        prompt_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Bind double-click to view prompt
        prompt_listbox.bind("<Double-1>", lambda e: self.view_prompt(prompt_window, prompt_listbox))

        # Populate the listbox with prompt titles
        self.update_prompt_listbox(prompt_listbox)

        # Add close button at the bottom
        ttk.Button(main_frame, text="Close", command=prompt_window.destroy).pack(pady=10)

    def update_prompt_listbox(self, listbox):
        """Update the prompt listbox with current prompts."""
        listbox.delete(0, tk.END)
        for title in self.prompt_manager.get_prompt_titles():
            listbox.insert(tk.END, title)

    def add_prompt(self, parent_window, listbox):
        """Add a new prompt."""
        # Create a new top-level window for adding a prompt
        add_window = tk.Toplevel(parent_window)
        add_window.title("Add New Prompt")
        add_window.geometry("600x400")
        add_window.minsize(500, 300)
        add_window.configure(background=self.bg_color)

        # Make it modal
        add_window.transient(parent_window)
        add_window.grab_set()

        # Create main frame
        main_frame = ttk.Frame(add_window, padding=(10, 10, 10, 10))
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title field
        ttk.Label(main_frame, text="Title:").pack(anchor="w", pady=(0, 5))
        title_entry = ttk.Entry(main_frame, width=50, font=("Segoe UI", 11))
        title_entry.pack(fill=tk.X, pady=(0, 10))

        # Content field
        ttk.Label(main_frame, text="Content:").pack(anchor="w", pady=(0, 5))
        content_text = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            height=10,
            font=("Segoe UI", 11),
            bg=self.secondary_bg,
            fg=self.fg_color
        )
        content_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=10)

        # Save and Cancel buttons
        ttk.Button(
            buttons_frame,
            text="Save",
            command=lambda: self.save_prompt(title_entry.get(), content_text.get("1.0", tk.END), add_window, listbox)
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            buttons_frame,
            text="Cancel",
            command=add_window.destroy
        ).pack(side=tk.RIGHT, padx=5)

    def save_prompt(self, title, content, window, listbox):
        """Save a prompt to the prompt manager."""
        if not title.strip():
            messagebox.showerror("Error", "Title cannot be empty")
            return

        if not content.strip():
            messagebox.showerror("Error", "Content cannot be empty")
            return

        # Add the prompt
        success = self.prompt_manager.add_prompt(title, content)

        if success:
            # Update the listbox
            self.update_prompt_listbox(listbox)
            # Close the window
            window.destroy()
            # Show success message
            messagebox.showinfo("Success", f"Prompt '{title}' saved successfully")
        else:
            messagebox.showerror("Error", "Failed to save prompt")

    def delete_prompt(self, listbox):
        """Delete a selected prompt."""
        # Get selected index
        selected = listbox.curselection()

        if not selected:
            messagebox.showinfo("Info", "Please select a prompt to delete")
            return

        # Get the title
        title = listbox.get(selected[0])

        # Confirm deletion
        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete the prompt '{title}'?"
        )

        if confirm:
            # Delete the prompt
            success = self.prompt_manager.delete_prompt(title)

            if success:
                # Update the listbox
                self.update_prompt_listbox(listbox)
                # Show success message
                messagebox.showinfo("Success", f"Prompt '{title}' deleted successfully")
            else:
                messagebox.showerror("Error", "Failed to delete prompt")

    def view_prompt(self, parent_window, listbox):
        """View and edit a selected prompt."""
        # Get selected index
        selected = listbox.curselection()

        if not selected:
            messagebox.showinfo("Info", "Please select a prompt to view")
            return

        # Get the title
        title = listbox.get(selected[0])

        # Get the prompt
        prompt = self.prompt_manager.get_prompt(title)

        if not prompt:
            messagebox.showerror("Error", f"Could not find prompt '{title}'")
            return

        # Create a new top-level window for viewing/editing the prompt
        view_window = tk.Toplevel(parent_window)
        view_window.title(f"Prompt: {title}")
        view_window.geometry("600x400")
        view_window.minsize(500, 300)
        view_window.configure(background=self.bg_color)

        # Make it modal
        view_window.transient(parent_window)
        view_window.grab_set()

        # Create main frame
        main_frame = ttk.Frame(view_window, padding=(10, 10, 10, 10))
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Content field
        content_text = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            height=15,
            font=("Segoe UI", 11),
            bg=self.secondary_bg,
            fg=self.fg_color
        )
        content_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Insert the prompt content
        content_text.insert("1.0", prompt.content)

        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=10)

        # Use in Chat button
        ttk.Button(
            buttons_frame,
            text="Use in Chat",
            command=lambda: self.use_prompt_in_chat(prompt.content, view_window)
        ).pack(side=tk.LEFT, padx=5)

        # Save and Close buttons
        ttk.Button(
            buttons_frame,
            text="Save Changes",
            command=lambda: self.update_prompt(title, content_text.get("1.0", tk.END), view_window, listbox)
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            buttons_frame,
            text="Close",
            command=view_window.destroy
        ).pack(side=tk.RIGHT, padx=5)

    def update_prompt(self, title, content, window, listbox):
        """Update an existing prompt."""
        if not content.strip():
            messagebox.showerror("Error", "Content cannot be empty")
            return

        # Update the prompt
        success = self.prompt_manager.update_prompt(title, content)

        if success:
            # Show success message
            messagebox.showinfo("Success", f"Prompt '{title}' updated successfully")
            # Close the window
            window.destroy()
        else:
            messagebox.showerror("Error", "Failed to update prompt")

    def use_prompt_in_chat(self, content, window):
        """Use the selected prompt in the chat input field."""
        # Clear the input field
        self.input_field.delete("1.0", tk.END)

        # Insert the prompt content
        self.input_field.insert("1.0", content)

        # Close the window
        window.destroy()

        # Focus on the input field
        self.input_field.focus_set()

        # Set placeholder visible to False
        self.input_placeholder_visible = False

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

    def reset_anthropic_api_key(self):
        """Reset the Anthropic API key"""
        self.reset_generic_api_key("anthropic")

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
                    elif provider == "anthropic":
                        self.prompt_for_anthropic_api_key()
                except Exception as e:
                    error_handler.handle_error(e, f"Resetting {provider} API key")

        else:
            self.display_message(f"\nAPI configuration not available for {provider}.\n", "error")

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
