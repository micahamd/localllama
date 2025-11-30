import tkinter as tk
from tkinter import scrolledtext, filedialog, StringVar, Menu, messagebox
from tkinter import ttk
from tkinter import font as tkFont
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

# Import MCP modules (consolidated)
from mcp_core import MCPManagerEnhanced as MCPManager
from mcp_ui import MCPPanelEnhanced as MCPPanel

# Enhanced tools system imports (Consolidated)
from tools_system import (
    ToolsManager, 
    ToolTask, 
    ToolStatus,
    ToolStatusPanel,
    PandaCSVAnalysisTool,
    EnhancedWebSearchTool, 
    EnhancedFileTools, 
    EnhancedDependencyManager,
    with_retry,
    RetryConfig
)

# Theme management
from theme_manager import ThemeManager, ColorScheme
from theme_ui import ThemeCustomizerDialog

class CollapsibleFrame(ttk.Frame):
    """A collapsible frame widget that can expand/collapse its content."""

    def __init__(self, parent, title="", expanded=True, **kwargs):
        super().__init__(parent, **kwargs)

        self.expanded = expanded
        self.title = title

        # Configure style for better visual hierarchy
        self.configure(relief="solid", borderwidth=1)

        # Create header frame with enhanced styling
        self.header_frame = ttk.Frame(self, style="Header.TFrame")
        self.header_frame.pack(fill=tk.X, padx=0, pady=0)

        # Add subtle background to header
        header_bg = ttk.Label(self.header_frame, text="", style="HeaderBG.TLabel")
        header_bg.place(x=0, y=0, relwidth=1, relheight=1)

        # Toggle button (arrow) with enhanced styling
        self.toggle_button = ttk.Button(
            self.header_frame,
            text="▼" if expanded else "▶",
            width=3,
            command=self.toggle,
            style="Toggle.TButton"
        )
        self.toggle_button.pack(side=tk.LEFT, padx=3, pady=2)

        # Title label with enhanced typography
        self.title_label = ttk.Label(
            self.header_frame,
            text=title,
            font=("Segoe UI", 14, "bold"),
            style="SectionTitle.TLabel"
        )
        self.title_label.pack(side=tk.LEFT, padx=(2, 0), pady=2)

        # Content frame with subtle background
        self.content_frame = ttk.Frame(self, style="Content.TFrame")
        if expanded:
            self.content_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=(0, 3))

        # Make header clickable
        self.header_frame.bind("<Button-1>", lambda e: self.toggle())
        self.title_label.bind("<Button-1>", lambda e: self.toggle())
        header_bg.bind("<Button-1>", lambda e: self.toggle())

    def toggle(self):
        """Toggle the expanded/collapsed state."""
        if self.expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self):
        """Expand the content frame."""
        self.expanded = True
        self.toggle_button.config(text="▼")
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

    def collapse(self):
        """Collapse the content frame."""
        self.expanded = False
        self.toggle_button.config(text="▶")
        self.content_frame.pack_forget()

    def add_content(self, widget):
        """Add a widget to the content frame."""
        widget.pack(in_=self.content_frame, fill=tk.X, padx=2, pady=1)
        return widget


