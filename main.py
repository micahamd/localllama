import tkinter as tk
from tkinter import scrolledtext, filedialog, StringVar, Menu, messagebox
from tkinter import ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import threading
import time
import json
from PIL import Image, ImageTk
from PIL import Image as PILImage
from io import BytesIO
import re
import markdown
from markitdown import MarkItDown
from typing import Optional, List, Dict, Any
import webbrowser
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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

# Import MCP modules
from mcp_server import MCPManager
from mcp_ui import MCPPanel

class OllamaChat:
    """Main application class for Ollama Chat."""

    # Define color scheme as class variables - enhanced for better aesthetics
    bg_color = "#1A1B26"  # Rich dark blue-black background
    fg_color = "#C0CAF5"  # Soft blue-white text for better readability
    accent_color = "#7AA2F7"  # Vibrant blue accent
    secondary_bg = "#24283B"  # Slightly lighter background for contrast
    tertiary_bg = "#16161E"  # Darker background for depth
    subtle_accent = "#BB9AF7"  # Purple accent for highlights and interactive elements
    success_color = "#9ECE6A"  # Vibrant green for success messages
    error_color = "#F7768E"  # Bright red for errors
    warning_color = "#E0AF68"  # Rich amber for warnings
    border_color = "#414868"  # Subtle border color
    highlight_color = "#2AC3DE"  # Cyan highlight for selections and focus
    cursor_color = "#61AFEF"  # Light blue cursor for better visibility
    muted_text = "#565F89"  # Muted text for less important elements

    def __init__(self, root):
        """Initialize the application and all its components."""
        self.root = root
        self.root.title("Local(o)llama Chat")
        self.root.geometry("1200x800")
        self.root.minsize(800, 400)

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

        # Configure ttk styles with enhanced aesthetics
        style.configure("TFrame",
                      background=self.bg_color,
                      borderwidth=1,
                      relief="solid",
                      bordercolor=self.border_color)

        style.configure("TLabel",
                      background=self.bg_color,
                      foreground=self.fg_color,
                      font=("Segoe UI", 10))

        # Create a frame style with no border
        style.configure("NoBorder.TFrame",
                      background=self.bg_color,
                      borderwidth=0,
                      relief="flat")

        # Create a frame style with subtle border and rounded corners
        style.configure("SubtleBorder.TFrame",
                      background=self.bg_color,
                      borderwidth=1,
                      relief="solid",
                      bordercolor=self.border_color)

        # Create a rounded frame style
        style.configure("Rounded.TFrame",
                      background=self.bg_color,
                      borderwidth=1,
                      relief="solid",
                      bordercolor=self.border_color)

        # Button styling with enhanced rounded corners effect
        style.configure("TButton",
                      background=self.secondary_bg,
                      foreground=self.fg_color,
                      borderwidth=1,
                      relief="flat",
                      padding=(10, 5),  # More padding for better touch targets
                      font=("Segoe UI", 10, "bold"))  # Bold text for better visibility
        style.map("TButton",
                 background=[("active", self.subtle_accent), ("pressed", self.accent_color)],
                 foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")],
                 relief=[("pressed", "sunken")])

        # Create a primary button style with accent color
        style.configure("Primary.TButton",
                      background=self.accent_color,
                      foreground="#FFFFFF",
                      borderwidth=1,
                      relief="flat",
                      padding=(10, 5),
                      font=("Segoe UI", 10, "bold"))
        style.map("Primary.TButton",
                 background=[("active", self.subtle_accent), ("pressed", self.highlight_color)],
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

        # Slider styling with accent colors
        style.configure("Horizontal.TScale",
                      background=self.bg_color,
                      troughcolor=self.secondary_bg,
                      sliderrelief="flat")
        style.map("Horizontal.TScale",
                 background=[("active", self.bg_color)],
                 troughcolor=[("active", self.secondary_bg)])

        # LabelFrame styling - enhanced with better borders, padding and rounded appearance
        style.configure("TLabelframe",
                      background=self.bg_color,
                      foreground=self.fg_color,
                      borderwidth=1,
                      relief="solid",
                      bordercolor=self.border_color,
                      padding=10)  # Increased padding for better spacing
        style.configure("TLabelframe.Label",
                      background=self.bg_color,
                      foreground=self.accent_color,
                      font=("Segoe UI", 11, "bold"))  # Slightly larger font for better readability

        # Configure root window
        self.root.configure(background=self.bg_color)

        # Set default font to a modern font
        self.root.option_add("*Font", ("Segoe UI", 10))


        # Initialize components
        self.settings = Settings()
        self.conversation_manager = ConversationManager()
        self.prompt_manager = PromptManager()

        # Initialize MCP manager
        self.mcp_manager = MCPManager()
        self.mcp_panel = None

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
        self.setup_mcp()
        self.load_models()
        self.bind_events()

        # Apply saved settings
        self.apply_settings()

        # No custom slider thumbs to initialize

        # Show welcome message
        self.display_message("Welcome to Loca(o)llama chat!\n", "status")
        self.display_message("Drop files here or type a message to begin.\n", "status")

    def create_main_frame(self):
        """Create the main application frame."""
        # Set minimum window size for better usability
        self.root.minsize(800, 600)

        # Set initial window size to 80% of screen if not maximized
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        initial_width = int(screen_width * 0.8)
        initial_height = int(screen_height * 0.8)

        # Center the window
        x = (screen_width - initial_width) // 2
        y = (screen_height - initial_height) // 2
        self.root.geometry(f"{initial_width}x{initial_height}+{x}+{y}")

        # Bind keyboard shortcut for sidebar toggle
        self.root.bind('<Control-b>', lambda e: self.toggle_sidebar())

        self.main_frame = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)  # Use PanedWindow
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Configure PanedWindow for better responsiveness
        self.root.after(100, self.configure_paned_window)

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
        self.top_k = tk.IntVar(value=self.settings.get("top_k", 40))
        self.top_p = tk.DoubleVar(value=self.settings.get("top_p", 0.9))
        self.repeat_penalty = tk.DoubleVar(value=self.settings.get("repeat_penalty", 1.1))
        self.max_tokens = tk.IntVar(value=self.settings.get("max_tokens", 2048))
        self.include_chat_var = tk.BooleanVar(value=self.settings.get("include_chat"))
        self.show_image_var = tk.BooleanVar(value=self.settings.get("show_image"))
        self.include_file_var = tk.BooleanVar(value=self.settings.get("include_file"))
        self.advanced_web_access_var = tk.BooleanVar(value=self.settings.get("advanced_web_access", False))
        self.write_file_var = tk.BooleanVar(value=self.settings.get("write_file", False))
        self.read_file_var = tk.BooleanVar(value=self.settings.get("read_file", False))
        self.intelligent_processing_var = tk.BooleanVar(value=self.settings.get("intelligent_processing", True))
        self.truncate_file_display_var = tk.BooleanVar(value=self.settings.get("truncate_file_display", True))

        # Processing control
        self.is_processing = False
        self.active_stream = None
        self.stop_event = threading.Event()
        self.rag_files = []
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
        file_menu.add_command(label="Rename Conversation", command=self.rename_conversation)
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

        # Tools menu
        tools_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Memory Control Program", command=self.show_mcp_panel)

        # Help menu
        help_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)

    def create_sidebar(self):
        """Create the sidebar with settings and model selection."""
        self.sidebar_frame = ttk.Frame(self.main_frame)  # Sidebar is now part of main_frame

        # Add to PanedWindow with responsive sizing
        self.main_frame.add(self.sidebar_frame, weight=0)  # Sidebar doesn't expand

        # Set initial sidebar width based on screen size
        screen_width = self.root.winfo_screenwidth()
        if screen_width < 1200:
            sidebar_width = 250  # Smaller width for smaller screens
        else:
            sidebar_width = 300  # Standard width for larger screens

        # Sidebar header with collapse button
        header_frame = ttk.Frame(self.sidebar_frame)
        header_frame.pack(fill=tk.X, pady=(5, 10))

        # Sidebar title - smaller font for compact layout
        sidebar_title = ttk.Label(header_frame, text="Settings", font=("Arial", 12, "bold"))
        sidebar_title.pack(side=tk.LEFT)

        # Collapse/expand button
        self.sidebar_collapsed = False
        self.collapse_button = ttk.Button(header_frame, text="◀", width=3, command=self.toggle_sidebar)
        self.collapse_button.pack(side=tk.RIGHT)

        # Create a canvas and scrollbar for scrollable content
        self.sidebar_canvas = tk.Canvas(
            self.sidebar_frame,
            bg=self.bg_color,
            highlightthickness=0,
            width=sidebar_width  # Responsive width
        )
        self.sidebar_scrollbar = ttk.Scrollbar(
            self.sidebar_frame,
            orient="vertical",
            command=self.sidebar_canvas.yview
        )
        self.sidebar_canvas.configure(yscrollcommand=self.sidebar_scrollbar.set)

        # Create a frame inside the canvas for all the content
        self.scrollable_sidebar = ttk.Frame(self.sidebar_canvas)
        self.sidebar_canvas_window = self.sidebar_canvas.create_window(
            (0, 0),
            window=self.scrollable_sidebar,
            anchor="nw"
        )

        # Pack the canvas and scrollbar
        self.sidebar_canvas.pack(side="left", fill="both", expand=True)
        self.sidebar_scrollbar.pack(side="right", fill="y")

        # Bind events for scrolling
        self.sidebar_canvas.bind('<Configure>', self._on_sidebar_canvas_configure)
        self.scrollable_sidebar.bind('<Configure>', self._on_sidebar_frame_configure)

        # Bind mousewheel to canvas for scrolling
        self.sidebar_canvas.bind("<MouseWheel>", self._on_sidebar_mousewheel)
        self.sidebar_canvas.bind("<Button-4>", self._on_sidebar_mousewheel)
        self.sidebar_canvas.bind("<Button-5>", self._on_sidebar_mousewheel)

        # Bind focus events to enable scrolling when sidebar is focused
        self.sidebar_canvas.bind("<Enter>", lambda e: self.sidebar_canvas.focus_set())
        self.sidebar_canvas.bind("<Leave>", lambda e: self.root.focus_set())

        # Models settings frame - now using scrollable_sidebar
        model_frame = ttk.LabelFrame(self.scrollable_sidebar, text="Models")
        model_frame.pack(fill=tk.X, padx=3, pady=3)

        # Developer selector - more compact
        ttk.Label(model_frame, text="Developer:", font=("Arial", 9)).pack(anchor="w", padx=3, pady=1)
        developer_selector = ttk.Combobox(model_frame, textvariable=self.developer,
                                         values=['ollama', 'google', 'deepseek', 'anthropic'], state='readonly',
                                         font=("Arial", 9))  # Added 'deepseek'
        developer_selector.pack(fill=tk.X, padx=3, pady=1)
        developer_selector.bind('<<ComboboxSelected>>', self.on_developer_changed)

        # LLM Model selector - more compact
        ttk.Label(model_frame, text="LLM Model:", font=("Arial", 9)).pack(anchor="w", padx=3, pady=1)
        self.model_selector = ttk.Combobox(model_frame, state='readonly', font=("Arial", 9))
        self.model_selector.pack(fill=tk.X, padx=3, pady=1)
        self.model_selector.bind('<<ComboboxSelected>>', self.on_model_selected)

        # Embedding Model selector - more compact
        ttk.Label(model_frame, text="Embedding:", font=("Arial", 9)).pack(anchor="w", padx=3, pady=1)
        self.embedding_selector = ttk.Combobox(model_frame, state='readonly', font=("Arial", 9))
        self.embedding_selector.pack(fill=tk.X, padx=3, pady=1)
        self.embedding_selector.bind('<<ComboboxSelected>>', self.on_embedding_model_selected)

        # Parameters settings frame - more compact
        params_frame = ttk.LabelFrame(self.scrollable_sidebar, text="Parameters")
        params_frame.pack(fill=tk.X, padx=3, pady=3)

        # Temperature control - more compact
        ttk.Label(params_frame, text="Temperature:", font=("Arial", 9)).pack(anchor="w", padx=3, pady=1)
        temp_frame = ttk.Frame(params_frame)
        temp_frame.pack(fill=tk.X, padx=3, pady=1)

        self.temp_slider = ttk.Scale(
            temp_frame,
            from_=0.0,
            to=2.0,
            orient='horizontal',
            variable=self.temperature,
            command=self.on_temp_change,
            style="Horizontal.TScale"
        )

        # No custom thumb - using the default ttk.Scale thumb
        self.temp_slider.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.temp_label = ttk.Label(temp_frame, text=f"{self.temperature.get():.2f}", font=("Arial", 8))
        self.temp_label.pack(side=tk.RIGHT, padx=3)

        # Context size control - more compact
        ttk.Label(params_frame, text="Context Size:", font=("Arial", 9)).pack(anchor="w", padx=3, pady=1)
        context_frame = ttk.Frame(params_frame)
        context_frame.pack(fill=tk.X, padx=3, pady=1)

        self.context_slider = ttk.Scale(
            context_frame,
            from_=1000,
            to=128000,
            orient='horizontal',
            variable=self.context_size,
            command=self.on_context_change,
            style="Horizontal.TScale"
        )

        # No custom thumb - using the default ttk.Scale thumb
        self.context_slider.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.context_label = ttk.Label(context_frame, text=str(self.context_size.get()))
        self.context_label.pack(side=tk.RIGHT, padx=5)

        # Top-k control
        ttk.Label(params_frame, text="Top-k (diversity):").pack(anchor="w", padx=5, pady=2)
        top_k_frame = ttk.Frame(params_frame)
        top_k_frame.pack(fill=tk.X, padx=5, pady=2)

        self.top_k_slider = ttk.Scale(
            top_k_frame,
            from_=1,
            to=100,
            orient='horizontal',
            variable=self.top_k,
            command=self.on_top_k_change,
            style="Horizontal.TScale"
        )
        self.top_k_slider.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.top_k_label = ttk.Label(top_k_frame, text=str(self.top_k.get()))
        self.top_k_label.pack(side=tk.RIGHT, padx=5)

        # Top-p control
        ttk.Label(params_frame, text="Top-p (nucleus):").pack(anchor="w", padx=5, pady=2)
        top_p_frame = ttk.Frame(params_frame)
        top_p_frame.pack(fill=tk.X, padx=5, pady=2)

        self.top_p_slider = ttk.Scale(
            top_p_frame,
            from_=0.1,
            to=1.0,
            orient='horizontal',
            variable=self.top_p,
            command=self.on_top_p_change,
            style="Horizontal.TScale"
        )
        self.top_p_slider.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.top_p_label = ttk.Label(top_p_frame, text=f"{self.top_p.get():.2f}")
        self.top_p_label.pack(side=tk.RIGHT, padx=5)

        # Repeat penalty control
        ttk.Label(params_frame, text="Repeat Penalty:").pack(anchor="w", padx=5, pady=2)
        repeat_penalty_frame = ttk.Frame(params_frame)
        repeat_penalty_frame.pack(fill=tk.X, padx=5, pady=2)

        self.repeat_penalty_slider = ttk.Scale(
            repeat_penalty_frame,
            from_=0.8,
            to=1.5,
            orient='horizontal',
            variable=self.repeat_penalty,
            command=self.on_repeat_penalty_change,
            style="Horizontal.TScale"
        )
        self.repeat_penalty_slider.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.repeat_penalty_label = ttk.Label(repeat_penalty_frame, text=f"{self.repeat_penalty.get():.2f}")
        self.repeat_penalty_label.pack(side=tk.RIGHT, padx=5)

        # Max tokens control
        ttk.Label(params_frame, text="Max Tokens:").pack(anchor="w", padx=5, pady=2)
        max_tokens_frame = ttk.Frame(params_frame)
        max_tokens_frame.pack(fill=tk.X, padx=5, pady=2)

        self.max_tokens_slider = ttk.Scale(
            max_tokens_frame,
            from_=256,
            to=8192,
            orient='horizontal',
            variable=self.max_tokens,
            command=self.on_max_tokens_change,
            style="Horizontal.TScale"
        )
        self.max_tokens_slider.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.max_tokens_label = ttk.Label(max_tokens_frame, text=str(self.max_tokens.get()))
        self.max_tokens_label.pack(side=tk.RIGHT, padx=5)

        # RAG settings frame - more compact
        rag_frame = ttk.LabelFrame(self.scrollable_sidebar, text="RAG Settings")
        rag_frame.pack(fill=tk.X, padx=3, pady=3)

        # Chunk size - more compact
        ttk.Label(rag_frame, text="Chunk Size:", font=("Arial", 9)).pack(anchor="w", padx=3, pady=1)
        self.chunk_entry = ttk.Entry(rag_frame, textvariable=self.chunk_size, width=5, font=("Arial", 9))
        self.chunk_entry.pack(anchor="w", padx=3, pady=1)

        # No semantic chunking options - removed for better performance

        # Options frame - more compact
        options_frame = ttk.LabelFrame(self.scrollable_sidebar, text="Options")
        options_frame.pack(fill=tk.X, padx=3, pady=3)

        # Include chat history
        include_chat_checkbox = ttk.Checkbutton(
            options_frame,
            text="Include chat history",
            variable=self.include_chat_var
        )
        include_chat_checkbox.pack(anchor="w", padx=3, pady=1)

        # Generate image checkbox removed - functionality not working

        # Show image preview - more compact
        show_image_checkbox = ttk.Checkbutton(
            options_frame,
            text="Show image preview",
            variable=self.show_image_var,
            command=self.on_show_image_toggle
        )
        show_image_checkbox.pack(anchor="w", padx=3, pady=1)

        # Include file content - more compact
        self.include_file_checkbox = ttk.Checkbutton(
            options_frame,
            text="Include file content",
            variable=self.include_file_var
        )
        self.include_file_checkbox.pack(anchor="w", padx=3, pady=1)

        # Intelligent file processing
        intelligent_processing_checkbox = ttk.Checkbutton(
            options_frame,
            text="Intelligent File Processing?",
            variable=self.intelligent_processing_var,
            command=self.on_intelligent_processing_toggle
        )
        intelligent_processing_checkbox.pack(anchor="w", padx=5, pady=2)

        # Tools section - more compact
        tools_frame = ttk.LabelFrame(self.scrollable_sidebar, text="Tools")
        tools_frame.pack(fill=tk.X, padx=3, pady=3)

        # Web Search checkbox
        self.advanced_web_access_var = tk.BooleanVar(value=self.settings.get("advanced_web_access", False))
        advanced_web_access_checkbox = ttk.Checkbutton(
            tools_frame,
            text="Web Search",
            variable=self.advanced_web_access_var,
            command=self.on_advanced_web_access_toggle
        )
        advanced_web_access_checkbox.pack(anchor="w", padx=3, pady=1)

        # Write File checkbox - more compact
        write_file_checkbox = ttk.Checkbutton(
            tools_frame,
            text="Write File",
            variable=self.write_file_var,
            command=self.on_write_file_toggle
        )
        write_file_checkbox.pack(anchor="w", padx=3, pady=1)

        # Read File checkbox - more compact
        read_file_checkbox = ttk.Checkbutton(
            tools_frame,
            text="Read File",
            variable=self.read_file_var,
            command=self.on_read_file_toggle
        )
        read_file_checkbox.pack(anchor="w", padx=3, pady=1)

        # Truncate File Display checkbox - more compact
        truncate_file_display_checkbox = ttk.Checkbutton(
            tools_frame,
            text="Truncate file display in chat",
            variable=self.truncate_file_display_var,
            command=self.on_truncate_file_display_toggle
        )
        truncate_file_display_checkbox.pack(anchor="w", padx=3, pady=1)

        # Conversations section with enhanced styling - more compact
        conversations_frame = ttk.LabelFrame(self.scrollable_sidebar, text="Conversations")
        conversations_frame.pack(fill=tk.X, padx=3, pady=3)

        # Conversation buttons - more compact
        conv_buttons_frame = ttk.Frame(conversations_frame)
        conv_buttons_frame.pack(fill=tk.X, padx=3, pady=3)

        ttk.Button(conv_buttons_frame, text="New", command=self.new_conversation).pack(side=tk.LEFT, padx=2)
        ttk.Button(conv_buttons_frame, text="Save", command=self.save_conversation).pack(side=tk.LEFT, padx=2)
        ttk.Button(conv_buttons_frame, text="Load", command=self.load_conversation).pack(side=tk.LEFT, padx=2)

        # Prompt History button
        ttk.Button(conv_buttons_frame, text="Prompt History", command=self.show_prompt_history).pack(side=tk.LEFT, padx=2)

        # Recent conversations list with enhanced styling
        ttk.Label(conversations_frame, text="Recent:").pack(anchor="w", padx=5)
        self.conversations_listbox = tk.Listbox(
            conversations_frame,
            height=5,
            bg=self.secondary_bg,
            fg=self.fg_color,
            selectbackground=self.subtle_accent,
            selectforeground="#FFFFFF",
            borderwidth=0,
            highlightthickness=2,
            highlightcolor=self.highlight_color,
            highlightbackground=self.border_color,
            font=("Segoe UI", 10)
        )
        self.conversations_listbox.pack(fill=tk.X, padx=5, pady=2)
        self.conversations_listbox.bind("<Double-1>", self.on_conversation_selected)

        # Update the conversations list
        self.update_conversations_list()

    def _on_sidebar_canvas_configure(self, event):
        """Handle canvas configuration changes for sidebar scrolling."""
        # Update the scroll region to encompass the inner frame
        self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all"))

        # Update the canvas window width to match the canvas width
        canvas_width = event.width
        self.sidebar_canvas.itemconfig(self.sidebar_canvas_window, width=canvas_width)

    def _on_sidebar_frame_configure(self, event):
        """Handle frame configuration changes for sidebar scrolling."""
        # Update the scroll region when the frame size changes
        self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all"))

    def _on_sidebar_mousewheel(self, event):
        """Handle mouse wheel scrolling in the sidebar."""
        # Determine scroll direction and amount
        if event.delta:
            # Windows
            delta = -1 * (event.delta / 120)
        elif event.num == 4:
            # Linux scroll up
            delta = -1
        elif event.num == 5:
            # Linux scroll down
            delta = 1
        else:
            delta = 0

        # Scroll the canvas
        self.sidebar_canvas.yview_scroll(int(delta), "units")

    def toggle_sidebar(self):
        """Toggle sidebar collapse/expand."""
        if self.sidebar_collapsed:
            # Expand sidebar
            self.sidebar_canvas.pack(side="left", fill="both", expand=True)
            self.sidebar_scrollbar.pack(side="right", fill="y")
            self.collapse_button.config(text="◀")
            self.sidebar_collapsed = False
        else:
            # Collapse sidebar
            self.sidebar_canvas.pack_forget()
            self.sidebar_scrollbar.pack_forget()
            self.collapse_button.config(text="▶")
            self.sidebar_collapsed = True

    def configure_paned_window(self):
        """Configure the PanedWindow with appropriate initial sizing."""
        try:
            # Get current window width
            window_width = self.root.winfo_width()

            # Set sidebar to take 25% of window width, but with min/max limits
            if window_width > 100:  # Ensure window is actually rendered
                sidebar_width = max(250, min(350, int(window_width * 0.25)))

                # Set the sash position (distance from left edge)
                self.main_frame.sashpos(0, sidebar_width)
        except:
            # If there's any error, try again later
            self.root.after(100, self.configure_paned_window)

    def create_chat_display(self):
        """Create the chat display area."""
        # Create a frame for the chat and input areas with padding
        self.chat_input_frame = ttk.Frame(self.main_frame, padding=(10, 10, 10, 10))
        self.main_frame.add(self.chat_input_frame, weight=1)  # Chat area expands to fill remaining space

        # Chat area - now directly in main_frame, below sidebar
        chat_frame = ttk.Frame(self.chat_input_frame)
        chat_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5) # Pack below sidebar

        # System instructions area with enhanced styling and rounded corners
        system_frame = ttk.LabelFrame(chat_frame, text="System Instructions", padding=(12, 12, 12, 12))
        system_frame.pack(fill=tk.X, padx=10, pady=10)

        self.system_text = scrolledtext.ScrolledText(
            system_frame,
            height=2,
            wrap=tk.WORD,
            font=("Segoe UI", 11),  # Slightly larger font
            bg=self.secondary_bg,
            fg=self.fg_color,
            insertbackground=self.cursor_color,  # Light blue cursor for better visibility
            padx=15,  # Increased horizontal padding
            pady=15,  # Increased vertical padding
            borderwidth=0,  # No border for cleaner look
            highlightthickness=2,  # Thicker highlight for focus
            highlightcolor=self.highlight_color,  # Cyan highlight when focused
            highlightbackground=self.border_color,
            relief="flat"  # Flat relief for modern look
        )
        self.system_text.pack(fill=tk.X, padx=5, pady=5)
        self.system_text.insert('1.0', self.settings.get("system_prompt", "Respond honestly, objectively and concisely."))

        # Main chat display - using custom HTMLText widget with enhanced styling and rounded corners
        self.chat_display = HTMLText(
            chat_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 12),
            bg=self.tertiary_bg,  # Darker background for better contrast
            fg=self.fg_color,
            insertbackground=self.cursor_color,  # Light blue cursor for better visibility
            padx=20,  # Increased padding for better readability
            pady=20,  # Increased padding for better readability
            borderwidth=0,  # No border for cleaner look
            highlightthickness=2,  # Thicker highlight for focus
            highlightcolor=self.highlight_color,  # Cyan highlight when focused
            highlightbackground=self.border_color,
            cursor="arrow",  # Use arrow cursor for better UX
            relief="flat"  # Flat relief for modern look
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

        # Add the input field to the frame with enhanced styling and rounded corners
        self.input_field = scrolledtext.ScrolledText(
            input_field_frame,
            wrap=tk.WORD,
            height=4,
            font=("Segoe UI", 12),
            padx=20,  # Increased padding for better readability
            pady=20,  # Increased padding for better readability
            bg=self.secondary_bg,
            fg=self.fg_color,
            insertbackground=self.cursor_color,  # Light blue cursor for better visibility
            borderwidth=0,  # No border for cleaner look
            highlightthickness=2,  # Thicker highlight for focus
            highlightcolor=self.highlight_color,  # Cyan highlight when focused
            highlightbackground=self.border_color,
            insertwidth=2,  # Wider cursor for better visibility
            relief="flat"  # Flat relief for modern look
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

        # Use Primary button style for the Send button to make it stand out
        ttk.Button(
            button_frame,
            text="Send",
            command=self.send_message,
            style="Primary.TButton"
        ).pack(side=tk.LEFT, padx=5)

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
        # Configure message tags with enhanced colors from our new theme
        self.chat_display.tag_configure('user', foreground=self.accent_color)  # Vibrant blue for user
        self.chat_display.tag_configure('assistant', foreground=self.success_color)  # Vibrant green for assistant
        self.chat_display.tag_configure('system', foreground=self.subtle_accent)  # Purple for system
        self.chat_display.tag_configure('error', foreground=self.error_color)  # Bright red for errors
        self.chat_display.tag_configure('warning', foreground=self.warning_color)  # Rich amber for warnings
        self.chat_display.tag_configure('status', foreground=self.muted_text)  # Muted text for status

        # Configure additional tags for rich text formatting with enhanced styling
        self.chat_display.tag_configure('user_label', foreground=self.accent_color, font=("Segoe UI", 13, "bold"))
        self.chat_display.tag_configure('assistant_label', foreground=self.success_color, font=("Segoe UI", 13, "bold"))
        self.chat_display.tag_configure('warning_label', foreground=self.warning_color, font=("Segoe UI", 13, "bold"))
        self.chat_display.tag_configure('system_label', foreground=self.subtle_accent, font=("Segoe UI", 13, "bold"))
        self.chat_display.tag_configure('error_label', foreground=self.error_color, font=("Segoe UI", 13, "bold"))
        self.chat_display.tag_configure('status_label', foreground=self.muted_text, font=("Segoe UI", 13, "bold"))

        # Configure file preview tags with enhanced colors
        self.chat_display.tag_configure('file_label', foreground=self.highlight_color, font=("Segoe UI", 13, "bold"))  # Cyan for file name
        self.chat_display.tag_configure('file_info', foreground=self.subtle_accent, font=("Segoe UI", 12))  # Purple for file info

        # Configure link tag for clickable links with enhanced styling
        self.chat_display.tag_configure('link', foreground=self.highlight_color, underline=1)
        self.chat_display.tag_bind('link', '<Button-1>', lambda e: self.open_url_from_text())

    def create_context_menu(self):
        """Create context menu for right-click actions."""
        # Common menu style
        menu_style = {
            'tearoff': 0,
            'bg': self.secondary_bg,
            'fg': self.fg_color,
            'activebackground': self.subtle_accent,
            'activeforeground': "#FFFFFF"
        }

        # Create a context menu for the chat display
        self.context_menu = Menu(self.root, **menu_style)
        self.context_menu.add_command(label="Copy", command=self.copy_selection)
        self.context_menu.add_command(label="Copy All", command=self.copy_all)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Select All", command=self.select_all)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Clear Chat", command=self.clear_chat)

        # Create a context menu for the input field
        self.input_context_menu = Menu(self.root, **menu_style)
        self.input_context_menu.add_command(label="Cut", command=lambda: self.input_field.event_generate("<<Cut>>"))
        self.input_context_menu.add_command(label="Copy", command=lambda: self.input_field.event_generate("<<Copy>>"))
        self.input_context_menu.add_command(label="Paste", command=lambda: self.input_field.event_generate("<<Paste>>"))
        self.input_context_menu.add_separator()
        self.input_context_menu.add_command(label="Select All", command=lambda: self.input_field.tag_add("sel", "1.0", "end"))
        self.input_context_menu.add_separator()
        self.input_context_menu.add_command(label="Clear", command=lambda: self.input_field.delete("1.0", tk.END))

        # Create a context menu for the system instructions
        self.system_context_menu = Menu(self.root, **menu_style)
        self.system_context_menu.add_command(label="Cut", command=lambda: self.system_text.event_generate("<<Cut>>"))
        self.system_context_menu.add_command(label="Copy", command=lambda: self.system_text.event_generate("<<Copy>>"))
        self.system_context_menu.add_command(label="Paste", command=lambda: self.system_text.event_generate("<<Paste>>"))
        self.system_context_menu.add_separator()
        self.system_context_menu.add_command(label="Select All", command=lambda: self.system_text.tag_add("sel", "1.0", "end"))
        self.system_context_menu.add_separator()
        self.system_context_menu.add_command(label="Reset to Default", command=self.reset_system_prompt)

        # Create a context menu for the conversations listbox
        self.conv_context_menu = Menu(self.root, **menu_style)
        self.conv_context_menu.add_command(label="Load Selected", command=lambda: self.load_selected_conversation())
        self.conv_context_menu.add_command(label="Rename Selected", command=lambda: self.rename_selected_conversation())
        self.conv_context_menu.add_command(label="Delete Selected", command=lambda: self.delete_selected_conversation())
        self.conv_context_menu.add_separator()
        self.conv_context_menu.add_command(label="New Conversation", command=self.new_conversation)

    def show_context_menu(self, event, menu):
        """Show the context menu at the current mouse position."""
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            # Make sure to release the grab
            menu.grab_release()

    def copy_all(self):
        """Copy all text from the chat display."""
        self.chat_display.tag_add("sel", "1.0", tk.END)
        self.chat_display.event_generate("<<Copy>>")
        self.chat_display.tag_remove("sel", "1.0", tk.END)

    def select_all(self):
        """Select all text in the chat display."""
        self.chat_display.tag_add("sel", "1.0", tk.END)
        self.chat_display.focus_set()

    def reset_system_prompt(self):
        """Reset the system prompt to default."""
        default_prompt = "Respond honestly, objectively and concisely."
        self.system_text.delete("1.0", tk.END)
        self.system_text.insert("1.0", default_prompt)
        self.settings.set("system_prompt", default_prompt)
        self.display_message("\nSystem prompt reset to default.\n", "status")

    def load_selected_conversation(self):
        """Load the selected conversation from the listbox."""
        selected = self.conversations_listbox.curselection()
        if not selected:
            messagebox.showinfo("Info", "Please select a conversation to load")
            return

        # Get the conversation name
        conv_name = self.conversations_listbox.get(selected[0])

        # Load the conversation
        self.load_conversation_by_name(conv_name)

    def rename_selected_conversation(self):
        """Rename the selected conversation from the listbox."""
        selected = self.conversations_listbox.curselection()
        if not selected:
            messagebox.showinfo("Info", "Please select a conversation to rename")
            return

        # Get the conversation name
        conv_name = self.conversations_listbox.get(selected[0])
        old_name = conv_name.replace('.json', '') if conv_name.endswith('.json') else conv_name

        # Prompt for new name
        from tkinter import simpledialog
        new_name = simpledialog.askstring(
            "Rename Conversation",
            f"Enter new name for '{old_name}':",
            initialvalue=old_name
        )

        if not new_name or new_name.strip() == old_name:
            return

        # Clean the new filename
        safe_name = "".join(c if c.isalnum() or c in [' ', '-', '_'] else '_' for c in new_name.strip())
        safe_name = safe_name.replace(' ', '_')

        if not safe_name:
            messagebox.showerror("Invalid Name", "Please enter a valid name.")
            return

        # Ensure .json extension
        if not safe_name.endswith('.json'):
            safe_name += '.json'

        # Rename the file
        try:
            conversations_dir = self.conversation_manager.conversations_dir
            old_filepath = os.path.join(conversations_dir, f"{conv_name}.json" if not conv_name.endswith('.json') else conv_name)
            new_filepath = os.path.join(conversations_dir, safe_name)

            if os.path.exists(new_filepath):
                messagebox.showerror("File Exists", f"A conversation named '{safe_name}' already exists.")
                return

            os.rename(old_filepath, new_filepath)

            # Update the conversations list
            self.update_conversations_list()

            # Show success message
            self.display_message(f"\nConversation renamed to '{safe_name.replace('.json', '')}'.\n", "status")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rename conversation: {str(e)}")

    def delete_selected_conversation(self):
        """Delete the selected conversation from the listbox."""
        selected = self.conversations_listbox.curselection()
        if not selected:
            messagebox.showinfo("Info", "Please select a conversation to delete")
            return

        # Get the conversation name
        conv_name = self.conversations_listbox.get(selected[0])

        # Confirm deletion
        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete the conversation '{conv_name}'?"
        )

        if confirm:
            # Delete the conversation file
            try:
                filepath = os.path.join("conversations", f"{conv_name}.json")
                if os.path.exists(filepath):
                    os.remove(filepath)

                # Update the conversations list
                self.update_conversations_list()

                # Show success message
                self.display_message(f"\nConversation '{conv_name}' deleted.\n", "status")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete conversation: {str(e)}")

    def bind_events(self):
        """Bind events to widgets."""
        # Create context menus
        self.create_context_menu()

        # Bind Ctrl+Enter AND Enter to send message
        self.input_field.bind('<Control-Return>', lambda e: self.send_message())
        self.input_field.bind('<Return>', lambda e: self.send_message() if not e.state & 0x0001 else None)
        # Don't trigger on Shift+Enter to allow for multi-line input

        # Bind drop for file handling
        self.chat_display.drop_target_register(DND_FILES)
        self.chat_display.dnd_bind('<<Drop>>', self.handle_drop)

        # Allow Copy in chat display
        self.chat_display.bind("<Control-c>", lambda e: self.chat_display.event_generate("<<Copy>>"))

        # Bind right-click to show context menu
        self.chat_display.bind("<Button-3>", lambda e: self.show_context_menu(e, self.context_menu))
        self.input_field.bind("<Button-3>", lambda e: self.show_context_menu(e, self.input_context_menu))
        self.system_text.bind("<Button-3>", lambda e: self.show_context_menu(e, self.system_context_menu))
        self.conversations_listbox.bind("<Button-3>", lambda e: self.show_context_menu(e, self.conv_context_menu))

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

    def setup_mcp(self):
        """Initialize the MCP (Memory Control Program) system."""
        # Create MCP panel but don't show it yet
        self.mcp_panel = MCPPanel(
            self.root,
            self.mcp_manager,
            self.bg_color,
            self.fg_color,
            self.accent_color,
            self.secondary_bg
        )

    def show_mcp_panel(self):
        """Show the MCP panel in a new window."""
        if not self.mcp_panel:
            self.setup_mcp()

        # Create a new top-level window
        mcp_window = tk.Toplevel(self.root)
        mcp_window.title("Memory Control Program")
        mcp_window.geometry("800x600")
        mcp_window.minsize(600, 400)
        mcp_window.configure(background=self.bg_color)

        # Create a new MCP panel specifically for this window
        mcp_panel = MCPPanel(
            mcp_window,
            self.mcp_manager,
            self.bg_color,
            self.fg_color,
            self.accent_color,
            self.secondary_bg
        )
        mcp_panel.show()

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

        # Update the temperature label

    def on_context_change(self, value):
        """Update context window label when slider moves."""
        self.context_label.config(text=f"{int(float(value))}")

    def on_top_k_change(self, value):
        """Update top-k label when slider moves."""
        self.top_k_label.config(text=f"{int(float(value))}")

    def on_top_p_change(self, value):
        """Update top-p label when slider moves."""
        self.top_p_label.config(text=f"{float(value):.2f}")

    def on_repeat_penalty_change(self, value):
        """Update repeat penalty label when slider moves."""
        self.repeat_penalty_label.config(text=f"{float(value):.2f}")

    def on_max_tokens_change(self, value):
        """Update max tokens label when slider moves."""
        self.max_tokens_label.config(text=f"{int(float(value))}")

    # Custom thumb methods removed

    def on_show_image_toggle(self):
        """Update inline image display based on the checkbox."""
        if self.file_type == 'image' and self.file_img:
            self.display_uploaded_image()

    def on_advanced_web_access_toggle(self):
        """Handle web search toggle."""
        advanced_web_access = self.advanced_web_access_var.get()
        self.settings.set("advanced_web_access", advanced_web_access)

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

    def on_write_file_toggle(self):
        """Handle write file tool toggle."""
        write_file_enabled = self.write_file_var.get()
        self.settings.set("write_file", write_file_enabled)

        if write_file_enabled:
            self.display_message("\n📝 Write File tool enabled!\n", "status")
            self.display_message("\nHow to use:\n", "status")
            self.display_message("• Ask the AI to create a file and specify the path like: [[\"/path/to/file.txt\"]]\n", "status")
            self.display_message("• Example: \"Create a summary table and save it as [[\"C:\\Users\\micah\\summary.txt\"]]\"\n", "status")
            self.display_message("• Supported formats: TXT, MD, JSON, CSV, HTML, XML, PY, JS, and more\n", "status")
            self.display_message("• The AI will automatically extract content from code blocks or response text\n", "status")
        else:
            self.display_message("\nWrite File tool disabled.\n", "status")

    def on_read_file_toggle(self):
        """Handle read file tool toggle."""
        read_file_enabled = self.read_file_var.get()
        self.settings.set("read_file", read_file_enabled)

        if read_file_enabled:
            self.display_message("\n📖 Read File tool enabled!\n", "status")
            self.display_message("\nHow to use:\n", "status")
            self.display_message("• Reference files in your messages using: <<\"C:\\path\\to\\file.ext\">>\n", "status")
            self.display_message("• Example: \"Using the data in <<\"data.csv\">>, create a summary\"\n", "status")
            self.display_message("• Supported formats: All MarkItDown formats (DOCX, PDF, images, etc.)\n", "status")
            self.display_message("• Files are automatically read and included in your message\n", "status")
        else:
            self.display_message("\nRead File tool disabled.\n", "status")

    def on_intelligent_processing_toggle(self):
        """Handle intelligent file processing toggle."""
        intelligent_processing = self.intelligent_processing_var.get()
        self.settings.set("intelligent_processing", intelligent_processing)

        if intelligent_processing:
            self.display_message("\nIntelligent file processing enabled. Images and complex content will be processed with AI.\n", "status")
        else:
            self.display_message("\nIntelligent file processing disabled. Only text content will be extracted.\n", "status")

    def on_truncate_file_display_toggle(self):
        """Handle truncate file display toggle."""
        truncate_enabled = self.truncate_file_display_var.get()
        self.settings.set("truncate_file_display", truncate_enabled)

    # OpenAI Example
    # def create_intelligent_markitdown(self):
    #     """Create a MarkItDown instance with OpenAI integration for intelligent processing."""
    #     try:
    #         from openai import OpenAI
    #         api_key = os.getenv('OPENAI_API_KEY')
    #         if not api_key:
    #             return self.create_basic_markitdown()
    #         
    #         client = OpenAI(api_key=api_key)
    #         md = MarkItDown(llm_client=client, llm_model="gpt-4o-mini")
    #         return md
    #     except Exception as e:
    #         return self.create_basic_markitdown()
    

    # Qwen Example using Ollama
    def create_intelligent_markitdown(self):
        try:
            from ollama import Client
    
            # Create Ollama client
            ollama_client = Client(host='http://localhost:11434')
    
            # Create wrapper to make Ollama compatible with OpenAI interface
            class OllamaWrapper:
                def __init__(self, client):
                    self.client = client
    
                class chat:
                    class completions:
                        @staticmethod
                        def create(messages, model="benhaotang/Nanonets-OCR-s:latest", **kwargs):
                            pass
                        
            client = OllamaWrapper(ollama_client)
            md = MarkItDown(llm_client=client, llm_model="benhaotang/Nanonets-OCR-s:latest")  # Use vision model
            return md
        except Exception:
            return self.create_basic_markitdown()

    def create_basic_markitdown(self):
        """Create a basic MarkItDown instance for text-only extraction."""
        return MarkItDown()

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

            # Choose MarkItDown instance based on intelligent processing setting
            if self.intelligent_processing_var.get():
                self.display_message("\nUsing intelligent processing for enhanced content extraction...\n", 'status')
                md = self.create_intelligent_markitdown()
            else:
                self.display_message("\nUsing basic text extraction...\n", 'status')
                md = self.create_basic_markitdown()

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

        # Store original input for display purposes
        original_input = user_input

        # Process file read requests if Read File tool is enabled
        if self.read_file_var.get():
            user_input = self.process_file_read_requests(user_input)

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

        # Add to conversation manager (use processed input)
        self.conversation_manager.add_message_to_active("user", user_input)

        # Display user message (use truncated version if enabled)
        display_input = self.get_truncated_display_message(original_input)
        self.display_message("\n", 'user')
        self.display_message(f"{display_input}\n", 'user')

        self.input_field.delete("1.0", tk.END)

        # Prepare message content
        content = user_input

        # Add web search results if enabled
        if self.advanced_web_access_var.get():
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

        # Include relevant memories if MCP is running
        if hasattr(self, 'mcp_manager') and self.mcp_manager.is_running:
            # Get relevant memories
            memories = self.mcp_manager.get_relevant_memories(user_input)
            if memories and memories != "No relevant memories found.":
                content += f"\n\n{memories}"

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

            # Add tool capabilities to system message if tools are enabled
            tool_instructions = []

            if self.write_file_var.get():
                tool_instructions.append(
                    "WRITE FILE TOOL: You can create files by including file paths in your response using the format [[\"path/to/file.ext\"]] or [[path/to/file.ext]]. "
                    "IMPORTANT: When a user asks you to save content to a file, you MUST include the exact file path in your response using the [[ ]] format. "
                    "Example: 'Here is your content: [content here] [[\"C:\\Users\\file.txt\"]]' "
                    "The system will automatically extract content from your response and write it to the specified file. "
                    "Supported formats include TXT, MD, JSON, CSV, HTML, XML, PY, JS, and more."
                )

            if self.read_file_var.get():
                tool_instructions.append(
                    "READ FILE TOOL: The user can reference files in their messages using the format <<\"path/to/file.ext\">> or <<path/to/file.ext>>. "
                    "When you see this format in a user's message, the file content has already been automatically read and included in their message. "
                    "You can reference and work with this file content directly. The system supports all MarkItDown formats including DOCX, PDF, images, and more."
                )

            if self.advanced_web_access_var.get():
                tool_instructions.append(
                    "WEB SEARCH TOOL: You have access to real-time web search capabilities. "
                    "You can search for current information and browse websites to provide up-to-date responses."
                )

            # Combine system message with tool instructions
            if tool_instructions:
                enhanced_system_msg = system_msg
                if enhanced_system_msg:
                    enhanced_system_msg += "\n\nAVAILABLE TOOLS:\n" + "\n".join(tool_instructions)
                else:
                    enhanced_system_msg = "AVAILABLE TOOLS:\n" + "\n".join(tool_instructions)
                system_msg = enhanced_system_msg

                # Debug message to confirm tools are enabled
                tool_names = []
                if self.write_file_var.get():
                    tool_names.append("Write File")
                if self.read_file_var.get():
                    tool_names.append("Read File")
                if self.advanced_web_access_var.get():
                    tool_names.append("Web Search")

                if tool_names:
                    self.display_message(f"\n🔧 Active tools: {', '.join(tool_names)}\n", "status")

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
                context_size=self.context_size.get(),
                top_k=self.top_k.get(),
                top_p=self.top_p.get(),
                repeat_penalty=self.repeat_penalty.get(),
                max_tokens=self.max_tokens.get()
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

                    # Process file write requests if the tool is enabled
                    if self.write_file_var.get():
                        try:
                            # Debug: Show what we're analyzing
                            self.display_message(f"\n🔍 Analyzing response for file paths...\n", 'status')

                            files_written = self.process_file_write_requests(full_response)
                            if files_written > 0:
                                # Add file writing info to conversation history
                                file_info = f"\n[File Writing: {files_written} file(s) created]"
                                self.conversation_manager.add_message_to_active("system", file_info)
                            else:
                                # Check if user requested file saving but AI didn't include path pattern
                                user_message = message.get('content', '').lower()
                                if any(keyword in user_message for keyword in ['save to', 'write to', 'save as', 'create file', 'save it to']):
                                    self.display_message(f"\n⚠️ File save requested but no file path pattern found in AI response.\n", 'warning')
                                    self.display_message(f"💡 The AI should include the file path like: [[\"C:\\path\\to\\file.txt\"]] in its response.\n", 'warning')

                                    # Try to extract file path from user message and suggest a follow-up
                                    import re
                                    path_match = re.search(r'\[\[([^\]]+)\]\]', message.get('content', ''))
                                    if path_match:
                                        suggested_path = path_match.group(1).strip('"').strip("'")
                                        self.display_message(f"🔧 Try asking: 'Please include [[\"" + suggested_path + "\"]] in your response to save the file.'\n", 'status')
                        except Exception as e:
                            error_msg = error_handler.handle_error(e, "Processing file write requests")
                            self.display_message(f"\nError processing file write requests: {error_msg}\n", 'error')

                    # Add the response to MCP memories if it's running
                    if hasattr(self, 'mcp_manager') and self.mcp_manager.is_running:
                        # Extract the user's question from the message
                        user_question = message.get('content', '').split('\n')[0]  # Get first line as question
                        # Create a memory with the Q&A pair
                        memory_content = f"Q: {user_question}\nA: {full_response}"
                        self.mcp_manager.add_memory(memory_content, tags=["conversation"])

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

    def detect_file_write_requests(self, response_text):
        """Detect file writing requests in the AI response.

        Args:
            response_text: The complete AI response text

        Returns:
            list: List of dictionaries containing file write requests
        """
        if not self.write_file_var.get():
            return []

        write_requests = []

        # Pattern 1: [["/path/to/file.ext"]] format (with quotes)
        pattern1 = r'\[\["([^"]+)"\]\]'
        matches1 = re.findall(pattern1, response_text)

        # Pattern 2: [[path]] format (without quotes)
        pattern2 = r'\[\[([^\]"]+)\]\]'
        matches2 = re.findall(pattern2, response_text)

        # Combine and deduplicate matches
        all_paths = list(set(matches1 + matches2))

        for path in all_paths:
            # Clean the path
            clean_path = path.strip().strip('"').strip("'")

            # Validate path
            if self.is_valid_file_path(clean_path):
                # Extract content for this file
                content = self.extract_file_content_from_response(response_text, path)

                write_requests.append({
                    'path': clean_path,
                    'content': content,
                    'original_pattern': path
                })

        return write_requests

    def is_valid_file_path(self, path):
        """Validate if the path is a valid file path.

        Args:
            path: The file path to validate

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            # Check if path is not empty
            if not path or len(path.strip()) == 0:
                return False

            # Check for invalid characters (basic validation)
            invalid_chars = ['<', '>', '|', '*', '?']
            if any(char in path for char in invalid_chars):
                return False

            # Check if it has a file extension
            if '.' not in os.path.basename(path):
                return False

            # Check if directory part exists or can be created
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                # Try to create directory
                try:
                    os.makedirs(directory, exist_ok=True)
                except:
                    return False

            return True
        except:
            return False

    def extract_file_content_from_response(self, response_text, file_path):
        """Extract content intended for a specific file from the AI response.

        Args:
            response_text: The complete AI response
            file_path: The file path to extract content for

        Returns:
            str: The extracted content
        """
        # Try to find content in code blocks first
        code_block_content = self.extract_from_code_blocks(response_text, file_path)
        if code_block_content:
            return code_block_content

        # Try to find content after the file path mention
        content_after_path = self.extract_content_after_path(response_text, file_path)
        if content_after_path:
            return content_after_path

        # Fallback: use the entire response (cleaned)
        return self.clean_response_for_file(response_text)

    def extract_from_code_blocks(self, response_text, file_path):
        """Extract content from code blocks in the response.

        Args:
            response_text: The AI response text
            file_path: The target file path

        Returns:
            str: Extracted code block content or None
        """
        # Pattern for code blocks with language specification
        code_block_pattern = r'```(\w+)?\s*(.*?)\s*```'
        matches = re.findall(code_block_pattern, response_text, re.DOTALL)

        if matches:
            # Get file extension to match with code block language
            file_ext = os.path.splitext(file_path)[1].lower()

            # Language mapping
            lang_map = {
                '.py': 'python',
                '.js': 'javascript',
                '.html': 'html',
                '.css': 'css',
                '.json': 'json',
                '.xml': 'xml',
                '.md': 'markdown',
                '.txt': 'text',
                '.csv': 'csv'
            }

            expected_lang = lang_map.get(file_ext, '')

            # Try to find matching language block first
            for lang, content in matches:
                if lang.lower() == expected_lang:
                    return content.strip()

            # If no language match, return the first code block
            return matches[0][1].strip()

        return None

    def extract_content_after_path(self, response_text, file_path):
        """Extract content that appears after the file path mention.

        Args:
            response_text: The AI response text
            file_path: The file path mentioned

        Returns:
            str: Extracted content or None
        """
        # Find the position of the file path in the response
        path_patterns = [
            f'[["{file_path}"]]',
            f'[[\'{file_path}\']]',
            f'[[{file_path}]]'
        ]

        for pattern in path_patterns:
            if pattern in response_text:
                # Find content after this pattern
                start_pos = response_text.find(pattern) + len(pattern)
                remaining_text = response_text[start_pos:].strip()

                # Extract meaningful content (stop at next file path or end)
                next_file_pattern = r'\[\[.*?\]\]'
                next_match = re.search(next_file_pattern, remaining_text)

                if next_match:
                    content = remaining_text[:next_match.start()].strip()
                else:
                    content = remaining_text

                # Clean and return if substantial content
                if len(content) > 10:  # Minimum content length
                    return self.clean_response_for_file(content)

        return None

    def clean_response_for_file(self, text):
        """Clean the response text for file writing.

        Args:
            text: The text to clean

        Returns:
            str: Cleaned text suitable for file writing
        """
        # Remove file path patterns
        text = re.sub(r'\[\[.*?\]\]', '', text)

        # Remove common AI response prefixes
        prefixes_to_remove = [
            "Here's the content for",
            "I'll create",
            "I'll write",
            "Here is",
            "Here's",
            "The file content is:",
            "File content:",
        ]

        for prefix in prefixes_to_remove:
            if text.strip().lower().startswith(prefix.lower()):
                text = text[len(prefix):].strip()
                break

        # Remove leading/trailing whitespace and normalize line endings
        text = text.strip()
        text = re.sub(r'\r\n|\r', '\n', text)

        return text

    def write_file_safely(self, file_path, content):
        """Write content to a file with safety checks.

        Args:
            file_path: The path where to write the file
            content: The content to write

        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Normalize the path
            file_path = os.path.normpath(file_path)

            # Additional safety checks
            if len(file_path) > 260:  # Windows path length limit
                return False, f"Path too long (max 260 characters): '{file_path}'"

            # Check for dangerous paths
            dangerous_patterns = ['..', '~', '$']
            if any(pattern in file_path for pattern in dangerous_patterns):
                return False, f"Potentially unsafe path detected: '{file_path}'"

            # Check file size limit (10MB)
            if len(content.encode('utf-8')) > 10 * 1024 * 1024:
                return False, f"Content too large (max 10MB): {len(content)} characters"

            # Check if file already exists
            file_exists = os.path.exists(file_path)
            if file_exists:
                self.display_message(f"\n⚠️ File '{file_path}' already exists and will be overwritten.\n", 'warning')

            # Ensure directory exists
            directory = os.path.dirname(file_path)
            if directory:
                os.makedirs(directory, exist_ok=True)

            # Create backup if file exists
            backup_path = None
            if file_exists:
                backup_path = f"{file_path}.backup"
                try:
                    import shutil
                    shutil.copy2(file_path, backup_path)
                    self.display_message(f"\n💾 Backup created: '{backup_path}'\n", 'status')
                except:
                    pass  # Backup failed, but continue

            # Write the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Verify the write was successful
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                return True, f"Successfully wrote {len(content)} characters ({file_size} bytes) to '{file_path}'"
            else:
                return False, f"File write appeared to succeed but file not found: '{file_path}'"

        except PermissionError:
            return False, f"Permission denied: Cannot write to '{file_path}'. Check folder permissions."
        except OSError as e:
            return False, f"OS error writing to '{file_path}': {str(e)}"
        except UnicodeEncodeError as e:
            return False, f"Unicode encoding error for '{file_path}': {str(e)}"
        except Exception as e:
            return False, f"Unexpected error writing to '{file_path}': {str(e)}"

    def process_file_write_requests(self, response_text):
        """Process all file write requests found in the response.

        Args:
            response_text: The complete AI response text

        Returns:
            int: Number of files successfully written
        """
        if not self.write_file_var.get():
            return 0

        write_requests = self.detect_file_write_requests(response_text)

        if not write_requests:
            return 0

        successful_writes = 0

        self.display_message(f"\n📝 Processing {len(write_requests)} file write request(s)...\n", 'status')

        for request in write_requests:
            file_path = request['path']
            content = request['content']

            if not content or len(content.strip()) == 0:
                self.display_message(f"\n⚠️ Skipping '{file_path}': No content to write\n", 'warning')
                continue

            success, message = self.write_file_safely(file_path, content)

            if success:
                successful_writes += 1
                if self.truncate_file_display_var.get():
                    # Minimal status message
                    filename = os.path.basename(file_path)
                    self.display_message(f"{filename} written\n", 'status')
                else:
                    # Detailed status message (existing)
                    self.display_message(f"\n✅ {message}\n", 'status')
                    # Show preview of written content
                    preview = content[:100] + "..." if len(content) > 100 else content
                    self.display_message(f"Preview: {preview}\n", 'status')
            else:
                self.display_message(f"\n❌ Failed to write '{file_path}': {message}\n", 'error')

        if successful_writes > 0:
            self.display_message(f"\n🎉 Successfully wrote {successful_writes} file(s)!\n", 'status')

        return successful_writes

    def get_truncated_display_message(self, user_input):
        """Generate truncated display message showing only file operations."""
        if not self.truncate_file_display_var.get():
            return user_input

        # Extract file read patterns
        read_pattern1 = r'<<\"([^\"]+)\">>'
        read_pattern2 = r'<<([^>\"]+)>>'
        read_matches = re.findall(read_pattern1, user_input) + re.findall(read_pattern2, user_input)

        # Extract file write patterns
        write_pattern1 = r'\[\[\"([^\"]+)\"\]\]'
        write_pattern2 = r'\[\[([^\]\"]+)\]\]'
        write_matches = re.findall(write_pattern1, user_input) + re.findall(write_pattern2, user_input)

        # Build truncated message
        truncated_parts = []

        # Add file read notifications
        for path in read_matches:
            filename = os.path.basename(path.strip().strip('"').strip("'"))
            truncated_parts.append(f"{filename} read")

        # Add file write notifications
        for path in write_matches:
            filename = os.path.basename(path.strip().strip('"').strip("'"))
            truncated_parts.append(f"{filename} written")

        # Remove file patterns from original message
        display_message = user_input
        for pattern in [read_pattern1, read_pattern2, write_pattern1, write_pattern2]:
            display_message = re.sub(pattern, '', display_message)

        # Clean up extra whitespace
        display_message = re.sub(r'\s+', ' ', display_message).strip()

        # Combine with file operations
        if truncated_parts:
            if display_message:
                return f"{display_message}\n\n" + "\n".join(truncated_parts)
            else:
                return "\n".join(truncated_parts)

        return display_message

    def process_file_read_requests(self, user_input):
        """Process file read requests in user input and replace with file content.

        Args:
            user_input: The user's input message

        Returns:
            str: The processed message with file content included
        """
        if not self.read_file_var.get():
            return user_input

        # Pattern 1: <<"path">> format (with quotes)
        pattern1 = r'<<\"([^\"]+)\">>'
        # Pattern 2: <<path>> format (without quotes)
        pattern2 = r'<<([^>\"]+)>>'

        # Find all file read requests
        matches1 = re.findall(pattern1, user_input)
        matches2 = re.findall(pattern2, user_input)

        # Combine and deduplicate matches
        all_paths = list(set(matches1 + matches2))

        if not all_paths:
            return user_input

        self.display_message(f"\n📖 Processing {len(all_paths)} file read request(s)...\n", 'status')

        processed_input = user_input
        files_read = 0

        for path in all_paths:
            # Clean the path
            clean_path = path.strip().strip('"').strip("'")

            # Try to read the file
            file_content = self.read_file_safely(clean_path)

            if file_content:
                files_read += 1

                # Replace the file reference with the content
                # Try both patterns
                for pattern in [f'<<"{path}">>', f"<<'{path}'>>", f'<<{path}>>']:
                    if pattern in processed_input:
                        replacement = f"\n\n--- Content from {clean_path} ---\n{file_content}\n--- End of {clean_path} ---\n\n"
                        processed_input = processed_input.replace(pattern, replacement)
                        break

                if self.truncate_file_display_var.get():
                    # Minimal status message
                    filename = os.path.basename(clean_path)
                    self.display_message(f"{filename} read\n", 'status')
                else:
                    # Detailed status message (existing)
                    self.display_message(f"✅ Read file: {clean_path} ({len(file_content)} characters)\n", 'status')
            else:
                self.display_message(f"❌ Failed to read file: {clean_path}\n", 'error')

        if files_read > 0:
            self.display_message(f"📚 Successfully read {files_read} file(s) and included in your message.\n", 'status')

        return processed_input

    def read_file_safely(self, file_path):
        """Safely read a file using MarkItDown.

        Args:
            file_path: The path to the file to read

        Returns:
            str: The file content as markdown, or None if failed
        """
        try:
            # Normalize the path
            file_path = os.path.normpath(file_path)

            # Check if file exists
            if not os.path.exists(file_path):
                return None

            # Check file size limit (50MB)
            file_size = os.path.getsize(file_path)
            if file_size > 50 * 1024 * 1024:
                self.display_message(f"⚠️ File too large (max 50MB): {file_path}\n", 'warning')
                return None

            # Use MarkItDown to convert file content
            md = MarkItDown()

            # Check if intelligent processing is enabled
            if self.intelligent_processing_var.get():
                # Use OpenAI for intelligent processing if available
                try:
                    import openai
                    api_key = os.getenv('OPENAI_API_KEY')
                    if api_key:
                        md = MarkItDown(llm_client=openai.OpenAI(api_key=api_key), llm_model="gpt-4o-mini")
                except:
                    pass  # Fall back to basic processing

            # Convert file to markdown
            result = md.convert(file_path)

            if result and hasattr(result, 'text_content'):
                return result.text_content
            elif isinstance(result, str):
                return result
            else:
                return None

        except PermissionError:
            self.display_message(f"⚠️ Permission denied: {file_path}\n", 'warning')
            return None
        except Exception as e:
            self.display_message(f"⚠️ Error reading file {file_path}: {str(e)}\n", 'warning')
            return None

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
            "top_k": self.top_k.get(),
            "top_p": self.top_p.get(),
            "repeat_penalty": self.repeat_penalty.get(),
            "max_tokens": self.max_tokens.get(),
            "include_chat": self.include_chat_var.get(),
            "show_image": self.show_image_var.get(),
            "include_file": self.include_file_var.get(),
            "advanced_web_access": self.advanced_web_access_var.get(),
            "write_file": self.write_file_var.get(),
            "read_file": self.read_file_var.get(),
            "intelligent_processing": self.intelligent_processing_var.get(),
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

        # Use clear_chat to handle both UI clearing and model context clearing
        self.clear_chat()

        # Update conversations list
        self.update_conversations_list()

        # Show status message
        self.display_message("Started a new conversation.\n", "status")

    def save_conversation(self):
        """Save the current conversation with custom filename and clean format."""
        if not self.conversation_manager.active_conversation.messages:
            messagebox.showinfo("Save Conversation", "No messages to save.")
            return

        # Prompt user for custom filename
        from tkinter import simpledialog

        # Suggest a default name based on the first user message or current time
        default_name = self._generate_default_filename()

        custom_name = simpledialog.askstring(
            "Save Conversation",
            "Enter a name for this conversation:",
            initialvalue=default_name
        )

        if not custom_name:
            return  # User cancelled

        # Clean the filename
        safe_name = "".join(c if c.isalnum() or c in [' ', '-', '_'] else '_' for c in custom_name)
        safe_name = safe_name.strip().replace(' ', '_')

        if not safe_name:
            safe_name = "conversation"

        # Save with clean format
        result = self.save_conversation_clean_format(safe_name)
        self.display_message(f"\n{result}\n", "status")

        # Update conversations list
        self.update_conversations_list()

    def _generate_default_filename(self):
        """Generate a default filename based on conversation content."""
        messages = self.conversation_manager.active_conversation.messages

        # Find the first meaningful user message
        for message in messages:
            if message.role == 'user' and message.content.strip():
                # Take first 30 characters and clean them
                content = message.content.strip()
                # Remove common file-related prefixes
                if content.lower().startswith(('document content:', 'file content:', 'image:')):
                    continue
                # Take first sentence or 30 characters
                first_sentence = content.split('.')[0][:30]
                if first_sentence:
                    return first_sentence.strip()

        # Fallback to timestamp
        from datetime import datetime
        return f"Chat_{datetime.now().strftime('%Y%m%d_%H%M')}"

    def save_conversation_clean_format(self, filename):
        """Save conversation in a clean, simplified format."""
        try:
            messages = self.conversation_manager.active_conversation.messages
            if not messages:
                return "No messages to save"

            # Create clean conversation data
            clean_conversation = []
            files_mentioned = []

            for message in messages:
                # Skip system, status, and error messages for clean format
                if message.role in ['system', 'status', 'error']:
                    continue

                content = message.content.strip()
                if not content:
                    continue

                # Check for file references
                if 'Document content:' in content or 'File path:' in content:
                    # Extract file information
                    lines = content.split('\n')
                    for line in lines:
                        if line.strip().startswith('File path:'):
                            file_path = line.replace('File path:', '').strip()
                            if file_path and file_path not in files_mentioned:
                                files_mentioned.append(os.path.basename(file_path))

                    # Clean the content by removing file metadata
                    cleaned_lines = []
                    skip_next = False
                    for line in lines:
                        line = line.strip()
                        if line.startswith(('Document content:', 'File path:', 'File has', 'Word count:')):
                            if line.startswith('Document content:'):
                                skip_next = True
                            continue
                        if skip_next and not line:
                            skip_next = False
                            continue
                        skip_next = False
                        if line:
                            cleaned_lines.append(line)

                    content = '\n'.join(cleaned_lines).strip()

                # Only add non-empty content
                if content:
                    if message.role == 'user':
                        clean_conversation.append({"User": content})
                    elif message.role == 'assistant':
                        clean_conversation.append({"Assistant": content})

            # Add file information if any files were processed
            if files_mentioned:
                file_info = f"Files processed: {', '.join(files_mentioned)}"
                clean_conversation.insert(0, {"Files": file_info})

            # Ensure filename has .json extension
            if not filename.endswith('.json'):
                filename += '.json'

            # Save to conversations directory
            conversations_dir = self.conversation_manager.conversations_dir
            filepath = os.path.join(conversations_dir, filename)

            # Check if file exists and ask for confirmation
            if os.path.exists(filepath):
                confirm = messagebox.askyesno(
                    "File Exists",
                    f"A file named '{filename}' already exists. Do you want to overwrite it?"
                )
                if not confirm:
                    return "Save cancelled"

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(clean_conversation, f, indent=2, ensure_ascii=False)

            return f"Conversation saved as '{filename}' in clean format"

        except Exception as e:
            return f"Error saving conversation: {str(e)}"

    def rename_conversation(self):
        """Rename an existing conversation file."""
        # Get list of conversation files
        files = self.conversation_manager.list_conversations()

        if not files:
            messagebox.showinfo("Rename Conversation", "No saved conversations found.")
            return

        # Create a selection dialog
        rename_window = tk.Toplevel(self.root)
        rename_window.title("Rename Conversation")
        rename_window.geometry("500x400")
        rename_window.configure(background=self.bg_color)
        rename_window.transient(self.root)
        rename_window.grab_set()

        # Center the window
        rename_window.update_idletasks()
        x = (rename_window.winfo_screenwidth() // 2) - (500 // 2)
        y = (rename_window.winfo_screenheight() // 2) - (400 // 2)
        rename_window.geometry(f"500x400+{x}+{y}")

        # Title
        title_label = ttk.Label(rename_window, text="Select Conversation to Rename",
                               font=("Segoe UI", 12, "bold"))
        title_label.pack(pady=10)

        # Listbox for conversations
        listbox_frame = ttk.Frame(rename_window)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        conversations_listbox = tk.Listbox(
            listbox_frame,
            bg=self.secondary_bg,
            fg=self.fg_color,
            selectbackground=self.subtle_accent,
            selectforeground="#FFFFFF",
            font=("Segoe UI", 10)
        )
        conversations_listbox.pack(fill=tk.BOTH, expand=True)

        # Populate listbox
        for filename in sorted(files):
            display_name = filename.replace('.json', '') if filename.endswith('.json') else filename
            conversations_listbox.insert(tk.END, display_name)

        # Buttons
        button_frame = ttk.Frame(rename_window)
        button_frame.pack(fill=tk.X, padx=20, pady=10)

        def do_rename():
            selection = conversations_listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a conversation to rename.")
                return

            old_filename = files[selection[0]]
            old_name = old_filename.replace('.json', '') if old_filename.endswith('.json') else old_filename

            # Prompt for new name
            from tkinter import simpledialog
            new_name = simpledialog.askstring(
                "Rename Conversation",
                f"Enter new name for '{old_name}':",
                initialvalue=old_name
            )

            if not new_name or new_name.strip() == old_name:
                return

            # Clean the new filename
            safe_name = "".join(c if c.isalnum() or c in [' ', '-', '_'] else '_' for c in new_name.strip())
            safe_name = safe_name.replace(' ', '_')

            if not safe_name:
                messagebox.showerror("Invalid Name", "Please enter a valid name.")
                return

            # Ensure .json extension
            if not safe_name.endswith('.json'):
                safe_name += '.json'

            # Check if new name already exists
            conversations_dir = self.conversation_manager.conversations_dir
            old_filepath = os.path.join(conversations_dir, old_filename)
            new_filepath = os.path.join(conversations_dir, safe_name)

            if os.path.exists(new_filepath):
                messagebox.showerror("File Exists", f"A conversation named '{safe_name}' already exists.")
                return

            try:
                # Rename the file
                os.rename(old_filepath, new_filepath)
                messagebox.showinfo("Success", f"Conversation renamed to '{safe_name}'")

                # Update the conversations list in main window
                self.update_conversations_list()

                # Close the rename window
                rename_window.destroy()

            except Exception as e:
                messagebox.showerror("Error", f"Failed to rename conversation: {str(e)}")

        ttk.Button(button_frame, text="Rename", command=do_rename,
                  style="Primary.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel",
                  command=rename_window.destroy).pack(side=tk.LEFT, padx=5)

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

        # Get the conversation name from the filepath
        conversation_name = os.path.basename(filepath)
        # Remove the .json extension if present
        if conversation_name.endswith('.json'):
            conversation_name = conversation_name[:-5]  # Remove .json

        # Load the conversation by name
        self.load_conversation_by_name(conversation_name)

    def load_conversation_by_name(self, conversation_name):
        """Load a conversation by its name."""
        try:
            # Construct the filepath
            filepath = os.path.join(self.conversation_manager.conversations_dir, f"{conversation_name}.json")

            # Check if the file exists
            if not os.path.exists(filepath):
                messagebox.showerror("Error", f"Conversation file not found: {conversation_name}")
                return

            # Load the selected conversation
            conversation = self.conversation_manager.load_conversation(filepath)

            if conversation:
                # Update model if it was saved with the conversation
                if conversation.model and conversation.model in self.model_selector["values"]:
                    self.model_selector.set(conversation.model)
                    self.selected_model = conversation.model

                # Clear the chat display first
                self.chat_display["state"] = "normal"
                self.chat_display.delete(1.0, tk.END)
                self.chat_display["state"] = "disabled"

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

                # Update the conversations list
                self.update_conversations_list()
        except Exception as e:
            error_msg = error_handler.handle_error(e, "Loading conversation")
            messagebox.showerror("Error", f"Failed to load conversation: {error_msg}")

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

            # Ask for confirmation
            confirm = messagebox.askyesno(
                "Load Conversation",
                f"Load conversation '{filename}'? This will replace the current conversation."
            )

            if confirm:
                # Extract conversation name (remove .json extension if present)
                conversation_name = filename
                if conversation_name.endswith('.json'):
                    conversation_name = conversation_name[:-5]  # Remove .json

                # Use our new method to load the conversation
                self.load_conversation_by_name(conversation_name)

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
        # Get the current prompt from the input field
        current_prompt = self.input_field.get("1.0", tk.END).strip()

        if not current_prompt:
            self.display_message("\nPlease enter a prompt in the input field first.\n", "error")
            self.display_message("\nThe prompt will be applied to each selected file.\n", "status")
            return

        if not self.selected_model:
            self.display_message("\nNo model selected!\n", "error")
            return

        # Show a message explaining what will happen
        self.display_message(f"\nBatch processing will apply this prompt to each file:\n", "status")
        self.display_message(f"\"{current_prompt}\"\n", "user")

        # Ask user to select files
        self.display_message("\nPlease select files to process...\n", "status")
        files = filedialog.askopenfilenames(title="Select Files for Batch Processing")

        if files:
            # Reset stop event before starting
            self.stop_event.clear()
            # Start processing in a separate thread
            processing_thread = threading.Thread(target=self.process_files, args=(files,))
            processing_thread.daemon = True  # Make thread daemon so it doesn't block program exit
            processing_thread.start()
        else:
            self.display_message("\nBatch processing cancelled - no files selected.\n", "status")

    def clear_model_context(self):
        """Clear the model's context without affecting the UI."""
        if self.selected_model:
            try:
                # Prepare a /clear message
                messages = [{'role': 'user', 'content': '/clear'}]

                # Send the message without displaying it
                self.model_manager.get_response(
                    messages=messages,
                    model=self.selected_model,
                    temperature=self.temperature.get(),
                    context_size=self.context_size.get(),
                    top_k=self.top_k.get(),
                    top_p=self.top_p.get(),
                    repeat_penalty=self.repeat_penalty.get(),
                    max_tokens=self.max_tokens.get()
                )
                return True
            except Exception as e:
                # Silently handle any errors - this is just a best effort
                print(f"Error sending /clear command: {str(e)}")
                return False
        return False

    def process_files(self, files):
        """Process multiple files with the same prompt."""
        # Set batch mode flag to control display behavior
        self.batch_mode = True

        base_prompt = self.input_field.get("1.0", tk.END).strip()
        self.display_message(f"\nStarting batch processing of {len(files)} files\n", "status")

        # Check if we should include chat history
        include_chat = self.include_chat_var.get()
        if not include_chat:
            self.display_message("\nChat history is disabled for batch processing. Each file will be processed independently.\n", "status")

        for idx, file_path in enumerate(files, 1):
            if self.stop_event.is_set():
                break

            self.display_message(f"\nProcessing file {idx}/{len(files)}: {os.path.basename(file_path)}\n", "status")

            # Clear model context if not including chat history
            if idx > 1 and not include_chat:
                self.display_message("\nClearing model context to save memory...\n", "status")
                self.clear_model_context()

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
                context_size=self.context_size.get(),
                top_k=self.top_k.get(),
                top_p=self.top_p.get(),
                repeat_penalty=self.repeat_penalty.get(),
                max_tokens=self.max_tokens.get()
            )
            self.active_stream = stream

            full_response = ""
            accumulated_content = ""
            try:
                for chunk in stream:
                    if self.stop_event.is_set():
                        break

                    if chunk and 'message' in chunk and 'content' in chunk['message']:
                        content = chunk['message']['content']
                        full_response += content

                        # For batch processing, accumulate content and display in logical chunks
                        # to avoid character-by-character display issues
                        if hasattr(self, 'batch_mode') and self.batch_mode:
                            # Accumulate content until we have a meaningful chunk
                            accumulated_content += content

                            # Define patterns for natural breakpoints
                            paragraph_break = re.compile(r'\n\s*\n')
                            list_item = re.compile(r'\n\s*[-*•]\s')
                            numbered_item = re.compile(r'\n\s*\d+\.\s')
                            code_block = re.compile(r'```[\s\S]*?```')
                            sentence_end = re.compile(r'[.!?]\s')

                            # Check for paragraph breaks first (strongest delimiter)
                            match = paragraph_break.search(accumulated_content)
                            if match:
                                display_index = match.end()
                                to_display = accumulated_content[:display_index]
                                accumulated_content = accumulated_content[display_index:]
                            # Then check for list items
                            elif list_item.search(accumulated_content) or numbered_item.search(accumulated_content):
                                # Find the last list item
                                list_matches = list(list_item.finditer(accumulated_content))
                                num_matches = list(numbered_item.finditer(accumulated_content))
                                all_matches = list_matches + num_matches
                                if all_matches:
                                    # Get the position of the last complete list item
                                    last_match = all_matches[-1]
                                    # Display up to the last complete list item
                                    to_display = accumulated_content[:last_match.start()]
                                    accumulated_content = accumulated_content[last_match.start():]
                                else:
                                    # No complete list items found, check for sentences
                                    match = sentence_end.search(accumulated_content)
                                    if match and len(accumulated_content) > 30:
                                        display_index = match.end()
                                        to_display = accumulated_content[:display_index]
                                        accumulated_content = accumulated_content[display_index:]
                                    elif len(accumulated_content) > 200:
                                        # If content is getting long, display it anyway
                                        to_display = accumulated_content
                                        accumulated_content = ""
                                    else:
                                        # Not enough content to display yet
                                        continue
                            # Check for code blocks
                            elif code_block.search(accumulated_content):
                                # Find complete code blocks
                                matches = list(code_block.finditer(accumulated_content))
                                if matches:
                                    last_match = matches[-1]
                                    to_display = accumulated_content[:last_match.end()]
                                    accumulated_content = accumulated_content[last_match.end():]
                                else:
                                    # No complete code blocks, check for sentences
                                    match = sentence_end.search(accumulated_content)
                                    if match and len(accumulated_content) > 30:
                                        display_index = match.end()
                                        to_display = accumulated_content[:display_index]
                                        accumulated_content = accumulated_content[display_index:]
                                    else:
                                        continue
                            # Check for complete sentences
                            elif sentence_end.search(accumulated_content) and len(accumulated_content) > 30:
                                # Find the last sentence end
                                matches = list(sentence_end.finditer(accumulated_content))
                                if matches:
                                    last_match = matches[-1]
                                    to_display = accumulated_content[:last_match.end()]
                                    accumulated_content = accumulated_content[last_match.end():]
                                else:
                                    continue
                            # If content is getting long, display it anyway
                            elif len(accumulated_content) > 200:
                                to_display = accumulated_content
                                accumulated_content = ""
                            else:
                                # Not enough content to display yet
                                continue

                            # Only display non-empty content
                            if to_display and to_display.strip():
                                self.display_message(to_display, 'assistant')
                        else:
                            # Normal streaming mode
                            self.display_message(content, 'assistant')
            finally:
                self.active_stream = None

                # Display any remaining accumulated content
                if hasattr(self, 'batch_mode') and self.batch_mode and accumulated_content.strip():
                    # Format the final content for better readability
                    final_content = accumulated_content.rstrip()

                    # Check if it's a partial code block
                    if '```' in final_content and final_content.count('```') % 2 == 1:
                        # Close the code block
                        final_content += '\n```'

                    # Check if it's a partial list
                    elif re.search(r'\n\s*[-*•]\s[^\n]*$', final_content) or re.search(r'\n\s*\d+\.\s[^\n]*$', final_content):
                        # Add a newline to complete the list
                        final_content += '\n'

                    # Add proper punctuation if missing for regular text
                    elif final_content and not final_content[-1] in ['.', '!', '?', ':', ';', ')', ']', '}']:
                        final_content += '.'

                    # Display the formatted content
                    self.display_message(final_content, 'assistant')

                # Add to conversation history only if include_chat is enabled
                if full_response and include_chat:
                    batch_msg = f"Batch result for {os.path.basename(file_path)}: {full_response}"
                    self.conversation_manager.add_message_to_active("assistant", batch_msg)
                    user_msg = f"Processed file: {os.path.basename(file_path)} with prompt: {base_prompt}"
                    self.conversation_manager.add_message_to_active("user", user_msg)

            self.display_message(f"\nCompleted processing file {idx}/{len(files)}\n", "status")

            # Memory management - force garbage collection after each file
            import gc
            gc.collect()

        # Final clear of model context after batch processing is complete
        if not include_chat:
            self.clear_model_context()

        # Reset batch mode flag
        self.batch_mode = False

        self.display_message("\nBatch processing completed.\n", "status")

    def clear_chat(self):
        """Clear the chat display and conversation history."""
        # Clear the chat display
        self.chat_display["state"] = "normal"
        self.chat_display.delete(1.0, tk.END)
        self.chat_display["state"] = "disabled"
        self.status_bar["text"] = "Ready"

        # Create a new conversation to clear history
        self.conversation_manager.new_conversation(model=self.selected_model)

        # Clear the model context using our helper method
        self.clear_model_context()

        # Display a status message
        self.display_message("Chat and conversation history cleared.\n", "status")

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
            fg=self.fg_color,
            insertbackground=self.cursor_color  # Light blue cursor for better visibility
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
            fg=self.fg_color,
            insertbackground=self.cursor_color  # Light blue cursor for better visibility
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
