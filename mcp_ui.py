"""
UI components for the MCP (Memory Control Program) functionality.
"""

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import threading
import time
from typing import Callable, Dict, List, Optional, Any
from mcp_file_import import MCPFileImporter

class MCPPanel:
    """UI panel for MCP functionality."""

    def __init__(self, parent, mcp_manager, bg_color, fg_color, accent_color, secondary_bg):
        """Initialize the MCP panel.

        Args:
            parent: The parent tkinter widget
            mcp_manager: The MCP manager instance
            bg_color: Background color
            fg_color: Foreground color
            accent_color: Accent color
            secondary_bg: Secondary background color
        """
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


class MemoryDialog(simpledialog.Dialog):
    """Dialog for adding or editing a memory."""

    def __init__(self, parent, title, initial_content="", initial_tags=None):
        """Initialize the dialog.

        Args:
            parent: The parent widget
            title: Dialog title
            initial_content: Initial content for editing
            initial_tags: Initial tags for editing
        """
        self.initial_content = initial_content
        self.initial_tags = initial_tags or []
        super().__init__(parent, title)

    def body(self, master):
        """Create dialog body.

        Args:
            master: The master widget

        Returns:
            Widget that should have initial focus
        """
        # Content label
        ttk.Label(master, text="Memory Content:").grid(row=0, column=0, sticky="w", padx=5, pady=5)

        # Content text
        self.content_text = tk.Text(master, width=50, height=10, wrap=tk.WORD)
        self.content_text.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self.content_text.insert(tk.END, self.initial_content)

        # Tags label
        ttk.Label(master, text="Tags (comma-separated):").grid(row=2, column=0, sticky="w", padx=5, pady=5)

        # Tags entry
        self.tags_var = tk.StringVar(value=", ".join(self.initial_tags))
        self.tags_entry = ttk.Entry(master, textvariable=self.tags_var, width=50)
        self.tags_entry.grid(row=3, column=0, padx=5, pady=5, sticky="ew")

        # Configure grid
        master.columnconfigure(0, weight=1)
        master.rowconfigure(1, weight=1)

        return self.content_text  # Initial focus

    def apply(self):
        """Process the data when OK is clicked."""
        self.result = {
            "content": self.content_text.get(1.0, tk.END).strip(),
            "tags": [tag.strip() for tag in self.tags_var.get().split(",") if tag.strip()]
        }