class OllamaChat:
    """Main application class for Ollama Chat."""

    def __init__(self, root):
        """Initialize the application and all its components."""
        self.root = root
        self.root.title("Local(o)llama Chat")
        self.root.geometry("1200x800")
        self.root.minsize(800, 400)

        # Initialize theme manager first
        self.theme_manager = ThemeManager()
        self.theme_manager.register_callback(self._on_theme_changed)
        
        # Get current color scheme
        self._apply_color_scheme(self.theme_manager.get_current_scheme())

        # Set up a modern theme
        self.setup_theme()
    
    def _apply_color_scheme(self, scheme: ColorScheme):
        """Apply a color scheme to the application."""
        self.bg_color = scheme.bg_color
        self.fg_color = scheme.fg_color
        self.accent_color = scheme.accent_color
        self.secondary_bg = scheme.secondary_bg
        self.tertiary_bg = scheme.tertiary_bg
        self.subtle_accent = scheme.subtle_accent
        self.success_color = scheme.success_color
        self.error_color = scheme.error_color
        self.warning_color = scheme.warning_color
        self.border_color = scheme.border_color
        self.highlight_color = scheme.highlight_color
        self.cursor_color = scheme.cursor_color
        self.muted_text = scheme.muted_text
        
        # Apply font configuration with validation
        self.font_family = self._validate_font(scheme.font_family, ['Arial', 'Helvetica', 'DejaVu Sans'])
        self.font_size = scheme.font_size
        self.font_family_mono = self._validate_font(scheme.font_family_mono, ['Courier New', 'Courier', 'DejaVu Sans Mono', 'Monospace'])
        self.font_size_mono = scheme.font_size_mono
        self.font_size_chat = scheme.font_size_chat
        self.font_size_input = scheme.font_size_input
        self.font_size_heading = scheme.font_size_heading
        self.font_weight = scheme.font_weight
        self.font_weight_heading = scheme.font_weight_heading
        
        # Store full scheme for markdown rendering
        self.color_scheme = scheme
    
    def _validate_font(self, font_name: str, fallbacks: list) -> str:
        """Validate font availability and return available font or fallback.
        
        Args:
            font_name: The font to check
            fallbacks: List of fallback fonts to try
            
        Returns:
            Available font name
        """
        try:
            # Get list of available fonts
            available_fonts = tkFont.families()
            
            # Normalize font names (case-insensitive on Linux)
            available_fonts_lower = [f.lower() for f in available_fonts]
            
            # Check if requested font is available (case-insensitive)
            if font_name.lower() in available_fonts_lower:
                # Return the actual font name from the system
                idx = available_fonts_lower.index(font_name.lower())
                return available_fonts[idx]
            
            # Try fallbacks
            for fallback in fallbacks:
                if fallback.lower() in available_fonts_lower:
                    print(f"Font '{font_name}' not available, using '{fallback}'")
                    idx = available_fonts_lower.index(fallback.lower())
                    return available_fonts[idx]
            
            # Universal fallbacks that work on most systems
            universal_fallbacks = ['helvetica', 'fixed', 'courier']
            for fallback in universal_fallbacks:
                if fallback in available_fonts_lower:
                    print(f"Font '{font_name}' not available, using '{fallback}' as fallback")
                    idx = available_fonts_lower.index(fallback)
                    return available_fonts[idx]
            
            # Last resort: use tkinter defaults
            print(f"Font '{font_name}' not available, using Tkinter default")
            return 'TkDefaultFont'
        except Exception as e:
            print(f"Error validating font: {e}")
            return 'TkDefaultFont'
    
    def _on_theme_changed(self, scheme: ColorScheme):
        """Callback when theme is changed."""
        self._apply_color_scheme(scheme)
        
        # Re-apply theme to refresh UI
        try:
            self.setup_theme()
            
            # Refresh chat display tags
            if hasattr(self, 'chat_display'):
                self.configure_tags()
            
            # Update all existing widgets recursively
            self._update_all_widgets_theme()
            
            # Show status message
            if hasattr(self, 'display_message'):
                self.display_message("\n✨ Theme updated successfully!\n", "status")
        except Exception as e:
            print(f"Error updating theme: {e}")
    
    def _update_all_widgets_theme(self):
        """Recursively update all widgets with new theme colors."""
        try:
            # Update root window
            self.root.configure(background=self.bg_color)
            
            # Update all tk.Frame widgets
            self._update_widget_colors(self.root)
            
            # Update specific major components
            if hasattr(self, 'chat_display'):
                self.chat_display.configure(
                    background=self.bg_color,
                    foreground=self.fg_color,
                    insertbackground=self.cursor_color,
                    selectbackground=self.subtle_accent,
                    selectforeground="#FFFFFF",
                    font=(self.font_family, self.font_size_chat)
                )
            
            if hasattr(self, 'input_field'):
                self.input_field.configure(
                    background=self.secondary_bg,
                    foreground=self.fg_color,
                    insertbackground=self.cursor_color,
                    selectbackground=self.subtle_accent,
                    selectforeground="#FFFFFF",
                    font=(self.font_family, self.font_size_input)
                )
            
            if hasattr(self, 'status_bar'):
                self.status_bar.configure(
                    background=self.secondary_bg,
                    foreground=self.fg_color
                )
            
            if hasattr(self, 'system_text'):
                self.system_text.configure(
                    background=self.secondary_bg,
                    foreground=self.fg_color,
                    insertbackground=self.cursor_color
                )
            
            # Update listbox widgets
            if hasattr(self, 'conversations_listbox'):
                self.conversations_listbox.configure(
                    background=self.secondary_bg,
                    foreground=self.fg_color,
                    selectbackground=self.subtle_accent,
                    selectforeground="#FFFFFF"
                )
            
            if hasattr(self, 'rag_files_listbox'):
                self.rag_files_listbox.configure(
                    background=self.secondary_bg,
                    foreground=self.fg_color,
                    selectbackground=self.subtle_accent,
                    selectforeground="#FFFFFF"
                )
            
            # Force update
            self.root.update_idletasks()
            
        except Exception as e:
            print(f"Error updating widget colors: {e}")
    
    def _update_widget_colors(self, widget):
        """Recursively update a widget and all its children."""
        try:
            # Update based on widget type
            widget_class = widget.winfo_class()
            
            if widget_class == 'Frame':
                widget.configure(background=self.bg_color)
            elif widget_class == 'Label':
                try:
                    widget.configure(
                        background=self.bg_color,
                        foreground=self.fg_color
                    )
                except tk.TclError:
                    pass  # Some labels may not support all options
            elif widget_class == 'Text':
                try:
                    widget.configure(
                        background=self.bg_color,
                        foreground=self.fg_color,
                        insertbackground=self.cursor_color,
                        selectbackground=self.subtle_accent
                    )
                except tk.TclError:
                    pass
            elif widget_class == 'Listbox':
                try:
                    widget.configure(
                        background=self.secondary_bg,
                        foreground=self.fg_color,
                        selectbackground=self.subtle_accent,
                        selectforeground="#FFFFFF"
                    )
                except tk.TclError:
                    pass
            elif widget_class == 'Canvas':
                try:
                    widget.configure(background=self.bg_color)
                except tk.TclError:
                    pass
            
            # Recursively update children
            for child in widget.winfo_children():
                self._update_widget_colors(child)
                
        except Exception as e:
            # Silently continue if widget doesn't exist or can't be updated
            pass

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
                      font=("Segoe UI", 12))

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
                      font=("Segoe UI", 12, "bold"))  # Bold text for better visibility
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
                      font=("Segoe UI", 12, "bold"))
        style.map("Primary.TButton",
                 background=[("active", self.subtle_accent), ("pressed", self.highlight_color)],
                 foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")],
                 relief=[("pressed", "sunken")])

        # Create an accent button style for active states (like Edit Mode)
        style.configure("Accent.TButton",
                      background=self.warning_color,  # Orange/amber for active state
                      foreground="#FFFFFF",
                      borderwidth=1,
                      relief="flat",
                      padding=(10, 5),
                      font=("Segoe UI", 12, "bold"))
        style.map("Accent.TButton",
                 background=[("active", self.error_color), ("pressed", self.subtle_accent)],
                 foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")],
                 relief=[("pressed", "sunken")])

        # Checkbox styling
        style.configure("TCheckbutton",
                      background=self.bg_color,
                      foreground=self.fg_color,
                      font=("Segoe UI", 12))
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
                      font=("Segoe UI", 12))
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
                      font=("Segoe UI", 14, "bold"))  # Slightly larger font for better readability

        # Enhanced styles for CollapsibleFrame visual hierarchy
        style.configure('Header.TFrame',
                      background=self.secondary_bg,
                      relief="flat",
                      borderwidth=0)
        style.configure('HeaderBG.TLabel',
                      background=self.secondary_bg,
                      relief="flat")
        style.configure('Content.TFrame',
                      background=self.bg_color,
                      relief="flat",
                      borderwidth=0)
        style.configure('SectionTitle.TLabel',
                      background=self.secondary_bg,
                      foreground=self.fg_color,
                      font=("Segoe UI", 12, "bold"))
        style.configure('Toggle.TButton',
                      background=self.secondary_bg,
                      foreground=self.accent_color,
                      borderwidth=0,
                      focuscolor='none',
                      font=("Segoe UI", 10),
                      relief="flat",
                      padding=(2, 1))
        style.map('Toggle.TButton',
                 background=[('active', self.subtle_accent), ('pressed', self.highlight_color)],
                 foreground=[('active', '#FFFFFF'), ('pressed', '#FFFFFF')])

        # Configure root window
        self.root.configure(background=self.bg_color)

        # Set default font to a modern font
        self.root.option_add("*Font", ("Segoe UI", 12))


        # Initialize components
        self.settings = Settings()
        self.conversation_manager = ConversationManager()
        self.prompt_manager = PromptManager()

        # Initialize MCP manager
        self.mcp_manager = MCPManager()
        
        # Enable enhanced MCP features
        if hasattr(self.mcp_manager, 'enable_feature'):
            self.mcp_manager.enable_feature("auto_categorization")
            self.mcp_manager.enable_feature("enhanced_analytics")
            print("🚀 Enhanced MCP features enabled!")
        
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

        # Restore saved geometry if available; otherwise center to 80% of screen
        saved_geom = getattr(self, 'saved_geometry', None)
        saved_max = self.settings.get("window_maximized", False)
        if saved_geom:
            try:
                self.root.geometry(saved_geom)
                if saved_max:
                    self.root.state('zoomed')
            except Exception:
                pass
        else:
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

        # Configure PanedWindow initial sash only once after render
        self._sash_initialized = False
        self.root.after(150, self.configure_paned_window)

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
        self.panda_csv_var = tk.BooleanVar(value=False)  # Always starts disabled

        # Processing control
        self.is_processing = False
        self.active_stream = None
        self.stop_event = threading.Event()
        self.rag_files = []
        self._advanced_web_search_failures = 0  # Counter for advanced web search failures

        # Initialize enhanced tools system
        self.tools_manager = ToolsManager(max_concurrent_tools=3)
        self.tool_status_panel = None  # Will be created after UI is ready
        
        # Enhanced tool instances
        self.enhanced_web_search = EnhancedWebSearchTool(self.tools_manager)
        self.enhanced_file_tools = EnhancedFileTools(self.tools_manager)
        self.enhanced_dependency_manager = EnhancedDependencyManager(self.tools_manager)
        
        # Panda CSV Analysis Tool
        self.panda_csv_tool = PandaCSVAnalysisTool()
        self.panda_csv_preview_prompt = None  # Store prompt during preview
        
        # Tool task tracking
        self.active_tasks = {}  # Maps task_id to description

        # Edit Chat History mode
        self.edit_mode_enabled = False

        # Agent Mode variables
        self.agent_mode_var = tk.BooleanVar(value=self.settings.get("agent_mode_enabled", False))
        self.agent_loop_limit = tk.IntVar(value=self.settings.get("agent_loop_limit", 0))
        self.armed_agents = []  # List of staged agent definitions
        self.active_agent_sequence_name = None  # Current sequence name when loading/saving
        self.configure_agents_button = None  # Will be set when creating sidebar

        # Agent cache and store
        from agent_cache import AgentCache
        from agent_sequence_store import AgentSequenceStore
        self.agent_cache = AgentCache()
        self.agent_store = AgentSequenceStore()

        # Load cached agents if available
        cached_agents = self.agent_cache.load_cached_agents()
        if cached_agents:
            self.armed_agents = cached_agents

        # RAG visualization
        self.rag_visualizer = None

        # Restore saved window/layout settings if available
        self.saved_geometry = self.settings.get("window_geometry", None)
        self.saved_sash_pos = self.settings.get("sash_pos", None)

        # Create tool status panel now that tools_manager is ready
        self.tool_status_panel = ToolStatusPanel(self.root, self.tools_manager)

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
        tools_menu.add_separator()
        tools_menu.add_command(label="Theme Customizer", command=self.show_theme_customizer)

        # Help menu
        help_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="View Help", command=self.show_help_window)

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

        # Models settings frame - using CollapsibleFrame
        model_frame = CollapsibleFrame(self.scrollable_sidebar, title="Models", expanded=True)
        model_frame.pack(fill=tk.X, padx=2, pady=2)

        # Developer selector
        dev_frame = ttk.Frame(model_frame.content_frame)
        dev_frame.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(dev_frame, text="Developer:", font=("Segoe UI", 11)).pack(anchor="w")
        developer_selector = ttk.Combobox(dev_frame, textvariable=self.developer,
                                         values=['ollama', 'google', 'deepseek', 'anthropic'], state='readonly',
                                         font=("Segoe UI", 9))
        developer_selector.pack(fill=tk.X, pady=(2, 0))
        developer_selector.bind('<<ComboboxSelected>>', self.on_developer_changed)

        # LLM Model selector
        llm_frame = ttk.Frame(model_frame.content_frame)
        llm_frame.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(llm_frame, text="LLM Model:", font=("Segoe UI", 9)).pack(anchor="w")
        self.model_selector = ttk.Combobox(llm_frame, state='readonly', font=("Segoe UI", 11))
        self.model_selector.pack(fill=tk.X, pady=(2, 0))
        self.model_selector.bind('<<ComboboxSelected>>', self.on_model_selected)

        # Embedding Model selector
        emb_frame = ttk.Frame(model_frame.content_frame)
        emb_frame.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(emb_frame, text="Embedding:", font=("Segoe UI", 9)).pack(anchor="w")
        self.embedding_selector = ttk.Combobox(emb_frame, state='readonly', font=("Segoe UI", 11))
        self.embedding_selector.pack(fill=tk.X, pady=(2, 0))
        self.embedding_selector.bind('<<ComboboxSelected>>', self.on_embedding_model_selected)

        # Basic Parameters - using CollapsibleFrame
        basic_params_frame = CollapsibleFrame(self.scrollable_sidebar, title="Basic Parameters", expanded=True)
        basic_params_frame.pack(fill=tk.X, padx=2, pady=2)

        # Temperature control
        temp_container = ttk.Frame(basic_params_frame.content_frame)
        temp_container.pack(fill=tk.X, padx=3, pady=3)
        ttk.Label(temp_container, text="Temperature:", font=("Segoe UI", 11)).pack(anchor="w")
        temp_frame = ttk.Frame(temp_container)
        temp_frame.pack(fill=tk.X, pady=(2, 0))

        self.temp_slider = ttk.Scale(
            temp_frame,
            from_=0.0,
            to=2.0,
            orient='horizontal',
            variable=self.temperature,
            command=self.on_temp_change,
            style="Horizontal.TScale"
        )
        self.temp_slider.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.temp_label = ttk.Label(temp_frame, text=f"{self.temperature.get():.2f}", font=("Segoe UI", 10))
        self.temp_label.pack(side=tk.RIGHT, padx=(5, 0))

        # Context size control - discrete values: 2k, 4k, 8k, 16k, 32k, 64k, 128k, 256k, 512k
        context_container = ttk.Frame(basic_params_frame.content_frame)
        context_container.pack(fill=tk.X, padx=3, pady=3)
        ttk.Label(context_container, text="Context Size:", font=("Segoe UI", 9)).pack(anchor="w")
        context_frame = ttk.Frame(context_container)
        context_frame.pack(fill=tk.X, pady=(2, 0))

        # Define discrete context values (in actual token counts)
        self.context_values = [2000, 4000, 8000, 16000, 32000, 64000, 128000, 256000, 512000]
        
        # Find closest position for current context size
        current_context = self.context_size.get()
        closest_pos = 0
        min_diff = abs(self.context_values[0] - current_context)
        for i, val in enumerate(self.context_values):
            diff = abs(val - current_context)
            if diff < min_diff:
                min_diff = diff
                closest_pos = i
        
        # Create a separate variable for slider position
        self.context_position = tk.IntVar(value=closest_pos)

        self.context_slider = ttk.Scale(
            context_frame,
            from_=0,
            to=len(self.context_values)-1,
            orient='horizontal',
            variable=self.context_position,
            command=self.on_context_change,
            style="Horizontal.TScale"
        )
        self.context_slider.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.context_label = ttk.Label(context_frame, text=self.format_context_size(self.context_values[closest_pos]), font=("Segoe UI", 10))
        self.context_label.pack(side=tk.RIGHT, padx=(5, 0))

        # Advanced Parameters - using CollapsibleFrame (collapsed by default)
        advanced_params_frame = CollapsibleFrame(self.scrollable_sidebar, title="Advanced Parameters", expanded=False)
        advanced_params_frame.pack(fill=tk.X, padx=2, pady=2)

        # Top-k control
        top_k_container = ttk.Frame(advanced_params_frame.content_frame)
        top_k_container.pack(fill=tk.X, padx=3, pady=3)
        ttk.Label(top_k_container, text="Top-k (diversity):", font=("Segoe UI", 9)).pack(anchor="w")
        top_k_frame = ttk.Frame(top_k_container)
        top_k_frame.pack(fill=tk.X, pady=(2, 0))

        self.top_k_slider = ttk.Scale(
            top_k_frame,
            from_=1,
            to=50,
            orient='horizontal',
            variable=self.top_k,
            command=self.on_top_k_change,
            style="Horizontal.TScale"
        )
        self.top_k_slider.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.top_k_label = ttk.Label(top_k_frame, text=str(self.top_k.get()), font=("Segoe UI", 10))
        self.top_k_label.pack(side=tk.RIGHT, padx=(5, 0))

        # Top-p control
        top_p_container = ttk.Frame(advanced_params_frame.content_frame)
        top_p_container.pack(fill=tk.X, padx=3, pady=3)
        ttk.Label(top_p_container, text="Top-p (nucleus):", font=("Segoe UI", 10)).pack(anchor="w")
        top_p_frame = ttk.Frame(top_p_container)
        top_p_frame.pack(fill=tk.X, pady=(2, 0))

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
        self.top_p_label = ttk.Label(top_p_frame, text=f"{self.top_p.get():.2f}", font=("Segoe UI", 10))
        self.top_p_label.pack(side=tk.RIGHT, padx=(5, 0))

        # Repeat penalty control
        repeat_penalty_container = ttk.Frame(advanced_params_frame.content_frame)
        repeat_penalty_container.pack(fill=tk.X, padx=3, pady=3)
        ttk.Label(repeat_penalty_container, text="Repeat Penalty:", font=("Segoe UI", 10)).pack(anchor="w")
        repeat_penalty_frame = ttk.Frame(repeat_penalty_container)
        repeat_penalty_frame.pack(fill=tk.X, pady=(2, 0))

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
        self.repeat_penalty_label = ttk.Label(repeat_penalty_frame, text=f"{self.repeat_penalty.get():.2f}", font=("Segoe UI", 10))
        self.repeat_penalty_label.pack(side=tk.RIGHT, padx=(5, 0))

        # Max tokens control - discrete values: 256, 512, 1k, 2k, 4k, 8k...64k
        max_tokens_container = ttk.Frame(advanced_params_frame.content_frame)
        max_tokens_container.pack(fill=tk.X, padx=3, pady=3)
        ttk.Label(max_tokens_container, text="Max Tokens:", font=("Segoe UI", 10)).pack(anchor="w")
        max_tokens_frame = ttk.Frame(max_tokens_container)
        max_tokens_frame.pack(fill=tk.X, pady=(2, 0))

        # Define discrete max tokens values
        self.max_tokens_values = [256, 512, 1000, 2000, 4000, 8000, 16000, 32000, 64000]
        
        # Find closest position for current max tokens
        current_max_tokens = self.max_tokens.get()
        closest_pos = 0
        min_diff = abs(self.max_tokens_values[0] - current_max_tokens)
        for i, val in enumerate(self.max_tokens_values):
            diff = abs(val - current_max_tokens)
            if diff < min_diff:
                min_diff = diff
                closest_pos = i
        
        # Create a separate variable for slider position
        self.max_tokens_position = tk.IntVar(value=closest_pos)

        self.max_tokens_slider = ttk.Scale(
            max_tokens_frame,
            from_=0,
            to=len(self.max_tokens_values)-1,
            orient='horizontal',
            variable=self.max_tokens_position,
            command=self.on_max_tokens_change,
            style="Horizontal.TScale"
        )
        self.max_tokens_slider.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.max_tokens_label = ttk.Label(max_tokens_frame, text=self.format_tokens(self.max_tokens_values[closest_pos]), font=("Segoe UI", 10))
        self.max_tokens_label.pack(side=tk.RIGHT, padx=(5, 0))

        # RAG Settings - using CollapsibleFrame (collapsed by default)
        rag_frame = CollapsibleFrame(self.scrollable_sidebar, title="RAG Settings", expanded=False)
        rag_frame.pack(fill=tk.X, padx=2, pady=2)

        # Chunk size - discrete values: 64, 128, 256, 512, 1k, 2k
        chunk_container = ttk.Frame(rag_frame.content_frame)
        chunk_container.pack(fill=tk.X, padx=3, pady=3)
        ttk.Label(chunk_container, text="Chunk Size:", font=("Segoe UI", 10)).pack(anchor="w")
        chunk_frame = ttk.Frame(chunk_container)
        chunk_frame.pack(fill=tk.X, pady=(2, 0))

        # Define discrete chunk size values
        self.chunk_values = [64, 128, 256, 512, 1000, 2000]
        
        # Find closest position for current chunk size
        current_chunk = self.chunk_size.get()
        closest_pos = 1  # Default to 128
        min_diff = abs(self.chunk_values[1] - current_chunk)
        for i, val in enumerate(self.chunk_values):
            diff = abs(val - current_chunk)
            if diff < min_diff:
                min_diff = diff
                closest_pos = i
        
        # Create a separate variable for slider position
        self.chunk_position = tk.IntVar(value=closest_pos)

        self.chunk_slider = ttk.Scale(
            chunk_frame,
            from_=0,
            to=len(self.chunk_values)-1,
            orient='horizontal',
            variable=self.chunk_position,
            command=self.on_chunk_change,
            style="Horizontal.TScale"
        )
        self.chunk_slider.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.chunk_label = ttk.Label(chunk_frame, text=self.format_chunk_size(self.chunk_values[closest_pos]), font=("Segoe UI", 10))
        self.chunk_label.pack(side=tk.RIGHT, padx=(5, 0))

        # Options - using CollapsibleFrame
        options_frame = CollapsibleFrame(self.scrollable_sidebar, title="Options", expanded=True)
        options_frame.pack(fill=tk.X, padx=2, pady=2)

        # Include chat history
        include_chat_checkbox = ttk.Checkbutton(
            options_frame.content_frame,
            text="Include chat history",
            variable=self.include_chat_var,
            style="TCheckbutton"
        )
        include_chat_checkbox.pack(anchor="w", padx=3, pady=2)

        # Show image preview
        show_image_checkbox = ttk.Checkbutton(
            options_frame.content_frame,
            text="Show image preview",
            variable=self.show_image_var,
            command=self.on_show_image_toggle,
            style="TCheckbutton"
        )
        show_image_checkbox.pack(anchor="w", padx=3, pady=2)

        # Include file content
        self.include_file_checkbox = ttk.Checkbutton(
            options_frame.content_frame,
            text="Include file content",
            variable=self.include_file_var,
            style="TCheckbutton"
        )
        self.include_file_checkbox.pack(anchor="w", padx=3, pady=2)

        # Intelligent file processing
        intelligent_processing_checkbox = ttk.Checkbutton(
            options_frame.content_frame,
            text="Intelligent File Processing?",
            variable=self.intelligent_processing_var,
            command=self.on_intelligent_processing_toggle,
            style="TCheckbutton"
        )
        intelligent_processing_checkbox.pack(anchor="w", padx=3, pady=2)

        # Agent Mode controls (initially hidden behind feature flag)
        if self.settings.get("agent_mode_beta", False):
            # Agent Tool checkbox
            agent_mode_checkbox = ttk.Checkbutton(
                options_frame.content_frame,
                text="Agent Tool",
                variable=self.agent_mode_var,
                command=self.on_agent_mode_toggle,
                style="TCheckbutton"
            )
            agent_mode_checkbox.pack(anchor="w", padx=3, pady=2)

            # Configure Agents button
            self.configure_agents_button = ttk.Button(
                options_frame.content_frame,
                text="Configure Agents",
                command=self.open_configure_agents_window,
                state="disabled"  # Initially disabled
            )
            self.configure_agents_button.pack(anchor="w", padx=3, pady=2, fill="x")

            # Check if we should enable the Configure button based on cached agents
            if len(self.armed_agents) > 0 and not self.agent_mode_var.get():
                self.configure_agents_button.config(state="normal")

        # Tools section - using CollapsibleFrame
        tools_frame = CollapsibleFrame(self.scrollable_sidebar, title="Tools", expanded=True)
        tools_frame.pack(fill=tk.X, padx=2, pady=2)

        # Web Search checkbox
        self.advanced_web_access_var = tk.BooleanVar(value=self.settings.get("advanced_web_access", False))
        advanced_web_access_checkbox = ttk.Checkbutton(
            tools_frame.content_frame,
            text="Web Search",
            variable=self.advanced_web_access_var,
            command=self.on_advanced_web_access_toggle,
            style="TCheckbutton"
        )
        advanced_web_access_checkbox.pack(anchor="w", padx=3, pady=2)

        # Write File checkbox
        write_file_checkbox = ttk.Checkbutton(
            tools_frame.content_frame,
            text="Write File",
            variable=self.write_file_var,
            command=self.on_write_file_toggle,
            style="TCheckbutton"
        )
        write_file_checkbox.pack(anchor="w", padx=3, pady=2)

        # Read File checkbox
        read_file_checkbox = ttk.Checkbutton(
            tools_frame.content_frame,
            text="Read File",
            variable=self.read_file_var,
            command=self.on_read_file_toggle,
            style="TCheckbutton"
        )
        read_file_checkbox.pack(anchor="w", padx=3, pady=2)

        # Truncate File Display checkbox
        truncate_file_display_checkbox = ttk.Checkbutton(
            tools_frame.content_frame,
            text="Truncate file display in chat",
            variable=self.truncate_file_display_var,
            command=self.on_truncate_file_display_toggle,
            style="TCheckbutton"
        )
        truncate_file_display_checkbox.pack(anchor="w", padx=3, pady=2)

        # Panda CSV Analysis Tool checkbox
        panda_csv_checkbox = ttk.Checkbutton(
            tools_frame.content_frame,
            text="Panda CSV Analysis Tool",
            variable=self.panda_csv_var,
            command=self.on_panda_csv_toggle,
            style="TCheckbutton"
        )
        panda_csv_checkbox.pack(anchor="w", padx=3, pady=2)

        # Conversations section - using CollapsibleFrame
        conversations_frame = CollapsibleFrame(self.scrollable_sidebar, title="Conversations", expanded=True)
        conversations_frame.pack(fill=tk.X, padx=2, pady=2)

        # Conversation buttons - arranged in a grid for better space usage
        conv_buttons_frame = ttk.Frame(conversations_frame.content_frame)
        conv_buttons_frame.pack(fill=tk.X, padx=3, pady=3)

        # First row of buttons
        button_row1 = ttk.Frame(conv_buttons_frame)
        button_row1.pack(fill=tk.X, pady=(0, 2))
        ttk.Button(button_row1, text="New", command=self.new_conversation, width=8).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(button_row1, text="Save", command=self.save_conversation, width=8).pack(side=tk.LEFT, padx=2)

        # Second row of buttons
        button_row2 = ttk.Frame(conv_buttons_frame)
        button_row2.pack(fill=tk.X)
        ttk.Button(button_row2, text="Load", command=self.load_conversation, width=8).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(button_row2, text="Prompts", command=self.show_prompt_history, width=8).pack(side=tk.LEFT, padx=2)

        # Recent conversations list
        recent_frame = ttk.Frame(conversations_frame.content_frame)
        recent_frame.pack(fill=tk.X, padx=3, pady=(5, 3))
        ttk.Label(recent_frame, text="Recent:", font=("Segoe UI", 10)).pack(anchor="w")

        self.conversations_listbox = tk.Listbox(
            recent_frame,
            height=4,  # Reduced height to save space
            bg=self.secondary_bg,
            fg=self.fg_color,
            selectbackground=self.subtle_accent,
            selectforeground="#FFFFFF",
            borderwidth=0,
            highlightthickness=1,
            highlightcolor=self.highlight_color,
            highlightbackground=self.border_color,
            font=("Segoe UI", 10)  # Slightly smaller font
        )
        self.conversations_listbox.pack(fill=tk.X, pady=(2, 0))
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

    # Removed responsive spacing and resize handlers to keep sizes consistent
    def on_window_resize(self, event):
        return

    def update_responsive_layout(self):
        return

    def configure_paned_window(self):
        """Configure the PanedWindow initial sash only once for consistent sizing."""
        if getattr(self, '_sash_initialized', False):
            return
        try:
            window_width = self.root.winfo_width()
            if window_width > 100:
                # Use saved sash position if available
                saved_pos = getattr(self, 'saved_sash_pos', None)
                if isinstance(saved_pos, int) and saved_pos > 0:
                    sidebar_width = saved_pos
                else:
                    # Fixed initial sidebar width with sensible min/max
                    sidebar_width = max(280, min(320, int(window_width * 0.24)))

                # Apply minsize constraints to panes for stability
                try:
                    # Set minsize on sidebar and chat panes
                    self.main_frame.paneconfig(self.sidebar_frame, minsize=260)
                    self.main_frame.paneconfig(self.chat_input_frame, minsize=400)
                except Exception:
                    pass

                self.main_frame.sashpos(0, sidebar_width)
                self._sash_initialized = True
        except Exception:
            # Retry once if initialization fails early in render
            self.root.after(150, self.configure_paned_window)

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
            font=("Segoe UI", 12),  # Slightly larger font
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

        # Edit Chat History button (toggles edit mode)
        self.edit_chat_button = ttk.Button(
            button_frame,
            text="Edit Chat History",
            command=self.toggle_edit_mode
        )
        self.edit_chat_button.pack(side=tk.LEFT, padx=2)

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
        self.chat_display.tag_configure('user', foreground=self.accent_color, font=(self.font_family, self.font_size_chat))
        self.chat_display.tag_configure('assistant', foreground=self.success_color, font=(self.font_family, self.font_size_chat))
        self.chat_display.tag_configure('system', foreground=self.subtle_accent, font=(self.font_family, self.font_size_chat))
        self.chat_display.tag_configure('error', foreground=self.error_color, font=(self.font_family, self.font_size_chat))
        self.chat_display.tag_configure('warning', foreground=self.warning_color, font=(self.font_family, self.font_size_chat))
        self.chat_display.tag_configure('status', foreground=self.muted_text, font=(self.font_family, self.font_size_chat))

        # Configure additional tags for rich text formatting with enhanced styling
        self.chat_display.tag_configure('user_label', foreground=self.accent_color, font=(self.font_family, self.font_size_heading, "bold"))
        self.chat_display.tag_configure('assistant_label', foreground=self.success_color, font=(self.font_family, self.font_size_heading, "bold"))
        self.chat_display.tag_configure('warning_label', foreground=self.warning_color, font=(self.font_family, self.font_size_heading, "bold"))
        self.chat_display.tag_configure('system_label', foreground=self.subtle_accent, font=(self.font_family, self.font_size_heading, "bold"))
        self.chat_display.tag_configure('error_label', foreground=self.error_color, font=(self.font_family, self.font_size_heading, "bold"))
        self.chat_display.tag_configure('status_label', foreground=self.muted_text, font=(self.font_family, self.font_size_heading, "bold"))

        # Configure file preview tags with enhanced colors
        self.chat_display.tag_configure('file_label', foreground=self.highlight_color, font=(self.font_family, self.font_size_heading, "bold"))
        self.chat_display.tag_configure('file_info', foreground=self.subtle_accent, font=(self.font_family, self.font_size_chat))

        # Configure link tag for clickable links with enhanced styling
        self.chat_display.tag_configure('link', foreground=self.highlight_color, underline=1, font=(self.font_family, self.font_size_chat))
        self.chat_display.tag_bind('link', '<Button-1>', lambda e: self.open_url_from_text())
        
        # Configure code block tags for enhanced markdown support
        self.chat_display.tag_configure('code',
            background='#0D0E14',  # Dark code background
            foreground='#E0E0E0',  # Light text
            font=(self.font_family_mono, self.font_size_mono),
            spacing1=4,
            spacing3=4,
            lmargin1=10,
            lmargin2=10,
            rmargin=10)
        
        self.chat_display.tag_configure('code_language',
            foreground=self.warning_color,
            font=(self.font_family_mono, self.font_size_mono, 'bold'))

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
    
    def show_theme_customizer(self):
        """Show the theme customizer dialog."""
        try:
            dialog = ThemeCustomizerDialog(self.root, self.theme_manager)
            dialog.show()
        except Exception as e:
            self.display_message(f"\\nError opening theme customizer: {str(e)}\\n", "error")
            error_handler.handle_error(e, "Theme Customizer")

    def show_help_window(self):
        """Show the comprehensive help documentation window."""
        # Create help window
        help_window = tk.Toplevel(self.root)
        help_window.title("Local(o)llama Chatbot - Help & Documentation")
        help_window.geometry("1200x800")
        help_window.minsize(900, 600)
        help_window.configure(background=self.bg_color)
        
        # Load HELP.md content
        help_file_path = os.path.join(os.path.dirname(__file__), 'HELP.md')
        try:
            with open(help_file_path, 'r', encoding='utf-8') as f:
                help_content = f.read()
        except FileNotFoundError:
            messagebox.showerror("Help File Not Found", 
                                "HELP.md file not found. Please ensure it exists in the application directory.")
            help_window.destroy()
            return
        except Exception as e:
            messagebox.showerror("Error Loading Help", 
                                f"Error loading help file: {e}")
            help_window.destroy()
            return
        
        # Parse table of contents
        toc_sections = self._extract_toc_from_markdown(help_content)
        
        # Create PanedWindow for two-panel layout
        paned_window = ttk.PanedWindow(help_window, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel: Table of Contents
        toc_frame = ttk.Frame(paned_window, relief=tk.SOLID, borderwidth=1)
        paned_window.add(toc_frame, weight=1)
        
        # TOC header
        toc_header = ttk.Label(toc_frame, text="Table of Contents", 
                               font=('Segoe UI', 12, 'bold'),
                               foreground=self.highlight_color,
                               background=self.bg_color)
        toc_header.pack(fill=tk.X, padx=10, pady=10)
        
        # TOC list with scrollbar
        toc_scroll_frame = ttk.Frame(toc_frame)
        toc_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        toc_scrollbar = ttk.Scrollbar(toc_scroll_frame)
        toc_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        toc_listbox = tk.Listbox(
            toc_scroll_frame,
            yscrollcommand=toc_scrollbar.set,
            bg=self.secondary_bg,
            fg=self.fg_color,
            selectbackground=self.highlight_color,
            selectforeground=self.bg_color,
            font=('Segoe UI', 10),
            relief=tk.FLAT,
            highlightthickness=0,
            activestyle='none',
            cursor='hand2'
        )
        toc_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        toc_scrollbar.config(command=toc_listbox.yview)
        
        # Populate TOC
        for section in toc_sections:
            indent = '  ' * (section['level'] - 1)
            display_text = f"{indent}{section['title']}"
            toc_listbox.insert(tk.END, display_text)
        
        # Right panel: Content viewer
        content_frame = ttk.Frame(paned_window, relief=tk.SOLID, borderwidth=1)
        paned_window.add(content_frame, weight=3)
        
        # Content text widget with scrollbar
        content_scroll_frame = ttk.Frame(content_frame)
        content_scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        content_scrollbar = ttk.Scrollbar(content_scroll_frame)
        content_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        content_text = tk.Text(
            content_scroll_frame,
            yscrollcommand=content_scrollbar.set,
            wrap=tk.WORD,
            bg=self.bg_color,
            fg=self.fg_color,
            font=('Segoe UI', 10),
            relief=tk.FLAT,
            padx=15,
            pady=15,
            highlightthickness=0,
            cursor='',
            state='disabled'
        )
        content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        content_scrollbar.config(command=content_text.yview)
        
        # Render initial content
        self.parse_markdown_to_text_widget(content_text, help_content, 
                                          lambda url: self._navigate_help_section(url, content_text, help_content, toc_sections, toc_listbox))
        
        # TOC click handler
        def on_toc_click(event):
            selection = toc_listbox.curselection()
            if selection:
                index = selection[0]
                section = toc_sections[index]
                self._scroll_to_section(content_text, help_content, section['anchor'])
        
        toc_listbox.bind('<<ListboxSelect>>', on_toc_click)
        
        # Enable mousewheel scrolling for content
        def on_content_mousewheel(event):
            content_text.yview_scroll(int(-1 * (event.delta / 120)), "units")
        content_text.bind("<MouseWheel>", on_content_mousewheel)
    
    def _extract_toc_from_markdown(self, markdown_content):
        """Extract table of contents sections from markdown content."""
        sections = []
        lines = markdown_content.split('\n')
        
        for line in lines:
            # Match markdown headers (## or ### at start of line)
            if line.startswith('##') and not line.startswith('###'):
                # Level 2 header
                title = line.strip('#').strip()
                # Create anchor from title (lowercase, replace spaces with hyphens)
                anchor = title.lower().replace(' ', '-').replace('&', '').replace('(', '').replace(')', '').replace(',', '').replace('.', '')
                sections.append({
                    'title': title,
                    'anchor': anchor,
                    'level': 2
                })
            elif line.startswith('###') and not line.startswith('####'):
                # Level 3 header (sub-sections) - optional, can be added if needed
                title = line.strip('#').strip()
                anchor = title.lower().replace(' ', '-').replace('&', '').replace('(', '').replace(')', '').replace(',', '').replace('.', '')
                sections.append({
                    'title': title,
                    'anchor': anchor,
                    'level': 3
                })
        
        return sections
    
    def _scroll_to_section(self, text_widget, markdown_content, anchor):
        """Scroll to a specific section in the help content."""
        # Find the section by searching for the header text
        lines = markdown_content.split('\n')
        line_number = 0
        
        for i, line in enumerate(lines):
            if line.startswith('#'):
                # Extract title from header
                title = line.strip('#').strip()
                line_anchor = title.lower().replace(' ', '-').replace('&', '').replace('(', '').replace(')', '').replace(',', '').replace('.', '')
                if line_anchor == anchor:
                    line_number = i
                    break
        
        # Calculate approximate text position
        # Each line in markdown roughly corresponds to a line in the Text widget
        text_widget.see(f'{line_number + 1}.0')
        text_widget.mark_set('insert', f'{line_number + 1}.0')
    
    def _navigate_help_section(self, url, content_text, help_content, toc_sections, toc_listbox):
        """Navigate to a section from a markdown link."""
        # Internal links start with #
        if url.startswith('#'):
            anchor = url[1:]  # Remove the #
            self._scroll_to_section(content_text, help_content, anchor)
            
            # Highlight corresponding TOC item
            for i, section in enumerate(toc_sections):
                if section['anchor'] == anchor:
                    toc_listbox.selection_clear(0, tk.END)
                    toc_listbox.selection_set(i)
                    toc_listbox.see(i)
                    break
        else:
            # External link - open in browser
            try:
                webbrowser.open(url)
            except Exception as e:
                messagebox.showerror("Error", f"Could not open URL: {e}")

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

        # Apply agent mode settings
        self.agent_mode_var.set(self.settings.get("agent_mode_enabled", False))
        self.agent_loop_limit.set(self.settings.get("agent_loop_limit", 0))

        # Set up agent mode variable traces to save settings when changed
        self.agent_mode_var.trace_add("write", self.save_agent_settings)
        self.agent_loop_limit.trace_add("write", self.save_agent_settings)

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

    def save_agent_settings(self, *args):
        """Save agent mode settings when they change."""
        try:
            self.settings.set("agent_mode_enabled", self.agent_mode_var.get())
            self.settings.set("agent_loop_limit", self.agent_loop_limit.get())
            self.settings.save_settings()
        except Exception as e:
            print(f"Error saving agent settings: {e}")

    def on_agent_mode_toggle(self):
        """Handle Agent Mode checkbox toggle."""
        try:
            is_enabled = self.agent_mode_var.get()

            if is_enabled:
                # Agent Mode turned ON - start staging
                self.display_message("\nAgent Sequence: Begin\n", 'status')
                self.armed_agents = []  # Clear any existing agents
                self.active_agent_sequence_name = None

                # Disable Configure button while staging
                if hasattr(self, 'configure_agents_button') and self.configure_agents_button:
                    self.configure_agents_button.config(state="disabled")

                # Clear cache
                self.agent_cache.clear_agent_cache()

            else:
                # Agent Mode turned OFF - finish staging
                if len(self.armed_agents) > 0:
                    # Save staged agents to cache
                    self.agent_cache.save_agents_to_cache(self.armed_agents)

                    # Show completion message
                    agent_count = len(self.armed_agents)
                    self.display_message(f"\n{agent_count} Agents Defined. View Configuration Window to Begin...\n", 'status')

                    # Enable Configure button
                    if hasattr(self, 'configure_agents_button') and self.configure_agents_button:
                        self.configure_agents_button.config(state="normal")
                else:
                    # No agents staged - just return to normal
                    self.display_message("\nAgent Mode disabled. No agents were staged.\n", 'status')

                    # Keep Configure button disabled
                    if hasattr(self, 'configure_agents_button') and self.configure_agents_button:
                        self.configure_agents_button.config(state="disabled")

            # Save the setting
            self.save_agent_settings()

        except Exception as e:
            self.display_message(f"\nError toggling Agent Mode: {e}\n", 'error')

    def open_configure_agents_window(self):
        """Open the Configure Agents window."""
        try:
            # Create the configuration window
            config_window = tk.Toplevel(self.root)
            config_window.title("Configure Agent Sequence")
            config_window.geometry("800x600")
            config_window.minsize(600, 400)

            # Make it modal
            config_window.transient(self.root)
            config_window.grab_set()

            # Center the window
            config_window.update_idletasks()
            x = (config_window.winfo_screenwidth() // 2) - (800 // 2)
            y = (config_window.winfo_screenheight() // 2) - (600 // 2)
            config_window.geometry(f"800x600+{x}+{y}")

            # Create main frame
            main_frame = ttk.Frame(config_window, padding="10")
            main_frame.pack(fill=tk.BOTH, expand=True)

            # Title
            title_label = ttk.Label(main_frame, text="Agent Sequence Configuration",
                                  font=("Arial", 14, "bold"))
            title_label.pack(pady=(0, 10))

            # Loop limit control
            loop_frame = ttk.Frame(main_frame)
            loop_frame.pack(fill=tk.X, pady=(0, 10))

            ttk.Label(loop_frame, text="Loop Limit:").pack(side=tk.LEFT)
            loop_spinbox = ttk.Spinbox(loop_frame, from_=0, to=10, width=5,
                                     textvariable=self.agent_loop_limit)
            loop_spinbox.pack(side=tk.LEFT, padx=(5, 0))
            ttk.Label(loop_frame, text="(0 = no loops allowed)").pack(side=tk.LEFT, padx=(5, 0))

            # Agent list frame
            list_frame = ttk.LabelFrame(main_frame, text="Staged Agents", padding="5")
            list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

            # Create container for listbox and buttons
            list_main_container = ttk.Frame(list_frame)
            list_main_container.pack(fill=tk.BOTH, expand=True)

            # Create listbox with scrollbar
            list_container = ttk.Frame(list_main_container)
            list_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            agent_listbox = tk.Listbox(list_container, font=("Consolas", 10))
            scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=agent_listbox.yview)
            agent_listbox.config(yscrollcommand=scrollbar.set)

            agent_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # Reorder buttons
            reorder_frame = ttk.Frame(list_main_container)
            reorder_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))

            up_btn = ttk.Button(reorder_frame, text="↑", width=3,
                              command=lambda: self.move_agent_up(agent_listbox))
            up_btn.pack(pady=(0, 2))

            down_btn = ttk.Button(reorder_frame, text="↓", width=3,
                                command=lambda: self.move_agent_down(agent_listbox))
            down_btn.pack(pady=(0, 2))

            delete_btn = ttk.Button(reorder_frame, text="✕", width=3,
                                  command=lambda: self.delete_agent(agent_listbox))
            delete_btn.pack(pady=(10, 2))

            edit_btn = ttk.Button(reorder_frame, text="✎", width=3,
                                command=lambda: self.edit_agent(agent_listbox, config_window))
            edit_btn.pack(pady=(0, 2))

            # Populate agent list
            self.populate_agent_list(agent_listbox)

            # Preview frame
            preview_frame = ttk.LabelFrame(main_frame, text="Agent Preview", padding="5")
            preview_frame.pack(fill=tk.X, pady=(0, 10))

            preview_text = tk.Text(preview_frame, height=8, font=("Consolas", 10),
                                 wrap=tk.WORD, state=tk.DISABLED)
            preview_scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=preview_text.yview)
            preview_text.config(yscrollcommand=preview_scrollbar.set)

            preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # Bind selection event
            def on_agent_select(event):
                selection = agent_listbox.curselection()
                if selection:
                    idx = selection[0]
                    if idx < len(self.armed_agents):
                        self.show_agent_preview(preview_text, self.armed_agents[idx])

            agent_listbox.bind('<<ListboxSelect>>', on_agent_select)

            # Button frame
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X)

            # Load button
            load_btn = ttk.Button(button_frame, text="Load Sequence",
                                command=lambda: self.load_agent_sequence_dialog(config_window, agent_listbox))
            load_btn.pack(side=tk.LEFT, padx=(0, 5))

            # Save button
            save_btn = ttk.Button(button_frame, text="Save Sequence",
                                command=lambda: self.save_agent_sequence_dialog(config_window))
            save_btn.pack(side=tk.LEFT, padx=(0, 5))

            # Run button
            run_btn = ttk.Button(button_frame, text="Run Sequence",
                               command=lambda: self.run_agent_sequence_from_config(config_window),
                               style="Accent.TButton")
            run_btn.pack(side=tk.RIGHT)

            # Enable/disable run button based on agent count
            if len(self.armed_agents) == 0:
                run_btn.config(state="disabled")

            # Show initial preview if agents exist
            if len(self.armed_agents) > 0:
                agent_listbox.selection_set(0)
                self.show_agent_preview(preview_text, self.armed_agents[0])

        except Exception as e:
            self.display_message(f"\nError opening Configure Agents window: {e}\n", 'error')

    def stage_agent(self, user_input):
        """Stage an agent definition when Agent Mode is active."""
        try:
            from agent_cache import create_agent_definition

            # Check maximum agent limit
            max_agents = self.settings.get("agent_max_count", 999)
            if len(self.armed_agents) >= max_agents:
                self.display_message(f"\nMaximum agent limit ({max_agents}) reached. Cannot stage more agents.\n", 'error')
                return

            # Generate agent title
            agent_count = len(self.armed_agents) + 1
            agent_title = f"Agent-{agent_count}"

            # Capture current system prompt
            system_prompt = self.system_text.get("1.0", tk.END).strip()
            if not system_prompt:
                system_prompt = "You are a helpful assistant."

            # Capture current model and developer
            current_model = self.model_selector.get() if hasattr(self, 'model_selector') else ""
            current_developer = self.developer.get() if hasattr(self, 'developer') else "ollama"

            # Create messages list
            messages = [{"role": "user", "content": user_input}]

            # Capture current parameters
            parameters = {
                "temperature": self.temperature.get(),
                "top_p": self.top_p.get(),
                "top_k": self.top_k.get(),
                "repeat_penalty": self.repeat_penalty.get(),
                "max_tokens": self.max_tokens.get(),
                "context_size": self.context_size.get(),
                "include_chat": self.include_chat_var.get(),
                "include_file": self.include_file_var.get(),
            }

            # Capture current tool settings
            tools = {
                "web_access": getattr(self, 'advanced_web_access_var', tk.BooleanVar()).get(),
                "write_file": self.write_file_var.get(),
                "read_file": self.read_file_var.get(),
                "intelligent_processing": self.intelligent_processing_var.get(),
            }

            # Capture file attachments if any
            file_attachments = []
            if hasattr(self, 'file_content') and self.file_content:
                file_attachments.append({
                    "content": self.file_content,
                    "type": getattr(self, 'file_type', 'text'),
                    "path": getattr(self, 'current_file_path', 'unknown')
                })

            # Capture RAG files if any
            rag_file_list = []
            if hasattr(self, 'rag_files') and self.rag_files:
                rag_file_list = [str(f) for f in self.rag_files]

            # Create metadata
            metadata = {
                "index": agent_count,
                "file_attachments": file_attachments,
                "rag_files": rag_file_list,
                "references": []  # Will be populated later if needed
            }

            # Create agent definition
            agent_def = create_agent_definition(
                title=agent_title,
                model=current_model,
                developer=current_developer,
                system=system_prompt,
                messages=messages,
                parameters=parameters,
                tools=tools,
                metadata=metadata
            )

            # Add to armed agents list
            self.armed_agents.append(agent_def)

            # Save to cache
            self.agent_cache.save_agents_to_cache(self.armed_agents)

            # Show feedback
            ordinal_names = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth"]
            if agent_count <= len(ordinal_names):
                ordinal = ordinal_names[agent_count - 1]
            else:
                ordinal = f"{agent_count}th"

            self.display_message(f"\n{ordinal} Agent Defined\n", 'status')

            # Clear input field
            self.input_field.delete("1.0", tk.END)
            self.input_field.insert("1.0", "Type your message here...")
            self.input_placeholder_visible = True

            # Update status bar if it exists
            if hasattr(self, 'status_bar'):
                self.status_bar.config(text=f"Defining Agent {agent_count + 1}...")

        except Exception as e:
            self.display_message(f"\nError staging agent: {e}\n", 'error')

    def populate_agent_list(self, listbox):
        """Populate the agent listbox with current agents."""
        listbox.delete(0, tk.END)
        for i, agent in enumerate(self.armed_agents):
            title = agent.get('title', f'Agent-{i+1}')
            model = agent.get('model', 'Unknown')
            developer = agent.get('developer', 'Unknown')
            message_count = len(agent.get('messages', []))

            display_text = f"{title} | {developer}:{model} | {message_count} msg(s)"
            listbox.insert(tk.END, display_text)

    def show_agent_preview(self, text_widget, agent):
        """Show agent details in the preview text widget."""
        text_widget.config(state=tk.NORMAL)
        text_widget.delete(1.0, tk.END)

        # Format agent information
        preview = f"Title: {agent.get('title', 'Unknown')}\n"
        preview += f"Model: {agent.get('model', 'Unknown')}\n"
        preview += f"Developer: {agent.get('developer', 'Unknown')}\n"
        preview += f"System: {agent.get('system', 'None')[:100]}...\n\n"

        # Show messages
        messages = agent.get('messages', [])
        preview += f"Messages ({len(messages)}):\n"
        for i, msg in enumerate(messages):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:200]
            preview += f"  {i+1}. {role}: {content}...\n"

        # Show parameters
        params = agent.get('parameters', {})
        preview += f"\nParameters:\n"
        for key, value in params.items():
            preview += f"  {key}: {value}\n"

        # Show tools
        tools = agent.get('tools', {})
        enabled_tools = [k for k, v in tools.items() if v]
        preview += f"\nEnabled Tools: {', '.join(enabled_tools) if enabled_tools else 'None'}\n"

        text_widget.insert(1.0, preview)
        text_widget.config(state=tk.DISABLED)

    def load_agent_sequence_dialog(self, parent_window, listbox):
        """Show dialog to load an agent sequence."""
        try:
            sequences = self.agent_store.list_agent_sequences()
            if not sequences:
                tk.messagebox.showinfo("No Sequences", "No saved agent sequences found.", parent=parent_window)
                return

            # Create selection dialog
            dialog = tk.Toplevel(parent_window)
            dialog.title("Load Agent Sequence")
            dialog.geometry("500x300")
            dialog.transient(parent_window)
            dialog.grab_set()

            # Center dialog
            dialog.update_idletasks()
            x = parent_window.winfo_x() + (parent_window.winfo_width() // 2) - 250
            y = parent_window.winfo_y() + (parent_window.winfo_height() // 2) - 150
            dialog.geometry(f"500x300+{x}+{y}")

            # Create listbox for sequences
            frame = ttk.Frame(dialog, padding="10")
            frame.pack(fill=tk.BOTH, expand=True)

            ttk.Label(frame, text="Select a sequence to load:").pack(anchor="w")

            seq_listbox = tk.Listbox(frame, font=("Consolas", 10))
            seq_scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=seq_listbox.yview)
            seq_listbox.config(yscrollcommand=seq_scrollbar.set)

            seq_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(5, 10))
            seq_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=(5, 10))

            # Populate sequences
            for title, metadata in sequences:
                agent_count = metadata.get('agent_count', 0)
                last_updated = metadata.get('last_updated', 'Unknown')[:10]  # Just date part
                display_text = f"{title} ({agent_count} agents) - {last_updated}"
                seq_listbox.insert(tk.END, display_text)

            # Buttons
            btn_frame = ttk.Frame(frame)
            btn_frame.pack(fill=tk.X)

            def load_selected():
                selection = seq_listbox.curselection()
                if selection:
                    idx = selection[0]
                    title = sequences[idx][0]
                    sequence = self.agent_store.load_agent_sequence(title)
                    if sequence:
                        self.armed_agents = sequence.agents
                        self.agent_loop_limit.set(sequence.loop_limit)
                        self.active_agent_sequence_name = sequence.title

                        # Update cache
                        self.agent_cache.save_agents_to_cache(self.armed_agents)

                        # Refresh the main listbox
                        self.populate_agent_list(listbox)

                        self.display_message(f"\nLoaded sequence '{title}' ({len(sequence.agents)} agents)\n", 'status')
                        dialog.destroy()
                    else:
                        tk.messagebox.showerror("Error", f"Failed to load sequence '{title}'", parent=dialog)

            ttk.Button(btn_frame, text="Load", command=load_selected).pack(side=tk.LEFT)
            ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)

        except Exception as e:
            self.display_message(f"\nError loading sequence: {e}\n", 'error')

    def save_agent_sequence_dialog(self, parent_window):
        """Show dialog to save the current agent sequence."""
        try:
            if not self.armed_agents:
                tk.messagebox.showwarning("No Agents", "No agents to save.", parent=parent_window)
                return

            # Get title from user
            title = tk.simpledialog.askstring(
                "Save Agent Sequence",
                "Enter a name for this agent sequence:",
                parent=parent_window,
                initialvalue=self.active_agent_sequence_name or "My Agent Sequence"
            )

            if title:
                from agent_sequence_store import AgentSequence

                # Create sequence object
                sequence = AgentSequence(
                    title=title,
                    agents=self.armed_agents,
                    loop_limit=self.agent_loop_limit.get()
                )

                # Save to store
                if self.agent_store.save_agent_sequence(sequence):
                    self.active_agent_sequence_name = title
                    self.display_message(f"\nSaved agent sequence '{title}' ({len(self.armed_agents)} agents)\n", 'status')
                else:
                    tk.messagebox.showerror("Save Error", f"Failed to save sequence '{title}'", parent=parent_window)

        except Exception as e:
            self.display_message(f"\nError saving sequence: {e}\n", 'error')

    def run_agent_sequence_from_config(self, config_window):
        """Run the agent sequence from the configuration window."""
        try:
            if not self.armed_agents:
                tk.messagebox.showwarning("No Agents", "No agents to run.", parent=config_window)
                return

            # Auto-save if we have a name
            if self.active_agent_sequence_name:
                from agent_sequence_store import AgentSequence
                sequence = AgentSequence(
                    title=self.active_agent_sequence_name,
                    agents=self.armed_agents,
                    loop_limit=self.agent_loop_limit.get()
                )
                self.agent_store.save_agent_sequence(sequence)

            # Close config window
            config_window.destroy()

            # Start agent sequence execution
            self.display_message(f"\nStarting agent sequence with {len(self.armed_agents)} agents...\n", 'status')

            # Disable controls during execution
            self.agent_mode_var.set(False)  # Turn off agent mode
            if hasattr(self, 'configure_agents_button') and self.configure_agents_button:
                self.configure_agents_button.config(state="disabled")

            # Run sequence in background thread
            import threading
            execution_thread = threading.Thread(target=self._run_agent_sequence, daemon=True)
            execution_thread.start()

        except Exception as e:
            self.display_message(f"\nError running sequence: {e}\n", 'error')

    def _run_agent_sequence(self):
        """Execute the agent sequence in background thread with branching support."""
        try:
            resolved_outputs = {}  # Store outputs from completed agents
            loop_count = 0
            max_loops = self.agent_loop_limit.get()
            visited_agents = set()  # Track visited agents for loop detection

            # Use index-based iteration to allow jumping
            current_index = 0

            while current_index < len(self.armed_agents):
                try:
                    agent = self.armed_agents[current_index]
                    agent_title = agent.get('title', f'Agent-{current_index+1}')

                    # Check for infinite loops
                    agent_key = f"{agent_title}_{current_index}"
                    if agent_key in visited_agents and loop_count >= max_loops:
                        self.root.after(0, lambda: self.display_message(f"\nLoop limit reached for {agent_title}\n", 'status'))
                        break

                    visited_agents.add(agent_key)

                    # Update status
                    self.root.after(0, lambda t=agent_title: self.display_message(f"\nExecuting {t}...\n", 'status'))

                    print(f"Debug: About to execute {agent_title}")

                    # Execute the agent
                    result = self._execute_single_agent(agent, resolved_outputs)

                    print(f"Debug: {agent_title} execution completed, result length: {len(str(result))}")

                    # Store result for future agents
                    resolved_outputs[agent_title] = result

                    # Check for branching directives in the result
                    next_index = self._check_branching_directives(result, current_index)

                    if next_index != current_index + 1:
                        # Branching occurred
                        loop_count += 1
                        if loop_count > max_loops:
                            self.root.after(0, lambda: self.display_message(f"\nBranch limit reached, continuing linearly\n", 'status'))
                            current_index += 1
                        else:
                            current_index = next_index
                            self.root.after(0, lambda t=agent_title, ni=next_index:
                                          self.display_message(f"{t} branching to Agent-{ni+1}\n", 'status'))
                    else:
                        # Normal progression
                        current_index += 1

                    # Update completion status
                    self.root.after(0, lambda t=agent_title: self.display_message(f"{t} Task Complete\n", 'status'))

                except Exception as e:
                    error_msg = f"Agent {agent.get('title', f'Agent-{current_index+1}')} failed: {str(e)}"
                    self.root.after(0, lambda msg=error_msg: self.display_message(f"\n{msg}\n", 'error'))
                    break

            # Completion message
            self.root.after(0, lambda: self.display_message("\nAll Agents Finished\n", 'status'))

        except Exception as e:
            error_msg = f"Agent sequence execution failed: {str(e)}"
            self.root.after(0, lambda msg=error_msg: self.display_message(f"\n{msg}\n", 'error'))

        finally:
            # Re-enable controls
            self.root.after(0, self._re_enable_agent_controls)

    def _check_branching_directives(self, result, current_index):
        """Check for branching directives in agent output."""
        import re

        # Look for PROCEED: Agent-X or RETRY: Agent-X patterns
        proceed_match = re.search(r'PROCEED:\s*Agent-(\d+)', result, re.IGNORECASE)
        retry_match = re.search(r'RETRY:\s*Agent-(\d+)', result, re.IGNORECASE)

        if proceed_match:
            target_agent = int(proceed_match.group(1)) - 1  # Convert to 0-based index
            if 0 <= target_agent < len(self.armed_agents):
                return target_agent

        if retry_match:
            target_agent = int(retry_match.group(1)) - 1  # Convert to 0-based index
            if 0 <= target_agent < len(self.armed_agents):
                return target_agent

        # No branching directive found, proceed normally
        return current_index + 1

    def _execute_single_agent(self, agent, resolved_outputs):
        """Execute a single agent and return its result."""
        try:
            agent_title = agent.get('title', 'Unknown')
            print(f"Debug: Starting execution of {agent_title}")

            # Set up the model manager for this agent
            developer = agent.get('developer', 'ollama')
            model = agent.get('model', '')

            print(f"Debug: {agent_title} - Developer: {developer}, Model: {model}")

            # Validate model is specified
            if not model:
                error_msg = f"Error: No model specified for agent {agent_title}"
                print(f"Debug: {error_msg}")
                return error_msg

            # Create appropriate model manager
            from models_manager import create_model_manager
            agent_model_manager = create_model_manager(developer)

            print(f"Debug: {agent_title} - Model manager created: {type(agent_model_manager)}")

            # Validate model manager was created successfully
            if not agent_model_manager:
                error_msg = f"Error: Could not create model manager for {developer}"
                print(f"Debug: {error_msg}")
                return error_msg

            # Prepare the message
            messages = agent.get('messages', [])
            if not messages:
                return "No message to process"

            user_message = messages[0].get('content', '')

            # Resolve placeholders in the message
            resolved_message = self._resolve_placeholders(user_message, resolved_outputs)

            # Get tool settings from agent definition
            tools = agent.get('tools', {})
            
            # Process Read File requests if tool is enabled
            if tools.get('read_file', False):
                try:
                    resolved_message = self.process_file_read_requests_sync(resolved_message)
                    if resolved_message != user_message:
                        self.root.after(0, lambda t=agent_title: 
                            self.display_message(f"[{t}] File read operations completed\n", 'status'))
                except Exception as e:
                    self.root.after(0, lambda t=agent_title, err=str(e): 
                        self.display_message(f"[{t}] File read error: {err}\n", 'error'))

            # Process Web Search if tool is enabled
            if tools.get('web_access', False):
                try:
                    self.root.after(0, lambda t=agent_title: 
                        self.display_message(f"[{t}] Searching the web...\n", 'status'))
                    
                    search_results = self.perform_advanced_web_search_sync(resolved_message)
                    if search_results:
                        resolved_message += f"\n\nWeb search results:\n{search_results}"
                        self.root.after(0, lambda t=agent_title: 
                            self.display_message(f"[{t}] Web search completed\n", 'status'))
                    else:
                        self.root.after(0, lambda t=agent_title: 
                            self.display_message(f"[{t}] No web results found\n", 'status'))
                except Exception as e:
                    self.root.after(0, lambda t=agent_title, err=str(e): 
                        self.display_message(f"[{t}] Web search error: {err}\n", 'error'))

            # Prepare system prompt
            system_prompt = agent.get('system', 'You are a helpful assistant.')

            # Prepare parameters
            parameters = agent.get('parameters', {})

            # Build the conversation context
            conversation = []

            # Add system message
            if system_prompt:
                conversation.append({"role": "system", "content": system_prompt})

            # Add resolved user message
            conversation.append({"role": "user", "content": resolved_message})

            # Get response from the model (using same parameters as regular send_message)
            try:
                response_generator = agent_model_manager.get_response(
                    messages=conversation,
                    model=model,
                    temperature=parameters.get('temperature', 0.7),
                    context_size=parameters.get('context_size', 8000),  # Added missing context_size
                    top_k=parameters.get('top_k', 20),
                    top_p=parameters.get('top_p', 0.9),
                    repeat_penalty=parameters.get('repeat_penalty', 1.1),
                    max_tokens=parameters.get('max_tokens', 2048)
                )
            except Exception as e:
                return f"Error calling model manager: {str(e)}"

            # Handle streaming response - collect all chunks
            if hasattr(response_generator, '__iter__') and not isinstance(response_generator, str):
                # It's a generator/iterator - collect all chunks
                response_chunks = []
                chunk_count = 0
                try:
                    for chunk in response_generator:
                        chunk_count += 1

                        # Handle the standard format: {'message': {'content': 'text'}}
                        if chunk and 'message' in chunk and 'content' in chunk['message']:
                            content = chunk['message']['content']
                            if content:
                                response_chunks.append(content)

                        # Handle direct string chunks
                        elif isinstance(chunk, str):
                            response_chunks.append(chunk)

                        # Handle other possible formats
                        elif hasattr(chunk, 'get'):
                            # Try different possible content fields
                            content = None
                            if 'content' in chunk:
                                content = chunk.get('content', '')
                            elif 'text' in chunk:
                                content = chunk.get('text', '')
                            elif 'response' in chunk:
                                content = chunk.get('response', '')

                            if content:
                                response_chunks.append(str(content))

                    response = ''.join(response_chunks)
                    print(f"Debug: Agent {agent_title} - Collected {chunk_count} chunks, total length: {len(response)}")

                except Exception as e:
                    response = f"Error processing streaming response: {str(e)}"
                    print(f"Debug: Streaming error for {agent_title}: {e}")
            else:
                # It's already a string
                response = str(response_generator)
                print(f"Debug: Agent {agent_title} - Direct response length: {len(response)}")

            # Ensure we have a valid response
            if not response or response.strip() == "":
                response = f"No response generated (model: {model}, developer: {developer})"
                print(f"Debug: Empty response for {agent_title} - model: {model}, developer: {developer}")

            # Process Write File requests if tool is enabled
            if tools.get('write_file', False):
                try:
                    self.root.after(0, lambda t=agent_title: 
                        self.display_message(f"[{t}] Checking for file write requests...\n", 'status'))
                    
                    files_written = self.process_file_write_requests(response)
                    if files_written > 0:
                        self.root.after(0, lambda t=agent_title, count=files_written: 
                            self.display_message(f"[{t}] {count} file(s) written successfully\n", 'status'))
                    else:
                        # Check if response contains file path patterns but no content was extracted
                        if '[[' in response and ']]' in response:
                            self.root.after(0, lambda t=agent_title: 
                                self.display_message(f"[{t}] ⚠️ File path found but no valid content extracted\n", 'warning'))
                except Exception as e:
                    self.root.after(0, lambda t=agent_title, err=str(e): 
                        self.display_message(f"[{t}] File write error: {err}\n", 'error'))

            # Display the response in the chat
            agent_title = agent.get('title', 'Agent')
            print(f"Debug: About to display response for {agent_title}, response length: {len(response)}")
            print(f"Debug: Response content preview: {response[:200]}...")

            self.root.after(0, lambda t=agent_title, r=response: self._display_agent_response(t, r))

            return response

        except Exception as e:
            return f"Error executing agent: {str(e)}"

    def _resolve_placeholders(self, message, resolved_outputs):
        """Resolve {{Agent-X}} placeholders in the message."""
        import re

        def replace_placeholder(match):
            agent_ref = match.group(1)  # e.g., "Agent-1"
            if agent_ref in resolved_outputs:
                output = resolved_outputs[agent_ref]
                # Truncate if too long
                if len(output) > 500:
                    return f"[Output from {agent_ref}]: {output[:500]}..."
                else:
                    return f"[Output from {agent_ref}]: {output}"
            else:
                return f"[{agent_ref} output not available]"

        # Replace {{Agent-X}} patterns
        resolved = re.sub(r'\{\{(Agent-\d+)\}\}', replace_placeholder, message)
        return resolved

    def _display_agent_response(self, agent_title, response):
        """Display agent response in the chat (called from main thread)."""
        print(f"Debug: Displaying response for {agent_title}, length: {len(response)}")
        print(f"Debug: Response preview: {response[:100]}...")

        self.display_message(f"\n🤖 {agent_title} Response:\n", 'assistant')
        self.display_message(f"{response}\n", 'assistant')

    def _re_enable_agent_controls(self):
        """Re-enable agent controls after sequence completion (called from main thread)."""
        if hasattr(self, 'configure_agents_button') and self.configure_agents_button:
            if len(self.armed_agents) > 0:
                self.configure_agents_button.config(state="normal")

    def move_agent_up(self, listbox):
        """Move selected agent up in the sequence."""
        try:
            selection = listbox.curselection()
            if not selection or selection[0] == 0:
                return  # Nothing selected or already at top

            idx = selection[0]
            # Swap agents
            self.armed_agents[idx], self.armed_agents[idx-1] = self.armed_agents[idx-1], self.armed_agents[idx]

            # Update titles to maintain order
            self._update_agent_titles()

            # Refresh listbox and maintain selection
            self.populate_agent_list(listbox)
            listbox.selection_set(idx-1)

            # Update cache
            self.agent_cache.save_agents_to_cache(self.armed_agents)

        except Exception as e:
            self.display_message(f"\nError moving agent up: {e}\n", 'error')

    def move_agent_down(self, listbox):
        """Move selected agent down in the sequence."""
        try:
            selection = listbox.curselection()
            if not selection or selection[0] >= len(self.armed_agents) - 1:
                return  # Nothing selected or already at bottom

            idx = selection[0]
            # Swap agents
            self.armed_agents[idx], self.armed_agents[idx+1] = self.armed_agents[idx+1], self.armed_agents[idx]

            # Update titles to maintain order
            self._update_agent_titles()

            # Refresh listbox and maintain selection
            self.populate_agent_list(listbox)
            listbox.selection_set(idx+1)

            # Update cache
            self.agent_cache.save_agents_to_cache(self.armed_agents)

        except Exception as e:
            self.display_message(f"\nError moving agent down: {e}\n", 'error')

    def delete_agent(self, listbox):
        """Delete selected agent from the sequence."""
        try:
            selection = listbox.curselection()
            if not selection:
                return  # Nothing selected

            idx = selection[0]
            agent_title = self.armed_agents[idx].get('title', f'Agent-{idx+1}')

            # Confirm deletion
            import tkinter.messagebox as msgbox
            if msgbox.askyesno("Confirm Delete", f"Delete {agent_title}?"):
                # Remove agent
                del self.armed_agents[idx]

                # Update titles to maintain order
                self._update_agent_titles()

                # Refresh listbox
                self.populate_agent_list(listbox)

                # Select next item if available
                if idx < len(self.armed_agents):
                    listbox.selection_set(idx)
                elif len(self.armed_agents) > 0:
                    listbox.selection_set(len(self.armed_agents) - 1)

                # Update cache
                self.agent_cache.save_agents_to_cache(self.armed_agents)

                self.display_message(f"\nDeleted {agent_title}\n", 'status')

        except Exception as e:
            self.display_message(f"\nError deleting agent: {e}\n", 'error')

    def edit_agent(self, listbox, parent_window):
        """Edit selected agent's properties."""
        try:
            selection = listbox.curselection()
            if not selection:
                return  # Nothing selected

            idx = selection[0]
            agent = self.armed_agents[idx]

            # Create edit dialog
            edit_window = tk.Toplevel(parent_window)
            edit_window.title(f"Edit {agent.get('title', 'Agent')}")
            edit_window.geometry("600x500")
            edit_window.transient(parent_window)
            edit_window.grab_set()

            # Center dialog
            edit_window.update_idletasks()
            x = parent_window.winfo_x() + (parent_window.winfo_width() // 2) - 300
            y = parent_window.winfo_y() + (parent_window.winfo_height() // 2) - 250
            edit_window.geometry(f"600x500+{x}+{y}")

            # Create form
            form_frame = ttk.Frame(edit_window, padding="10")
            form_frame.pack(fill=tk.BOTH, expand=True)

            # Title field
            ttk.Label(form_frame, text="Title:").pack(anchor="w")
            title_var = tk.StringVar(value=agent.get('title', ''))
            title_entry = ttk.Entry(form_frame, textvariable=title_var, width=50)
            title_entry.pack(fill=tk.X, pady=(0, 10))

            # System prompt field
            ttk.Label(form_frame, text="System Prompt:").pack(anchor="w")
            system_text = tk.Text(form_frame, height=5, wrap=tk.WORD)
            system_text.insert(1.0, agent.get('system', ''))
            system_text.pack(fill=tk.X, pady=(0, 10))

            # User message field
            ttk.Label(form_frame, text="User Message:").pack(anchor="w")
            message_text = tk.Text(form_frame, height=8, wrap=tk.WORD)
            messages = agent.get('messages', [])
            if messages:
                message_text.insert(1.0, messages[0].get('content', ''))
            message_text.pack(fill=tk.X, pady=(0, 10))

            # Buttons
            btn_frame = ttk.Frame(form_frame)
            btn_frame.pack(fill=tk.X)

            def save_changes():
                # Update agent
                agent['title'] = title_var.get() or f"Agent-{idx+1}"
                agent['system'] = system_text.get(1.0, tk.END).strip()

                # Update message
                new_message = message_text.get(1.0, tk.END).strip()
                if new_message:
                    agent['messages'] = [{"role": "user", "content": new_message}]

                # Update timestamp
                from datetime import datetime
                agent['metadata']['timestamp'] = datetime.now().isoformat()

                # Refresh listbox
                self.populate_agent_list(listbox)
                listbox.selection_set(idx)

                # Update cache
                self.agent_cache.save_agents_to_cache(self.armed_agents)

                self.display_message(f"\nUpdated {agent['title']}\n", 'status')
                edit_window.destroy()

            ttk.Button(btn_frame, text="Save", command=save_changes).pack(side=tk.LEFT)
            ttk.Button(btn_frame, text="Cancel", command=edit_window.destroy).pack(side=tk.RIGHT)

        except Exception as e:
            self.display_message(f"\nError editing agent: {e}\n", 'error')

    def _update_agent_titles(self):
        """Update agent titles to maintain sequential numbering."""
        for i, agent in enumerate(self.armed_agents):
            agent['title'] = f"Agent-{i+1}"
            agent['metadata']['index'] = i+1

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
        pos = int(float(value))
        context_value = self.context_values[pos]
        self.context_size.set(context_value)  # Update the actual context size variable
        self.context_label.config(text=self.format_context_size(context_value))

    def format_context_size(self, value):
        """Format context size for display (e.g., 8000 -> '8k')."""
        if value >= 1000:
            return f"{value // 1000}k"
        return str(value)

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
        pos = int(float(value))
        tokens_value = self.max_tokens_values[pos]
        self.max_tokens.set(tokens_value)  # Update the actual max tokens variable
        self.max_tokens_label.config(text=self.format_tokens(tokens_value))

    def format_tokens(self, value):
        """Format token count for display (e.g., 2000 -> '2k')."""
        if value >= 1000:
            return f"{value // 1000}k"
        return str(value)

    def on_chunk_change(self, value):
        """Update chunk size label when slider moves."""
        pos = int(float(value))
        chunk_value = self.chunk_values[pos]
        self.chunk_size.set(chunk_value)  # Update the actual chunk size variable
        self.chunk_label.config(text=self.format_chunk_size(chunk_value))

    def format_chunk_size(self, value):
        """Format chunk size for display (e.g., 1000 -> '1k')."""
        if value >= 1000:
            return f"{value // 1000}k"
        return str(value)

    # Custom thumb methods removed

    def on_show_image_toggle(self):
        """Update inline image display based on the checkbox."""
        if self.file_type == 'image' and self.file_img:
            self.display_uploaded_image()

    def on_advanced_web_access_toggle(self):
        """Handle web search toggle with enhanced dependency management."""
        advanced_web_access = self.advanced_web_access_var.get()
        self.settings.set("advanced_web_access", advanced_web_access)

        if advanced_web_access:
            # Use enhanced dependency management for non-blocking installation
            dependencies = ["crawl4ai", "playwright"]
            
            def on_success():
                self.display_message("\nAdvanced web search enabled. The chatbot can now crawl websites for detailed information.\n", "status")
            
            def on_error(error_msg):
                self.display_message(f"\nError setting up web search: {error_msg}\n", 'error')
                self.advanced_web_access_var.set(False)
                self.settings.set("advanced_web_access", False)
            
            # Submit dependency management task to enhanced tools manager
            task_id = self.enhanced_dependency_manager.manage_dependencies(
                dependencies, 
                on_success, 
                on_error
            )
            self.active_tasks[task_id] = "Installing web search dependencies"
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

    def on_panda_csv_toggle(self):
        """Handle Panda CSV Analysis Tool toggle."""
        try:
            if self.panda_csv_var.get():
                # Tool enabled - prompt for CSV file
                file_path = filedialog.askopenfilename(
                    title="Select CSV File for Analysis",
                    filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
                )
                
                if not file_path:
                    # User canceled - disable checkbox
                    self.panda_csv_var.set(False)
                    return
                
                # Load the CSV
                try:
                    self.panda_csv_tool.load_csv(file_path)
                    metadata = self.panda_csv_tool.get_metadata()
                    
                    # Display success message with metadata and helper text
                    msg = f"\n[CSV Tool Enabled]\n"
                    msg += f"File: {metadata['file_path']}\n"
                    msg += f"Rows: {metadata['rows']}, Columns: {metadata['cols']}\n"
                    msg += f"Original Headers: {', '.join(metadata['original_headers'])}\n\n"
                    msg += "Helper Text:\n"
                    msg += "  {{CX}} - Double braces = Output Column (write result to column X)\n"
                    msg += "  {CX} - Single braces = Input Column (read value from column X)\n"
                    msg += "  {RX} - Row specification (optional)\n"
                    msg += "    {R1}      - Process only row 1\n"
                    msg += "    {R1-5}    - Process rows 1 through 5\n"
                    msg += "    {R1,3,5}  - Process rows 1, 3, and 5\n"
                    msg += "    {R5-}     - Process rows 5 to end\n"
                    msg += "    No {R...} - Process all rows\n"
                    msg += "  Example: '{R1-10} Grade this answer: {C1}. Write score to {{C5}}'\n\n"
                    msg += "Enter your prompt using column/row references, then I'll show you a preview.\n"
                    
                    self.display_message(msg, 'status')
                    
                    # Warn about chat history
                    self.display_message("\n⚠️ WARNING: When CSV Tool is active, chat history is NOT included in prompts.\n", 'error')
                    
                except Exception as e:
                    self.display_message(f"\n[CSV Tool Error]\nFailed to load CSV: {e}\n", 'error')
                    self.panda_csv_var.set(False)
                    return
            
            else:
                # Tool disabled - clear state
                self.panda_csv_tool.clear()
                self.panda_csv_preview_prompt = None
                self.display_message("\n[CSV Tool Disabled]\n", 'status')
                
        except Exception as e:
            self.display_message(f"\n[CSV Tool Error]\n{e}\n", 'error')
            self.panda_csv_var.set(False)

    def process_csv_rows(self, prompt: str, preview_only: bool = False):
        """Process CSV rows with the given prompt.
        
        Args:
            prompt: The prompt template with {CX}, {{CX}}, and optional {R...} placeholders
            preview_only: If True, only process first 3 rows for preview
        """
        # Set processing state
        self.is_processing = True
        self.status_bar["text"] = "Processing CSV rows..."
        
        try:
            if not self.panda_csv_tool.has_data():
                self.display_message("\n[CSV Tool Error]\nNo CSV loaded.\n", 'error')
                return
            
            # Import here to access utility function
            from tools_system import parse_row_specification
            
            metadata = self.panda_csv_tool.get_metadata()
            total_rows = metadata['rows']
            
            # Extract row specification from prompt
            row_spec, cleaned_prompt = self.panda_csv_tool.extract_row_specification(prompt)
            
            # Determine which rows to process
            if row_spec:
                try:
                    # Parse the row specification
                    row_indices = parse_row_specification(row_spec, total_rows)
                    
                    # In preview mode, limit to first 3 of specified rows
                    if preview_only:
                        rows_to_process = row_indices[:3]
                    else:
                        rows_to_process = row_indices
                    
                    spec_description = f"rows {row_spec}"
                except ValueError as e:
                    self.display_message(f"\n[CSV Tool Error]\nInvalid row specification: {e}\n", 'error')
                    return
            else:
                # No row specification - process all rows or first 3 for preview
                if preview_only:
                    rows_to_process = list(range(min(3, total_rows)))
                    spec_description = "all rows"
                else:
                    rows_to_process = list(range(total_rows))
                    spec_description = "all rows"
            
            # Display start message
            if preview_only:
                mode_str = f"PREVIEW MODE - First {len(rows_to_process)} rows of {spec_description}"
            else:
                mode_str = f"Processing {len(rows_to_process)} rows ({spec_description})"
            
            self.display_message(f"\n[CSV Processing Started - {mode_str}]\n", 'status')
            
            # Process each row
            for idx, row_idx in enumerate(rows_to_process):
                if self.stop_event.is_set():
                    self.display_message(f"\n[CSV Processing Stopped]\nProcessed {idx}/{len(rows_to_process)} rows.\n", 'status')
                    break
                
                # Show progress
                self.display_message(f"\n--- Row {row_idx + 1} ({idx + 1}/{len(rows_to_process)}) ---\n", 'status')
                
                # Process the prompt for this row (use cleaned_prompt without {R...})
                processed_prompt, output_columns, substitution_log = self.panda_csv_tool.process_prompt_for_row(
                    cleaned_prompt, row_idx
                )
                
                # Check if output columns are specified
                if not output_columns and not preview_only:
                    self.display_message(f"\n⚠️ Warning: No output columns specified (use {{{{CX}}}} syntax).\nResults will only be displayed, not saved to CSV.\n", 'error')
                
                # Display what we're sending
                self.display_message(f"Prompt: {processed_prompt[:200]}{'...' if len(processed_prompt) > 200 else ''}\n", 'info')
                if output_columns:
                    self.display_message(f"Expected outputs: {', '.join([f'COLUMN_{col}' for col in output_columns])}\n", 'info')
                else:
                    self.display_message(f"Expected outputs: (none specified - response will not be saved to CSV)\n", 'info')
                
                # Call the model (using current chat settings but NO chat history)
                try:
                    # Save original chat history
                    original_history = self.conversation_manager.active_conversation.messages.copy()
                    
                    # Temporarily clear history for this request
                    self.conversation_manager.active_conversation.messages = []
                    
                    # Get response
                    response_text = self._get_model_response_sync(processed_prompt)
                    
                    # Restore history
                    self.conversation_manager.active_conversation.messages = original_history
                    
                    # If no output columns specified, just display the raw response
                    if not output_columns:
                        self.display_message("\n", 'assistant')
                        self.display_message(f"{response_text}\n", 'assistant')
                    else:
                        # Parse the response for structured output
                        parsed_results = self.panda_csv_tool.parse_model_response(response_text, output_columns)
                        
                        # Display results
                        if parsed_results:
                            self.display_message("Results:\n", 'info')
                            for col_num, value in parsed_results.items():
                                self.display_message(f"  COLUMN_{col_num}: {value[:100]}{'...' if len(value) > 100 else ''}\n", 'info')
                            
                            # Update cells (only if not preview mode)
                            if not preview_only:
                                for col_num, value in parsed_results.items():
                                    self.panda_csv_tool.update_cell(row_idx, col_num, value)
                        else:
                            self.display_message("No valid outputs found in response.\n", 'error')
                            # Still show the raw response so user can see what the model said
                            self.display_message(f"\nRaw response:\n{response_text[:500]}{'...' if len(response_text) > 500 else ''}\n", 'info')
                    
                except Exception as e:
                    self.display_message(f"Error processing row {row_idx + 1}: {e}\n", 'error')
                    continue
                
                # Save after each row (only if not preview mode)
                if not preview_only:
                    try:
                        self.panda_csv_tool.save_csv()
                        self.display_message(f"✓ Saved after row {row_idx + 1}\n", 'status')
                    except Exception as e:
                        self.display_message(f"Warning: Failed to save after row {row_idx + 1}: {e}\n", 'error')
            
            # Final message
            if preview_only:
                self.display_message("\n[Preview Complete]\n", 'status')
                if row_spec:
                    self.display_message(f"Enter a new prompt to revise, or type 'ok' to re-apply the same prompt to {spec_description}.\n", 'info')
                else:
                    self.display_message("Enter a new prompt to revise, or type 'ok' to re-apply the same prompt to all rows.\n", 'info')
                # Store the prompt for later
                self.panda_csv_preview_prompt = prompt
            else:
                self.display_message(f"\n[CSV Processing Complete]\nProcessed {len(rows_to_process)} rows.\n", 'status')
                self.display_message(f"Results saved to: {metadata['file_path']}\n", 'info')
                # Clear preview prompt
                self.panda_csv_preview_prompt = None
                
        except Exception as e:
            self.display_message(f"\n[CSV Processing Error]\n{e}\n", 'error')
            import traceback
            traceback.print_exc()
        finally:
            # Reset processing state
            self.is_processing = False
            self.status_bar["text"] = "Ready"

    def _get_model_response_sync(self, prompt: str) -> str:
        """Get a synchronous response from the model for CSV processing.
        
        Args:
            prompt: The prompt to send
            
        Returns:
            The model's response text
        """
        try:
            # Get system instructions (full, not truncated - needed for consistent evaluation)
            system_msg = self.system_text.get('1.0', tk.END).strip()
            
            # Prepare messages (system + user prompt, no history)
            messages = []
            if system_msg:
                messages.append({
                    'role': 'system',
                    'content': system_msg
                })
            messages.append({
                'role': 'user',
                'content': prompt
            })
            
            # Use the same approach as the main send_message method
            # Get streaming response from model manager
            full_response = ""
            stream = self.model_manager.get_response(
                messages=messages,
                model=self.selected_model,
                temperature=self.temperature.get()
            )
            
            # Collect streaming response
            for chunk in stream:
                if self.stop_event.is_set():
                    break
                    
                if isinstance(chunk, dict) and 'message' in chunk:
                    content = chunk['message'].get('content', '')
                    full_response += content
                elif isinstance(chunk, str):
                    full_response += chunk
            
            return full_response
                
        except Exception as e:
            raise Exception(f"Failed to get model response: {e}")

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

    def toggle_edit_mode(self):
        """Toggle edit mode for chat history.
        
        When enabled, the chat display becomes editable, allowing users to modify
        the conversation history directly. This is useful for:
        - Correcting mistakes in previous messages
        - Removing unwanted content before including in context
        - Manually adjusting the conversation flow
        """
        try:
            if not self.edit_mode_enabled:
                # ENABLE EDIT MODE
                self.edit_mode_enabled = True
                
                # Make chat display editable
                self.chat_display["state"] = "normal"
                
                # Update button appearance to show active state
                self.edit_chat_button.configure(style="Accent.TButton")
                
                # Show status message
                self.status_bar["text"] = "Edit Mode: ON - You can now edit chat history directly"
                
                # Add a visual indicator at the top of chat
                current_content = self.chat_display.get("1.0", tk.END)
                self.chat_display.delete("1.0", tk.END)
                self.chat_display.insert("1.0", "🔓 EDIT MODE ACTIVE - Chat history is now editable\n" + "="*60 + "\n\n", "warning")
                self.chat_display.insert(tk.END, current_content)
                self.chat_display.see("1.0")  # Scroll to top to show indicator
                
            else:
                # DISABLE EDIT MODE
                self.edit_mode_enabled = False
                
                # Get the edited content first (in case user edited it)
                edited_content = self.chat_display.get("1.0", tk.END)
                
                # Remove edit mode indicator if present
                if edited_content.startswith("🔓 EDIT MODE ACTIVE"):
                    # Find the end of the indicator (after the separator line)
                    lines = edited_content.split("\n")
                    if len(lines) > 2:
                        # Remove first 3 lines (indicator, separator, blank line)
                        edited_content = "\n".join(lines[3:])
                
                # Update display with cleaned content
                self.chat_display.delete("1.0", tk.END)
                self.chat_display.insert("1.0", edited_content)
                
                # Make chat display read-only again
                self.chat_display["state"] = "disabled"
                
                # Reset button appearance
                self.edit_chat_button.configure(style="TButton")
                
                # Update status
                self.status_bar["text"] = "Edit Mode: OFF - Chat history is read-only"
                self.chat_display.see(tk.END)  # Scroll to bottom
                
        except Exception as e:
            error_handler.handle_error(e, "Toggling edit mode")
            self.display_message(f"\nError toggling edit mode: {e}\n", "error")
            # Ensure we're in a consistent state
            self.edit_mode_enabled = False
            try:
                self.chat_display["state"] = "disabled"
            except:
                pass

    @safe_execute("Sending message")
    def send_message(self):
        """Process and send the user's message."""
        user_input = self.input_field.get("1.0", tk.END).strip()
        if not user_input or user_input == "Type your message here...":
            return

        # Store original input for display purposes
        original_input = user_input

        # Check if Agent Mode is active - if so, stage the agent instead of sending
        if self.agent_mode_var.get():
            self.stage_agent(original_input)
            return

        # Check if Panda CSV Tool is active
        if self.panda_csv_var.get() and self.panda_csv_tool.has_data():
            # Display user input
            self.display_message("\n", 'user')
            self.display_message(f"{original_input}\n", 'user')
            self.input_field.delete("1.0", tk.END)
            
            # Check if user typed 'ok' to continue from preview
            if self.panda_csv_preview_prompt and original_input.lower().strip() == 'ok':
                # Continue with full processing using stored prompt in a separate thread
                threading.Thread(target=self.process_csv_rows, args=(self.panda_csv_preview_prompt, False)).start()
                return
            
            # Otherwise, treat as new prompt and start preview in a separate thread
            threading.Thread(target=self.process_csv_rows, args=(original_input, True)).start()
            return

        # Process file read requests if Read File tool is enabled
        if self.read_file_var.get():
            user_input = self.process_file_read_requests_sync(user_input)

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

        # Display user message (use truncated version if enabled, but only for display)
        if self.truncate_file_display_var.get():
            # For truncated display, show the original message without file patterns
            # The actual file operation status will be shown by the processing methods
            display_input = self.get_truncated_display_message_text_only(original_input)
        else:
            # For full display, show the processed message with file content
            display_input = user_input

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
                search_results = self.perform_advanced_web_search_sync(user_input)
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
        """Get formatted chat history for context.
        
        Retrieves the full visible chat history from the UI display,
        including messages that may not have been added to the conversation manager
        (e.g., batch processing with history disabled).
        """
        try:
            # Get all text from the chat display
            self.chat_display["state"] = "normal"
            display_content = self.chat_display.get("1.0", tk.END).strip()
            self.chat_display["state"] = "disabled"
            
            # If display is empty, fall back to conversation manager
            if not display_content:
                history = []
                for msg in self.conversation_manager.active_conversation.messages:
                    if msg.role in ['user', 'assistant']:
                        history.append(f"{msg.role.capitalize()}: {msg.content}")
                return "\n\n".join(history)
            
            # Return the full markdown display content
            # This includes all visible interactions regardless of conversation manager state
            return display_content
            
        except Exception as e:
            # Fallback to conversation manager on any error
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
        """Display a message in the chat window with optional tags and enhanced markdown rendering.
        
        Respects edit mode: if edit mode is enabled, the widget remains editable.
        """
        # Remember if we were in edit mode
        was_in_edit_mode = getattr(self, 'edit_mode_enabled', False)
        
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
            # Use enhanced markdown rendering for assistant messages
            try:
                self._render_markdown_safe(message)
            except Exception as e:
                print(f"Error in markdown rendering: {e}")
                # Fallback to basic display
                self._display_message_fallback(message, tag)
        else:
            # For other message types, just insert with the tag
            self.chat_display.insert(tk.END, message, tag)

        # Only disable if we weren't in edit mode
        if not was_in_edit_mode:
            self.chat_display["state"] = "disabled"
        
        self.chat_display.see(tk.END)
    
    def _render_markdown_safe(self, message):
        """Safely render markdown with improved error handling."""
        try:
            # Convert markdown to HTML with enhanced extensions
            html = markdown.markdown(
                message,
                extensions=[
                    'extra',           # Tables, code blocks, etc.
                    'codehilite',      # Syntax highlighting support
                    'nl2br',           # Convert newlines to <br>
                    'sane_lists',      # Better list handling
                    'fenced_code'      # Support for ``` code blocks
                ]
            )
            
            # Create parser with main UI color scheme for consistency
            scheme = self.theme_manager.get_current_scheme()
            color_scheme = {
                'bg': scheme.bg_color,
                'fg': scheme.fg_color,
                'accent': scheme.accent_color,
                'purple': scheme.markdown_h1 or scheme.subtle_accent,
                'cyan': scheme.markdown_h2 or scheme.highlight_color,
                'green': scheme.success_color,
                'red': scheme.error_color,
                'yellow': scheme.warning_color,
                'code_bg': scheme.code_bg,
                'code_fg': scheme.code_fg,
                'link': scheme.link_color,
                'quote_border': scheme.quote_border,
                'hr': scheme.hr_color,
                'border': scheme.border_color,
                'header_bg': scheme.header_bg
            }
            parser = HTMLTextParser(self.chat_display, color_scheme=color_scheme)
            parser.feed(html)
            
        except Exception as e:
            print(f"Markdown parse error: {e}")
            # Fall back to basic display
            raise  # Re-raise to trigger fallback in display_message
    
    def _display_message_fallback(self, message, tag):
        """Fallback display method for when markdown rendering fails."""
        parts = message.split('```')
        for i, part in enumerate(parts):
            if i % 2 == 0:  # Regular text
                self.chat_display.insert(tk.END, part, tag)
            else:  # Code block
                # Try to extract language from first line
                lines = part.strip().split('\n', 1)
                if len(lines) > 1:
                    language = lines[0].strip()
                    code = lines[1] if len(lines) > 1 else ''
                else:
                    language = ''
                    code = part.strip()
                
                # Display code block with basic formatting
                self.chat_display.insert(tk.END, '\n', tag)
                if language:
                    self.chat_display.insert(tk.END, f'[{language}]\n', 'code_language')
                self.chat_display.insert(tk.END, code, 'code')
                self.chat_display.insert(tk.END, '\n', tag)

    def parse_markdown_to_text_widget(self, text_widget, markdown_content, link_callback=None):
        """Parse markdown and render it in a Text widget with proper formatting.
        
        Args:
            text_widget: Tkinter Text widget to render into
            markdown_content: Markdown string to parse
            link_callback: Optional function to call when links are clicked (receives URL)
        """
        # Configure text widget tags for markdown elements
        text_widget.tag_configure('h1', font=(self.font_family, self.font_size_heading + 4, 'bold'), foreground=self.highlight_color, spacing1=15, spacing3=10)
        text_widget.tag_configure('h2', font=(self.font_family, self.font_size_heading + 2, 'bold'), foreground=self.accent_color, spacing1=12, spacing3=8)
        text_widget.tag_configure('h3', font=(self.font_family, self.font_size_heading, 'bold'), foreground=self.subtle_accent, spacing1=10, spacing3=6)
        text_widget.tag_configure('h4', font=(self.font_family, self.font_size_chat + 2, 'bold'), foreground=self.fg_color, spacing1=8, spacing3=4)
        text_widget.tag_configure('h5', font=(self.font_family, self.font_size_chat + 1, 'bold'), foreground=self.fg_color, spacing1=6, spacing3=3)
        text_widget.tag_configure('h6', font=(self.font_family, self.font_size_chat, 'bold'), foreground=self.muted_text, spacing1=4, spacing3=2)
        
        text_widget.tag_configure('bold', font=(self.font_family, self.font_size_chat + 1, 'bold'))
        text_widget.tag_configure('italic', font=(self.font_family, self.font_size_chat + 1, 'italic'))
        text_widget.tag_configure('bold_italic', font=(self.font_family, self.font_size_chat + 1, 'bold italic'))
        text_widget.tag_configure('code', font=(self.font_family_mono, self.font_size_mono), background=self.secondary_bg, foreground=self.success_color)
        text_widget.tag_configure('code_block', font=(self.font_family_mono, self.font_size_mono), background=self.secondary_bg, foreground=self.fg_color, spacing1=5, spacing3=5, lmargin1=20, lmargin2=20)
        text_widget.tag_configure('link', foreground=self.highlight_color, underline=True, font=(self.font_family, self.font_size_chat))
        text_widget.tag_configure('list_item', lmargin1=20, lmargin2=40)
        text_widget.tag_configure('blockquote', lmargin1=20, lmargin2=20, foreground=self.muted_text, background=self.tertiary_bg)
        text_widget.tag_configure('separator', foreground=self.border_color)
        
        # Make links clickable if callback provided
        if link_callback:
            text_widget.tag_bind('link', '<Button-1>', lambda e: self._handle_help_link_click(e, link_callback))
            text_widget.tag_bind('link', '<Enter>', lambda e: text_widget.config(cursor='hand2'))
            text_widget.tag_bind('link', '<Leave>', lambda e: text_widget.config(cursor=''))
        
        # Enable widget for insertion
        text_widget['state'] = 'normal'
        text_widget.delete('1.0', tk.END)
        
        # Parse markdown line by line
        lines = markdown_content.split('\n')
        i = 0
        in_code_block = False
        code_block_content = []
        code_block_language = ''
        
        while i < len(lines):
            line = lines[i]
            
            # Code block detection
            if line.strip().startswith('```'):
                if not in_code_block:
                    # Start of code block
                    in_code_block = True
                    code_block_language = line.strip()[3:].strip()
                    code_block_content = []
                else:
                    # End of code block
                    in_code_block = False
                    if code_block_language:
                        text_widget.insert(tk.END, f'[{code_block_language}]\n', 'code')
                    text_widget.insert(tk.END, '\n'.join(code_block_content) + '\n', 'code_block')
                    text_widget.insert(tk.END, '\n')
                    code_block_content = []
                    code_block_language = ''
                i += 1
                continue
            
            # If in code block, collect lines
            if in_code_block:
                code_block_content.append(line)
                i += 1
                continue
            
            # Headers
            if line.startswith('# '):
                text_widget.insert(tk.END, line[2:] + '\n', 'h1')
            elif line.startswith('## '):
                text_widget.insert(tk.END, line[3:] + '\n', 'h2')
            elif line.startswith('### '):
                text_widget.insert(tk.END, line[4:] + '\n', 'h3')
            elif line.startswith('#### '):
                text_widget.insert(tk.END, line[5:] + '\n', 'h4')
            elif line.startswith('##### '):
                text_widget.insert(tk.END, line[6:] + '\n', 'h5')
            elif line.startswith('###### '):
                text_widget.insert(tk.END, line[7:] + '\n', 'h6')
            
            # Horizontal rule
            elif line.strip() in ['---', '___', '***']:
                text_widget.insert(tk.END, '─' * 80 + '\n', 'separator')
            
            # List items
            elif line.strip().startswith('- ') or line.strip().startswith('* '):
                self._parse_inline_formatting(text_widget, '• ' + line.strip()[2:], 'list_item')
                text_widget.insert(tk.END, '\n')
            elif re.match(r'^\d+\.\s', line.strip()):
                # Numbered list
                match = re.match(r'^(\d+)\.\s(.*)$', line.strip())
                if match:
                    num, content = match.groups()
                    self._parse_inline_formatting(text_widget, f'{num}. {content}', 'list_item')
                    text_widget.insert(tk.END, '\n')
            
            # Blockquote
            elif line.strip().startswith('>'):
                text_widget.insert(tk.END, line.strip()[1:].strip() + '\n', 'blockquote')
            
            # Regular paragraph
            elif line.strip():
                self._parse_inline_formatting(text_widget, line)
                text_widget.insert(tk.END, '\n')
            
            # Empty line
            else:
                text_widget.insert(tk.END, '\n')
            
            i += 1
        
        # Disable widget after rendering
        text_widget['state'] = 'disabled'
    
    def _parse_inline_formatting(self, text_widget, line, base_tag=''):
        """Parse inline markdown formatting (bold, italic, code, links)."""
        # Regular expressions for inline elements
        patterns = [
            (r'\[([^\]]+)\]\(([^)]+)\)', 'link'),  # [text](url)
            (r'`([^`]+)`', 'code'),                  # `code`
            (r'\*\*\*([^*]+)\*\*\*', 'bold_italic'), # ***text***
            (r'\*\*([^*]+)\*\*', 'bold'),           # **text**
            (r'\*([^*]+)\*', 'italic'),             # *text*
            (r'___([^_]+)___', 'bold_italic'),      # ___text___
            (r'__([^_]+)__', 'bold'),               # __text__
            (r'_([^_]+)_', 'italic'),               # _text_
        ]
        
        # Store link targets for later retrieval
        if not hasattr(self, '_help_links'):
            self._help_links = {}
        
        remaining = line
        while remaining:
            earliest_match = None
            earliest_pos = len(remaining)
            earliest_pattern_info = None
            
            # Find earliest match among all patterns
            for pattern, tag_type in patterns:
                match = re.search(pattern, remaining)
                if match and match.start() < earliest_pos:
                    earliest_match = match
                    earliest_pos = match.start()
                    earliest_pattern_info = (pattern, tag_type)
            
            if earliest_match:
                # Insert text before match
                if earliest_pos > 0:
                    if base_tag:
                        text_widget.insert(tk.END, remaining[:earliest_pos], base_tag)
                    else:
                        text_widget.insert(tk.END, remaining[:earliest_pos])
                
                # Insert formatted text
                pattern, tag_type = earliest_pattern_info
                if tag_type == 'link':
                    link_text = earliest_match.group(1)
                    link_url = earliest_match.group(2)
                    
                    # Store link info
                    link_mark = f'link_{len(self._help_links)}'
                    self._help_links[link_mark] = link_url
                    
                    # Insert link with mark
                    start_idx = text_widget.index(tk.END)
                    tags = ('link', link_mark, base_tag) if base_tag else ('link', link_mark)
                    text_widget.insert(tk.END, link_text, tags)
                else:
                    formatted_text = earliest_match.group(1)
                    tags = (tag_type, base_tag) if base_tag else (tag_type,)
                    text_widget.insert(tk.END, formatted_text, tags)
                
                # Continue with remaining text
                remaining = remaining[earliest_match.end():]
            else:
                # No more matches, insert remaining text
                if base_tag:
                    text_widget.insert(tk.END, remaining, base_tag)
                else:
                    text_widget.insert(tk.END, remaining)
                break
    
    def _handle_help_link_click(self, event, link_callback):
        """Handle clicking on a link in the help viewer."""
        try:
            # Get the link mark at click position
            text_widget = event.widget
            index = text_widget.index(f'@{event.x},{event.y}')
            
            # Get all tags at this position
            tags = text_widget.tag_names(index)
            
            # Find link mark
            for tag in tags:
                if tag.startswith('link_'):
                    url = self._help_links.get(tag)
                    if url:
                        link_callback(url)
                    break
        except Exception as e:
            print(f"Error handling link click: {e}")

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

        # NEW: Try to find content BEFORE the file path (common pattern)
        content_before_path = self.extract_content_before_path(response_text, file_path)
        if content_before_path:
            return content_before_path

        # CHANGED: Don't fall back to entire response - return empty string instead
        # The calling function will handle empty content appropriately
        return ""

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

    def extract_content_before_path(self, response_text, file_path):
        """Extract content that appears BEFORE the file path mention.

        This handles the common pattern where AI writes:
        "Here's the content:
        [actual content here]
        [[file.txt]]"

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
                # Find content BEFORE this pattern
                end_pos = response_text.find(pattern)
                preceding_text = response_text[:end_pos].strip()

                # Look for common content delimiters
                # Try to find the last code block before the file path
                code_block_match = re.findall(r'```(?:\w+)?\s*(.*?)\s*```', preceding_text, re.DOTALL)
                if code_block_match:
                    # Return the last code block
                    return code_block_match[-1].strip()

                # Try to find content after common phrases like "here's", "content:", etc.
                content_markers = [
                    r'(?:here\'?s?\s+(?:the\s+)?content:?|content:?|file\s+content:?)\s*\n+(.*)',
                    r'(?:I\'ll\s+(?:create|write)|creating|writing).*?:\s*\n+(.*)',
                    r'(?:save|saving)\s+(?:this|the\s+following).*?:\s*\n+(.*)'
                ]

                for marker_pattern in content_markers:
                    match = re.search(marker_pattern, preceding_text, re.IGNORECASE | re.DOTALL)
                    if match:
                        content = match.group(1).strip()
                        # Stop at common ending phrases
                        for ending in ['I hope', 'Let me know', 'Would you like', 'This will', 'This should']:
                            if ending in content:
                                content = content[:content.find(ending)].strip()
                        if len(content) > 10:
                            return content

                # If no markers found but there's substantial content, use the last paragraph
                if len(preceding_text) > 50:
                    # Split by double newlines (paragraphs)
                    paragraphs = [p.strip() for p in preceding_text.split('\n\n') if p.strip()]
                    if paragraphs:
                        last_paragraph = paragraphs[-1]
                        # Check if it looks like actual content (not just explanation)
                        if len(last_paragraph) > 30 and not last_paragraph.lower().startswith(('i ', 'here', 'this', 'let', 'would')):
                            return last_paragraph

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
        """Write content to a file using enhanced async tools.

        Args:
            file_path: The path where to write the file
            content: The content to write

        Returns:
            str: Task ID for tracking the write operation
        """
        if not self.write_file_var.get():
            self.display_message("\nFile writing is disabled. Enable it in Tools section.\n", 'warning')
            return None

        def on_success(result):
            success, message = result
            if success:
                self.display_message(f"✅ {message}\n", 'status')
            else:
                self.display_message(f"❌ Write failed: {message}\n", 'error')
        
        def on_error(error_msg):
            self.display_message(f"❌ File write failed: {error_msg}\n", 'error')
        
        # Submit write task to enhanced tools manager
        task_id = self.enhanced_file_tools.write_file(file_path, content, on_success, on_error)
        self.active_tasks[task_id] = f"Writing to {os.path.basename(file_path)}"
        
        return task_id

    def write_file_safely_sync(self, file_path, content):
        """Legacy synchronous file write (deprecated - use write_file_safely instead).

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
        skipped_empty = 0

        self.display_message(f"\n📝 Processing {len(write_requests)} file write request(s)...\n", 'status')

        for request in write_requests:
            file_path = request['path']
            content = request['content']

            # Improved validation
            if not content or len(content.strip()) == 0:
                skipped_empty += 1
                self.display_message(f"\n⚠️ Skipping '{file_path}': No content extracted\n", 'warning')
                self.display_message(f"💡 Tip: Ensure content is in a code block or clearly delimited before/after the file path\n", 'status')
                continue

            # Additional check: don't write if content is suspiciously short
            if len(content.strip()) < 5:
                skipped_empty += 1
                self.display_message(f"\n⚠️ Skipping '{file_path}': Content too short ({len(content)} chars)\n", 'warning')
                continue

            # Additional check: don't write if content looks like AI explanation
            lower_content = content.lower()[:100]
            explanation_indicators = ['i will', 'i have', 'here is how', 'let me', 'i can', 'this will', 'i\'ll']
            if any(indicator in lower_content for indicator in explanation_indicators):
                # Be cautious but don't skip if it's substantial content
                if len(content) < 100:
                    skipped_empty += 1
                    self.display_message(f"\n⚠️ Skipping '{file_path}': Content appears to be explanation, not file data\n", 'warning')
                    continue

            success, message = self.write_file_safely_sync(file_path, content)

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

        # Summary message
        if successful_writes > 0:
            self.display_message(f"\n🎉 Successfully wrote {successful_writes} file(s)!\n", 'status')

        if skipped_empty > 0:
            self.display_message(f"\n⚠️ Skipped {skipped_empty} file(s) due to empty or invalid content\n", 'warning')
            self.display_message(f"💡 Tip: Ask the AI to include content in code blocks or clearly mark content boundaries\n", 'status')

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

    def get_truncated_display_message_text_only(self, user_input):
        """Remove file patterns from message for display, without adding status messages."""
        # Extract file read patterns
        read_pattern1 = r'<<\"([^\"]+)\">>'
        read_pattern2 = r'<<([^>\"]+)>>'

        # Extract file write patterns
        write_pattern1 = r'\[\[\"([^\"]+)\"\]\]'
        write_pattern2 = r'\[\[([^\]\"]+)\]\]'

        # Remove file patterns from original message
        display_message = user_input
        for pattern in [read_pattern1, read_pattern2, write_pattern1, write_pattern2]:
            display_message = re.sub(pattern, '', display_message)

        # Clean up extra whitespace
        display_message = re.sub(r'\s+', ' ', display_message).strip()

        return display_message

    def process_file_read_requests(self, user_input):
        """Process file read requests in user input using enhanced async tools.

        Args:
            user_input: The user's input message

        Returns:
            str: Task ID for tracking the read operation
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

        def on_success(results):
            """Handle successful file reads"""
            processed_input = user_input
            files_read = 0
            
            for path, file_content in results.items():
                if file_content:
                    files_read += 1
                    # Replace the file reference with the content
                    for pattern in [f'<<"{path}">>', f"<<'{path}'>>", f'<<{path}>>']:
                        if pattern in processed_input:
                            replacement = f"\n\n--- Content from {path} ---\n{file_content}\n--- End of {path} ---\n\n"
                            processed_input = processed_input.replace(pattern, replacement)
                            break
                    
                    if self.truncate_file_display_var.get():
                        filename = os.path.basename(path)
                        self.display_message(f"{filename} read\n", 'status')
                    else:
                        self.display_message(f"✅ Read file: {path} ({len(file_content)} characters)\n", 'status')
                else:
                    self.display_message(f"❌ Failed to read file: {path}\n", 'error')
            
            if files_read > 0:
                self.display_message(f"📚 Successfully read {files_read} file(s) and included in your message.\n", 'status')
            
            # Continue with processed input if this was part of a larger operation
            return processed_input
        
        def on_error(error_msg):
            self.display_message(f"❌ File read operation failed: {error_msg}\n", 'error')
            return user_input
        
        # Submit batch read task to enhanced tools manager
        task_id = self.enhanced_file_tools.read_files_batch(all_paths, on_success, on_error)
        self.active_tasks[task_id] = f"Reading {len(all_paths)} file(s)"
        
        return task_id

    def process_file_read_requests_sync(self, user_input):
        """Legacy synchronous file reading for backward compatibility.

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
            file_content = self.read_file_safely_sync(clean_path)

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
        """Read a file using enhanced async tools.

        Args:
            file_path: The path to the file to read

        Returns:
            str: Task ID for tracking the read operation
        """
        def on_success(content):
            return content
        
        def on_error(error_msg):
            self.display_message(f"❌ File read failed: {error_msg}\n", 'error')
            return None
        
        # Submit read task to enhanced tools manager
        task_id = self.enhanced_file_tools.read_file(file_path, on_success, on_error)
        self.active_tasks[task_id] = f"Reading {os.path.basename(file_path)}"
        
        return task_id

    def read_file_safely_sync(self, file_path):
        """Legacy synchronous file read (deprecated - use read_file_safely instead).

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

        except UnicodeDecodeError as e:
            # If MarkItDown fails with Unicode error, try manual UTF-8 reading for text files
            return self._fallback_file_read(file_path, e)
        except Exception as e:
            # Check if it's a MarkItDown encoding error
            error_str = str(e)
            if "UnicodeDecodeError" in error_str or "ascii" in error_str.lower() or "codec can't decode" in error_str.lower():
                return self._fallback_file_read(file_path, e)
            elif "PermissionError" in error_str or "Permission denied" in error_str:
                self.display_message(f"⚠️ Permission denied: {file_path}\n", 'warning')
                return None
            else:
                self.display_message(f"⚠️ Error reading file {file_path}: {str(e)}\n", 'warning')
                return None

    def _fallback_file_read(self, file_path, original_error):
        """Fallback file reading with multiple encoding strategies."""
        # Try different encodings in order of preference
        encodings_to_try = [
            ('utf-8', 'replace'),
            ('utf-8', 'ignore'), 
            ('latin1', 'replace'),
            ('cp1252', 'replace'),  # Windows default
            ('iso-8859-1', 'replace')
        ]
        
        for encoding, error_handling in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=encoding, errors=error_handling) as f:
                    content = f.read()
                    if encoding != 'utf-8' or error_handling != 'strict':
                        self.display_message(f"⚠️ Used fallback reading ({encoding}/{error_handling}) for {file_path} due to encoding issue\n", 'warning')
                    return content
            except Exception:
                continue
        
        # If all encodings fail, try binary read and decode with error replacement
        try:
            with open(file_path, 'rb') as f:
                raw_content = f.read()
                # Try to decode as UTF-8 with replacement
                content = raw_content.decode('utf-8', errors='replace')
                self.display_message(f"⚠️ Used binary fallback reading for {file_path} - some characters may be replaced\n", 'warning')
                return content
        except Exception as final_error:
            self.display_message(f"⚠️ All fallback reading methods failed for {file_path}. Original error: {str(original_error)}, Final error: {str(final_error)}\n", 'warning')
            return None

    def perform_advanced_web_search(self, query):
        """Perform an advanced web search using enhanced async tools.

        Args:
            query: The search query

        Returns:
            str: Task ID for tracking the search operation
        """
        if not self.advanced_web_access_var.get():
            self.display_message("\nAdvanced web search is disabled. Please enable it in the Tools section.\n", 'warning')
            return None

        self.display_message(f"\nStarting advanced web search for: '{query}'\n", 'status')
        
        def on_success(result):
            if result:
                self.display_message(result, 'tool_result')
            else:
                self.display_message("\nWeb search completed but no results were found.\n", 'warning')
        
        def on_error(error_msg):
            self.display_message(f"\nAdvanced web search failed: {error_msg}\n", 'error')
            # Consider disabling if persistent errors
            if "Playwright" in error_msg or "browser" in error_msg.lower():
                self.display_message("\nTo fix this, run: python -m playwright install --with-deps\n", 'warning')
        
        # Submit search task to enhanced tools manager
        task_id = self.enhanced_web_search.search(query, on_success, on_error)
        self.active_tasks[task_id] = f"Web search: {query[:50]}..."
        
        return task_id

    def perform_advanced_web_search_sync(self, query):
        """Legacy synchronous web search for backward compatibility.
        
        Args:
            query: The search query

        Returns:
            str: Search results or None if failed
        """
        if not self.advanced_web_access_var.get():
            self.display_message("\nAdvanced web search is disabled. Please enable it in the Tools section.\n", 'warning')
            return None

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
            self.display_message("\nCrawl4ai not available. Please enable advanced web search in Tools section.\n", 'warning')
            return None
        except Exception as e:
            error_msg = str(e)
            self.display_message(f"\nError during advanced web search: {error_msg}\n", 'error')
            # Check if the error is related to missing Playwright browsers
            if "Executable doesn't exist" in error_msg and "chrome-win" in error_msg:
                self.display_message("\nTo fix this, run: python -m playwright install --with-deps\n", 'warning')
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
        # Check if there's content in the chat display
        self.chat_display["state"] = "normal"
        has_content = bool(self.chat_display.get("1.0", tk.END).strip())
        self.chat_display["state"] = "disabled"
        
        # Ask for confirmation if there's content
        if has_content:
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
        """Save the current conversation with custom filename and clean format.
        
        Extracts conversation content from the UI display (primary source)
        rather than from the conversation_manager.
        """
        # Check if there's any content in the chat display
        self.chat_display["state"] = "normal"
        display_content = self.chat_display.get("1.0", tk.END).strip()
        self.chat_display["state"] = "disabled"
        
        if not display_content:
            messagebox.showinfo("Save Conversation", "No messages to save.")
            return

        # Prompt user for custom filename
        from tkinter import simpledialog

        # Suggest a default name based on the first user message or current time
        default_name = self._generate_default_filename_from_display()

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

        # Save with clean format from UI display
        result = self.save_conversation_from_display(safe_name)
        self.display_message(f"\n{result}\n", "status")

        # Update conversations list
        self.update_conversations_list()

    def _generate_default_filename_from_display(self):
        """Generate a default filename based on UI display content."""
        try:
            # Get display content
            self.chat_display["state"] = "normal"
            display_content = self.chat_display.get("1.0", tk.END).strip()
            self.chat_display["state"] = "disabled"
            
            if not display_content:
                from datetime import datetime
                return f"Chat_{datetime.now().strftime('%Y%m%d_%H%M')}"
            
            # Look for first user message (typically starts with emoji or "You:")
            lines = display_content.split('\n')
            for line in lines:
                # Look for user messages
                if any(marker in line for marker in ['🧑 You:', 'You:', 'User:']):
                    # Get next non-empty line after the marker
                    idx = lines.index(line)
                    if idx + 1 < len(lines):
                        content = lines[idx + 1].strip()
                        # Skip file-related content
                        if content and not any(skip in content.lower() for skip in 
                                             ['document content:', 'file content:', 'image:', 'file:']):
                            # Take first sentence or 30 characters
                            first_sentence = content.split('.')[0][:30]
                            if first_sentence:
                                return first_sentence.strip()
            
            # Fallback to timestamp
            from datetime import datetime
            return f"Chat_{datetime.now().strftime('%Y%m%d_%H%M')}"
            
        except Exception:
            from datetime import datetime
            return f"Chat_{datetime.now().strftime('%Y%m%d_%H%M')}"

    def save_conversation_from_display(self, filename):
        """Save conversation from UI display in a format compatible with load.
        
        Extracts the full conversation from the chat display and saves it
        in a clean, readable format that can be loaded back.
        """
        try:
            # Get display content
            self.chat_display["state"] = "normal"
            display_content = self.chat_display.get("1.0", tk.END).strip()
            self.chat_display["state"] = "disabled"
            
            if not display_content:
                return "No messages to save"

            # Create conversation data with metadata
            from datetime import datetime
            conversation_data = {
                "title": filename,
                "model": self.selected_model or "unknown",
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "display_content": display_content  # Store full markdown display
            }

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
                json.dump(conversation_data, f, indent=2, ensure_ascii=False)

            return f"Conversation saved as '{filename}'"

        except Exception as e:
            return f"Error saving conversation: {str(e)}"

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

            # Validate that we have actual content to save
            if not clean_conversation:
                return "Error: No valid conversation content to save (all messages were filtered out)"

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
        """Load a conversation by its name.
        
        Supports both new format (display_content) and legacy format (messages array)
        for backward compatibility with existing saved conversations.
        """
        try:
            # Construct the filepath
            filepath = os.path.join(self.conversation_manager.conversations_dir, f"{conversation_name}.json")

            # Check if the file exists
            if not os.path.exists(filepath):
                messagebox.showerror("Error", f"Conversation file not found: {conversation_name}")
                return

            # Load the JSON data
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Clear the chat display first
            self.chat_display["state"] = "normal"
            self.chat_display.delete(1.0, tk.END)
            
            # Check if this is the new format (has display_content)
            if "display_content" in data:
                # NEW FORMAT: Just insert the saved display content
                self.chat_display.insert("1.0", data["display_content"])
                
                # Update model if saved
                if data.get("model") and data["model"] in self.model_selector["values"]:
                    self.model_selector.set(data["model"])
                    self.selected_model = data["model"]
                    
                self.display_message(f"\nLoaded conversation: {data.get('title', conversation_name)}\n", "status")
                
            else:
                # LEGACY FORMAT: Load using conversation_manager for backward compatibility
                conversation = self.conversation_manager.load_conversation(filepath)
                
                if conversation:
                    # Update model if it was saved with the conversation
                    if conversation.model and conversation.model in self.model_selector["values"]:
                        self.model_selector.set(conversation.model)
                        self.selected_model = conversation.model

                    # Render the conversation in the chat display using the old method
                    self.conversation_manager.render_conversation(self.chat_display, {
                        'user': {'foreground': '#6699CC'},
                        'assistant': {'foreground': '#99CC99'},
                        'system': {'foreground': '#CC9999'},
                        'error': {'foreground': '#FF6666'},
                        'status': {'foreground': '#999999'},
                        'code': {'font': ('Consolas', 12), 'background': '#2A2A2A', 'foreground': '#E0E0E0'}
                    })

                    self.display_message(f"\nLoaded conversation: {conversation.title}\n", "status")
            
            self.chat_display["state"] = "disabled"
            
            # Update the conversations list
            self.update_conversations_list()
            
        except Exception as e:
            self.chat_display["state"] = "disabled"
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

        # Clear agent cache and reset agent mode
        if hasattr(self, 'agent_cache'):
            self.agent_cache.clear_agent_cache()

        if hasattr(self, 'armed_agents'):
            self.armed_agents = []

        if hasattr(self, 'agent_mode_var'):
            self.agent_mode_var.set(False)

        if hasattr(self, 'active_agent_sequence_name'):
            self.active_agent_sequence_name = None

        # Update Configure Agents button state
        if hasattr(self, 'configure_agents_button') and self.configure_agents_button:
            self.configure_agents_button.config(state="disabled")

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

        # Make it modal (set transient first, grab_set after window is visible)
        view_window.transient(parent_window)

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
        
        # Now that all widgets are created, make the window visible and grab focus
        # This needs to be done after all widgets are packed for Linux/X11 compatibility
        view_window.update_idletasks()  # Ensure window is fully laid out
        view_window.deiconify()  # Make sure it's visible
        try:
            view_window.grab_set()  # Now safe to grab focus
        except Exception:
            pass  # If grab fails, continue anyway (window will still work)

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
        # Persist window geometry and sash position
        try:
            # Record maximized state and geometry
            is_max = (self.root.state() == 'zoomed')
            geom = self.root.winfo_geometry()
            self.settings.set("window_maximized", is_max)
            self.settings.set("window_geometry", geom)
            try:
                sash = self.main_frame.sashpos(0)
                self.settings.set("sash_pos", sash)
            except Exception:
                pass
        except Exception:
            pass

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
