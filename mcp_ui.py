"""
MCP UI - Consolidated UI Module
================================

This module consolidates all MCP UI functionality from:
- mcp_ui.py (Base MCPPanel class)
- mcp_ui_enhanced.py (Enhanced panel wrapper)
- mcp_file_import.py (File import functionality)

Maintains 100% backward compatibility while reducing file count.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import threading
import time
import tempfile
from typing import Callable, Dict, List, Optional, Any
from datetime import datetime
from markitdown import MarkItDown


# =============================================================================
# FILE IMPORT FUNCTIONALITY
# =============================================================================

class MCPFileImporter:
    """File importer for the MCP UI."""

    def __init__(self, parent, mcp_manager, bg_color, fg_color, accent_color, secondary_bg):
        """Initialize the file importer."""
        self.parent = parent
        self.mcp_manager = mcp_manager
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.accent_color = accent_color
        self.secondary_bg = secondary_bg

        # Initialize markitdown
        self.md = MarkItDown()

        # Supported file types
        self.file_types = [
            ("All supported files", "*.txt *.md *.pdf *.docx *.doc *.rtf *.html *.htm *.pptx *.ppt *.xlsx *.xls *.csv *.json *.xml *.py *.js *.java *.c *.cpp *.h *.cs *.php *.rb *.go *.rs *.swift *.kt *.ts *.mp3 *.wav *.mp4 *.avi *.mov *.jpg *.jpeg *.png *.gif *.bmp *.tiff *.zip"),
            ("Text files", "*.txt"),
            ("Markdown files", "*.md"),
            ("PDF files", "*.pdf"),
            ("Word documents", "*.docx *.doc"),
            ("HTML files", "*.html *.htm"),
            ("PowerPoint presentations", "*.pptx *.ppt"),
            ("Excel spreadsheets", "*.xlsx *.xls *.csv"),
            ("Code files", "*.py *.js *.java *.c *.cpp *.h *.cs *.php *.rb *.go *.rs *.swift *.kt *.ts"),
            ("Audio files", "*.mp3 *.wav"),
            ("Video files", "*.mp4 *.avi *.mov"),
            ("Image files", "*.jpg *.jpeg *.png *.gif *.bmp *.tiff"),
            ("Archive files", "*.zip"),
            ("All files", "*.*")
        ]

    def show_import_dialog(self):
        """Show the file import dialog."""
        # Ask user to select a file
        file_path = filedialog.askopenfilename(
            title="Select File to Import as Memory",
            filetypes=self.file_types,
            parent=self.parent
        )

        if not file_path:
            return  # User cancelled

        # Show processing dialog
        self.show_processing_dialog(file_path)

    def show_processing_dialog(self, file_path):
        """Show a dialog while processing the file."""
        # Create processing dialog
        processing_dialog = tk.Toplevel(self.parent)
        processing_dialog.title("Processing File")
        processing_dialog.geometry("300x100")
        processing_dialog.transient(self.parent)
        processing_dialog.grab_set()
        processing_dialog.configure(background=self.bg_color)

        # Add processing message
        ttk.Label(
            processing_dialog,
            text=f"Processing {os.path.basename(file_path)}...",
            background=self.bg_color,
            foreground=self.fg_color
        ).pack(pady=10)

        # Add progress bar
        progress = ttk.Progressbar(processing_dialog, mode="indeterminate")
        progress.pack(fill=tk.X, padx=20, pady=10)
        progress.start()

        # Process file in a separate thread
        def process_thread():
            try:
                # Convert file to markdown
                result = self.md.convert(file_path)

                # Close processing dialog
                processing_dialog.after(0, processing_dialog.destroy)

                # Show preview dialog
                self.show_preview_dialog(file_path, result)
            except Exception as e:
                # Close processing dialog
                processing_dialog.after(0, processing_dialog.destroy)

                # Show error message
                messagebox.showerror(
                    "Error",
                    f"Error processing file: {str(e)}",
                    parent=self.parent
                )

        # Start processing thread
        threading.Thread(target=process_thread, daemon=True).start()

    def show_preview_dialog(self, file_path, result):
        """Show a preview dialog with the converted content."""
        # Create preview dialog
        preview_dialog = tk.Toplevel(self.parent)
        preview_dialog.title(f"Memory Preview: {os.path.basename(file_path)}")
        preview_dialog.geometry("800x600")
        preview_dialog.transient(self.parent)
        preview_dialog.grab_set()
        preview_dialog.configure(background=self.bg_color)

        # Create main frame
        main_frame = ttk.Frame(preview_dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Add title field
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            title_frame,
            text="Memory Title:",
            width=15
        ).pack(side=tk.LEFT)

        title_var = tk.StringVar(value=os.path.basename(file_path))
        title_entry = ttk.Entry(
            title_frame,
            textvariable=title_var,
            width=50
        )
        title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Add content field
        content_frame = ttk.LabelFrame(main_frame, text="Memory Content")
        content_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(content_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add text widget
        content_text = tk.Text(
            content_frame,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            bg=self.secondary_bg,
            fg=self.fg_color,
            font=("Segoe UI", 10)
        )
        content_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=content_text.yview)

        # Insert content
        content_text.insert(tk.END, result.text_content)

        # Add tags field
        tags_frame = ttk.Frame(main_frame)
        tags_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            tags_frame,
            text="Tags (comma-separated):",
            width=15
        ).pack(side=tk.LEFT)

        # Generate suggested tags based on file type and content
        suggested_tags = self.suggest_tags(file_path, result.text_content)

        tags_var = tk.StringVar(value=", ".join(suggested_tags))
        tags_entry = ttk.Entry(
            tags_frame,
            textvariable=tags_var,
            width=50
        )
        tags_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Add buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(
            button_frame,
            text="Cancel",
            command=preview_dialog.destroy
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            button_frame,
            text="Save as Memory",
            command=lambda: self.save_as_memory(
                title_var.get(),
                content_text.get(1.0, tk.END),
                tags_var.get().split(","),
                preview_dialog
            )
        ).pack(side=tk.RIGHT, padx=5)

        # Add split options for large content
        if len(result.text_content) > 2000:
            ttk.Button(
                button_frame,
                text="Split into Multiple Memories",
                command=lambda: self.show_split_dialog(
                    title_var.get(),
                    result.text_content,
                    tags_var.get().split(","),
                    preview_dialog
                )
            ).pack(side=tk.RIGHT, padx=5)

    def suggest_tags(self, file_path, content):
        """Suggest tags based on file type and content."""
        tags = []

        # Add file type tag
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext:
            tags.append(file_ext[1:])  # Remove the dot

        # Add file category tag
        if file_ext in ['.txt', '.md']:
            tags.append('text')
        elif file_ext in ['.pdf', '.docx', '.doc', '.rtf']:
            tags.append('document')
        elif file_ext in ['.html', '.htm']:
            tags.append('web')
        elif file_ext in ['.pptx', '.ppt']:
            tags.append('presentation')
        elif file_ext in ['.xlsx', '.xls', '.csv']:
            tags.append('spreadsheet')
        elif file_ext in ['.py', '.js', '.java', '.c', '.cpp', '.h', '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.ts']:
            tags.append('code')
        elif file_ext in ['.mp3', '.wav']:
            tags.append('audio')
        elif file_ext in ['.mp4', '.avi', '.mov']:
            tags.append('video')
        elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
            tags.append('image')
        elif file_ext in ['.zip']:
            tags.append('archive')

        # Add content-based tags (simple keyword extraction)
        keywords = ['python', 'javascript', 'java', 'code', 'algorithm', 'data', 'analysis',
                   'research', 'project', 'report', 'meeting', 'notes', 'summary', 'review']

        for keyword in keywords:
            if keyword.lower() in content.lower():
                tags.append(keyword)

        # Limit to top 8 tags to avoid clutter
        return list(set(tags))[:8]

    def save_as_memory(self, title, content, tags, dialog):
        """Save the content as a memory."""
        # Clean up tags
        clean_tags = [tag.strip() for tag in tags if tag.strip()]

        # Add title to the content
        formatted_content = f"# {title}\n\n{content}"

        # Add memory
        memory_id = self.mcp_manager.add_memory(formatted_content, clean_tags)

        if memory_id:
            messagebox.showinfo(
                "Success",
                "File content saved as memory successfully.",
                parent=self.parent
            )
            dialog.destroy()
        else:
            messagebox.showerror(
                "Error",
                "Failed to save memory. Make sure the MCP server is running.",
                parent=self.parent
            )

    def show_split_dialog(self, title, content, tags, parent_dialog):
        """Show dialog for splitting content into multiple memories."""
        # Create split dialog
        split_dialog = tk.Toplevel(self.parent)
        split_dialog.title("Split into Multiple Memories")
        split_dialog.geometry("400x300")
        split_dialog.transient(parent_dialog)
        split_dialog.grab_set()
        split_dialog.configure(background=self.bg_color)

        # Create main frame
        main_frame = ttk.Frame(split_dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Add split method options
        method_frame = ttk.LabelFrame(main_frame, text="Split Method")
        method_frame.pack(fill=tk.X, pady=5)

        split_method = tk.StringVar(value="paragraphs")

        ttk.Radiobutton(
            method_frame,
            text="Split by Paragraphs",
            variable=split_method,
            value="paragraphs"
        ).pack(anchor=tk.W, padx=10, pady=5)

        ttk.Radiobutton(
            method_frame,
            text="Split by Headings",
            variable=split_method,
            value="headings"
        ).pack(anchor=tk.W, padx=10, pady=5)

        ttk.Radiobutton(
            method_frame,
            text="Split into Equal Chunks",
            variable=split_method,
            value="chunks"
        ).pack(anchor=tk.W, padx=10, pady=5)

        # Add chunk size option
        size_frame = ttk.Frame(main_frame)
        size_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            size_frame,
            text="Maximum chunk size (characters):"
        ).pack(side=tk.LEFT, padx=5)

        chunk_size = tk.IntVar(value=1000)
        chunk_size_entry = ttk.Spinbox(
            size_frame,
            from_=100,
            to=5000,
            increment=100,
            textvariable=chunk_size,
            width=10
        )
        chunk_size_entry.pack(side=tk.LEFT, padx=5)

        # Add buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(
            button_frame,
            text="Cancel",
            command=split_dialog.destroy
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            button_frame,
            text="Split and Save",
            command=lambda: self.split_and_save(
                title,
                content,
                tags,
                split_method.get(),
                chunk_size.get(),
                split_dialog,
                parent_dialog
            )
        ).pack(side=tk.RIGHT, padx=5)

    def split_and_save(self, title, content, tags, method, chunk_size, split_dialog, parent_dialog):
        """Split content and save as multiple memories."""
        # Split content based on method
        chunks = self.split_content(content, method, chunk_size)

        # Clean up tags
        clean_tags = [tag.strip() for tag in tags if tag.strip()]

        # Add each chunk as a memory
        success_count = 0
        for i, chunk in enumerate(chunks, 1):
            # Add part number to tags
            chunk_tags = clean_tags + [f"part{i}"]

            # Add memory with title and part number
            formatted_chunk = f"# {title} (Part {i})\n\n{chunk}"
            memory_id = self.mcp_manager.add_memory(formatted_chunk, chunk_tags)

            if memory_id:
                success_count += 1

        # Show result
        if success_count > 0:
            messagebox.showinfo(
                "Success",
                f"Content split into {success_count} memories successfully.",
                parent=self.parent
            )
            split_dialog.destroy()
            parent_dialog.destroy()
        else:
            messagebox.showerror(
                "Error",
                "Failed to save memories. Make sure the MCP server is running.",
                parent=self.parent
            )

    def split_content(self, content, method, chunk_size):
        """Split content into chunks."""
        if method == "paragraphs":
            # Split by paragraphs (double newline)
            paragraphs = content.split("\n\n")

            # Combine paragraphs into chunks of appropriate size
            chunks = []
            current_chunk = ""

            for paragraph in paragraphs:
                # If adding this paragraph would exceed chunk size, start a new chunk
                if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = paragraph
                else:
                    if current_chunk:
                        current_chunk += "\n\n" + paragraph
                    else:
                        current_chunk = paragraph

            # Add the last chunk if it's not empty
            if current_chunk:
                chunks.append(current_chunk)

        elif method == "headings":
            # Split by markdown headings (lines starting with #)
            lines = content.split("\n")

            # Find heading lines
            heading_indices = [i for i, line in enumerate(lines) if line.strip().startswith("#")]

            # If no headings found, fall back to paragraph splitting
            if not heading_indices:
                return self.split_content(content, "paragraphs", chunk_size)

            # Create chunks based on headings
            chunks = []
            for i in range(len(heading_indices)):
                start_idx = heading_indices[i]
                end_idx = heading_indices[i+1] if i+1 < len(heading_indices) else len(lines)

                chunk = "\n".join(lines[start_idx:end_idx])
                chunks.append(chunk)

        else:  # chunks
            # Split into equal-sized chunks
            chunks = []
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i+chunk_size]

                # Try to end at a sentence boundary if possible
                if i+chunk_size < len(content):
                    # Find the last sentence boundary in the chunk
                    last_period = chunk.rfind(". ")
                    if last_period > chunk_size * 0.75:  # Only adjust if we're at least 75% through the chunk
                        chunk = content[i:i+last_period+1]
                        i = i + last_period + 1

                chunks.append(chunk)

        return chunks


# =============================================================================
# BASE MCP PANEL
# =============================================================================

class MCPPanel:
    """Base UI panel for MCP functionality."""

    def __init__(self, parent, mcp_manager, bg_color, fg_color, accent_color, secondary_bg):
        """Initialize the MCP panel."""
        self.parent = parent
        self.mcp_manager = mcp_manager
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.accent_color = accent_color
        self.secondary_bg = secondary_bg
        self.cursor_color = "#61AFEF"  # Light blue cursor for better visibility

        # Create file importer
        self.file_importer = MCPFileImporter(parent, mcp_manager, bg_color, fg_color, accent_color, secondary_bg)

        # Create the main frame
        self.frame = ttk.Frame(parent)

        # Create UI components
        self.create_ui()

    def create_ui(self):
        """Create the UI components."""
        # Title
        title_label = ttk.Label(
            self.frame,
            text="Memory Control Program",
            font=("Segoe UI", 14, "bold")
        )
        title_label.pack(pady=10)

        # Server control frame
        server_frame = ttk.LabelFrame(self.frame, text="Server Control")
        server_frame.pack(fill=tk.X, padx=10, pady=5)

        # Server status
        self.status_var = tk.StringVar(value="Server Status: Not Running")
        status_label = ttk.Label(
            server_frame,
            textvariable=self.status_var,
            foreground="red"
        )
        status_label.pack(anchor="w", padx=5, pady=5)

        # Server control buttons
        button_frame = ttk.Frame(server_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        self.start_button = ttk.Button(
            button_frame,
            text="Start Server",
            command=self.start_server
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(
            button_frame,
            text="Stop Server",
            command=self.stop_server,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Memory management frame
        memory_frame = ttk.LabelFrame(self.frame, text="Memory Management")
        memory_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Memory list
        list_frame = ttk.Frame(memory_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create a frame for the listbox and scrollbar
        listbox_frame = ttk.Frame(list_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        # Memory listbox with scrollbar
        self.memory_listbox = tk.Listbox(
            listbox_frame,
            bg=self.secondary_bg,
            fg=self.fg_color,
            selectbackground=self.accent_color,
            selectforeground="#FFFFFF",
            font=("Segoe UI", 10),
            height=10
        )
        self.memory_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.memory_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.memory_listbox.config(yscrollcommand=scrollbar.set)

        # Bind double-click to view memory
        self.memory_listbox.bind("<Double-1>", self.view_memory)

        # Memory content display
        content_frame = ttk.LabelFrame(memory_frame, text="Memory Content")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.content_text = tk.Text(
            content_frame,
            bg=self.secondary_bg,
            fg=self.fg_color,
            font=("Segoe UI", 10),
            wrap=tk.WORD,
            height=6,
            insertbackground=self.cursor_color  # Light blue cursor for better visibility
        )
        self.content_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.content_text.config(state=tk.DISABLED)

        # Memory action buttons
        action_frame = ttk.Frame(memory_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            action_frame,
            text="Add Memory",
            command=self.add_memory
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            action_frame,
            text="Import File",
            command=self.import_file
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            action_frame,
            text="Edit Memory",
            command=self.edit_memory
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            action_frame,
            text="Delete Memory",
            command=self.delete_memory
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            action_frame,
            text="Refresh",
            command=self.refresh_memories
        ).pack(side=tk.LEFT, padx=5)

        # Search frame
        search_frame = ttk.Frame(memory_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ttk.Button(
            search_frame,
            text="Search",
            command=self.search_memories
        ).pack(side=tk.LEFT, padx=5)

        # Create context menu
        self.create_context_menu()

    def create_context_menu(self):
        """Create context menu for the memory listbox."""
        self.context_menu = tk.Menu(self.frame, tearoff=0)
        self.context_menu.add_command(label="View Memory", command=self.view_selected_memory)
        self.context_menu.add_command(label="Edit Memory", command=self.edit_memory)
        self.context_menu.add_command(label="Delete Memory", command=self.delete_memory)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Add Memory", command=self.add_memory)
        self.context_menu.add_command(label="Import File", command=self.import_file)
        self.context_menu.add_command(label="Refresh List", command=self.refresh_memories)

        # Bind right-click to show context menu
        self.memory_listbox.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        """Show the context menu at the current mouse position."""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            # Make sure to release the grab
            self.context_menu.grab_release()

    def start_server(self):
        """Start the MCP server."""
        # Start in a separate thread to avoid blocking the UI
        def start_thread():
            success = self.mcp_manager.start_server()
            if success:
                self.status_var.set("Server Status: Running")
                self.start_button.config(state=tk.DISABLED)
                self.stop_button.config(state=tk.NORMAL)
                self.refresh_memories()

        threading.Thread(target=start_thread, daemon=True).start()

    def stop_server(self):
        """Stop the MCP server."""
        # Stop in a separate thread to avoid blocking the UI
        def stop_thread():
            success = self.mcp_manager.stop_server()
            if success:
                self.status_var.set("Server Status: Not Running")
                self.start_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)

        threading.Thread(target=stop_thread, daemon=True).start()

    def refresh_memories(self):
        """Refresh the memory list."""
        # Clear the listbox
        self.memory_listbox.delete(0, tk.END)

        # Get all memories
        memories = self.mcp_manager.get_all_memories()

        # Add to listbox
        for memory in memories:
            # Truncate content for display
            content = memory.get("content", "")
            if len(content) > 50:
                content = content[:47] + "..."

            # Format display string
            display = f"{content}"

            # Add to listbox
            self.memory_listbox.insert(tk.END, display)

    def view_memory(self, event=None):
        """View the selected memory."""
        self.view_selected_memory()

    def view_selected_memory(self):
        """View the currently selected memory."""
        # Get selected index
        selected = self.memory_listbox.curselection()
        if not selected:
            messagebox.showinfo("Info", "Please select a memory to view")
            return

        # Get all memories
        memories = self.mcp_manager.get_all_memories()

        # Check if index is valid
        if selected[0] >= len(memories):
            messagebox.showerror("Error", "Invalid memory selection")
            return

        # Get the memory
        memory = memories[selected[0]]

        # Display content
        self.content_text.config(state=tk.NORMAL)
        self.content_text.delete(1.0, tk.END)
        self.content_text.insert(tk.END, memory.get("content", ""))
        self.content_text.config(state=tk.DISABLED)

    def add_memory(self):
        """Add a new memory."""
        # Prompt for memory content
        content = simpledialog.askstring(
            "Add Memory",
            "Enter memory content:",
            parent=self.frame
        )

        if not content:
            return

        # Prompt for tags
        tags_str = simpledialog.askstring(
            "Add Memory",
            "Enter tags (comma-separated):",
            parent=self.frame
        )

        tags = []
        if tags_str:
            tags = [tag.strip() for tag in tags_str.split(",")]

        # Add the memory
        memory_id = self.mcp_manager.add_memory(content, tags)

        if memory_id:
            messagebox.showinfo("Success", "Memory added successfully")
            self.refresh_memories()
        else:
            messagebox.showerror("Error", "Failed to add memory")

    def import_file(self):
        """Import a file as a memory."""
        # Show file import dialog
        self.file_importer.show_import_dialog()

        # Refresh memories after import (will be called by the importer)

    def edit_memory(self):
        """Edit the selected memory."""
        # Get selected index
        selected = self.memory_listbox.curselection()
        if not selected:
            messagebox.showinfo("Info", "Please select a memory to edit")
            return

        # Get all memories
        memories = self.mcp_manager.get_all_memories()

        # Check if index is valid
        if selected[0] >= len(memories):
            messagebox.showerror("Error", "Invalid memory selection")
            return

        # Get the memory
        memory = memories[selected[0]]
        memory_id = memory.get("id")

        # Prompt for new content
        content = simpledialog.askstring(
            "Edit Memory",
            "Edit memory content:",
            initialvalue=memory.get("content", ""),
            parent=self.frame
        )

        if content is None:  # User cancelled
            return

        # Prompt for new tags
        current_tags = ", ".join(memory.get("tags", []))
        tags_str = simpledialog.askstring(
            "Edit Memory",
            "Edit tags (comma-separated):",
            initialvalue=current_tags,
            parent=self.frame
        )

        tags = []
        if tags_str:
            tags = [tag.strip() for tag in tags_str.split(",")]

        # Update the memory
        success = self.mcp_manager.update_memory(memory_id, content, tags)

        if success:
            messagebox.showinfo("Success", "Memory updated successfully")
            self.refresh_memories()

            # Update the content display
            self.content_text.config(state=tk.NORMAL)
            self.content_text.delete(1.0, tk.END)
            self.content_text.insert(tk.END, content)
            self.content_text.config(state=tk.DISABLED)
        else:
            messagebox.showerror("Error", "Failed to update memory")

    def delete_memory(self):
        """Delete the selected memory."""
        # Get selected index
        selected = self.memory_listbox.curselection()
        if not selected:
            messagebox.showinfo("Info", "Please select a memory to delete")
            return

        # Get all memories
        memories = self.mcp_manager.get_all_memories()

        # Check if index is valid
        if selected[0] >= len(memories):
            messagebox.showerror("Error", "Invalid memory selection")
            return

        # Get the memory
        memory = memories[selected[0]]
        memory_id = memory.get("id")

        # Confirm deletion
        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete this memory?\n\n{memory.get('content', '')[:100]}..."
        )

        if not confirm:
            return

        # Delete the memory
        success = self.mcp_manager.delete_memory(memory_id)

        if success:
            messagebox.showinfo("Success", "Memory deleted successfully")
            self.refresh_memories()

            # Clear the content display
            self.content_text.config(state=tk.NORMAL)
            self.content_text.delete(1.0, tk.END)
            self.content_text.config(state=tk.DISABLED)
        else:
            messagebox.showerror("Error", "Failed to delete memory")

    def search_memories(self):
        """Search memories by content."""
        # Get search query
        query = self.search_var.get()

        if not query:
            # If empty query, show all memories
            self.refresh_memories()
            return

        # Search memories
        memories = self.mcp_manager.search_memories(query)

        # Clear the listbox
        self.memory_listbox.delete(0, tk.END)

        # Add results to listbox
        for memory in memories:
            # Truncate content for display
            content = memory.get("content", "")
            if len(content) > 50:
                content = content[:47] + "..."

            # Format display string
            display = f"{content}"

            # Add to listbox
            self.memory_listbox.insert(tk.END, display)

        # Show message if no results
        if not memories:
            messagebox.showinfo("Search Results", "No matching memories found")

    def show(self):
        """Show the MCP panel."""
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Update server status
        if self.mcp_manager.is_running:
            self.status_var.set("Server Status: Running")
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
        else:
            self.status_var.set("Server Status: Not Running")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

        # Refresh memories
        self.refresh_memories()

    def hide(self):
        """Hide the MCP panel."""
        self.frame.pack_forget()


# =============================================================================
# ENHANCED MCP PANEL (adds optional advanced features)
# =============================================================================

class MCPPanelEnhanced:
    """
    Enhanced MCP Panel that wraps original functionality.
    Maintains 100% backward compatibility while adding new features.
    """
    
    def __init__(self, parent, mcp_manager, bg_color, fg_color, accent_color, secondary_bg):
        """Initialize enhanced panel with same parameters as original."""
        
        # Store initialization parameters
        self.parent = parent
        self.mcp_manager = mcp_manager
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.accent_color = accent_color
        self.secondary_bg = secondary_bg
        
        # Initialize original panel first (critical for compatibility)
        self.original_panel = MCPPanel(parent, mcp_manager, bg_color, fg_color, accent_color, secondary_bg)
        
        # Enhanced UI state
        self.enhanced_mode = False
        self.enhanced_widgets = {}
        
        # Note: Enhanced mode is disabled by default
        # To enable: call enable_enhanced_mode()
    
    # ==========================================================================
    # BACKWARD COMPATIBLE API (Exact Same Methods)
    # ==========================================================================
    
    def show(self):
        """Show the panel (always uses original for maximum compatibility)."""
        self.original_panel.show()
    
    def hide(self):
        """Hide the panel."""
        self.original_panel.hide()
    
    # ==========================================================================
    # ENHANCED FUNCTIONALITY (Optional - Future Extension Point)
    # ==========================================================================
    
    def enable_enhanced_mode(self):
        """Enable enhanced UI mode (placeholder for future features)."""
        self.enhanced_mode = True
        print("Enhanced UI mode enabled (no additional features implemented yet)")
    
    def disable_enhanced_mode(self):
        """Disable enhanced UI mode (use classic UI)."""
        self.enhanced_mode = False
        print("Enhanced UI mode disabled - using classic UI")
    
    def is_enhanced_mode(self) -> bool:
        """Check if enhanced mode is active."""
        return self.enhanced_mode
