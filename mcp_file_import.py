"""
File import module for the MCP UI.
This module provides functionality to import various file types as memories using markitdown.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from typing import Optional, Callable, Dict, Any
from markitdown import MarkItDown
import tempfile

class MCPFileImporter:
    """File importer for the MCP UI."""

    def __init__(self, parent, mcp_manager, bg_color, fg_color, accent_color, secondary_bg):
        """Initialize the file importer.

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
        """Show a dialog while processing the file.

        Args:
            file_path: Path to the file to process
        """
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
        """Show a preview dialog with the converted content.

        Args:
            file_path: Path to the original file
            result: MarkItDown conversion result
        """
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
        """Suggest tags based on file type and content.

        Args:
            file_path: Path to the file
            content: Converted content

        Returns:
            List of suggested tags
        """
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
        # This could be enhanced with more sophisticated NLP techniques
        keywords = ['python', 'javascript', 'java', 'code', 'algorithm', 'data', 'analysis',
                   'research', 'project', 'report', 'meeting', 'notes', 'summary', 'review']

        for keyword in keywords:
            if keyword.lower() in content.lower():
                tags.append(keyword)

        # Limit to top 5 content-based tags to avoid clutter
        return list(set(tags))[:8]

    def save_as_memory(self, title, content, tags, dialog):
        """Save the content as a memory.

        Args:
            title: Memory title
            content: Memory content
            tags: Memory tags
            dialog: Dialog to close after saving
        """
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
        """Show dialog for splitting content into multiple memories.

        Args:
            title: Memory title
            content: Content to split
            tags: Memory tags
            parent_dialog: Parent dialog to close after saving
        """
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
        """Split content and save as multiple memories.

        Args:
            title: Memory title
            content: Content to split
            tags: Memory tags
            method: Split method (paragraphs, headings, chunks)
            chunk_size: Maximum chunk size
            split_dialog: Split dialog to close after saving
            parent_dialog: Parent dialog to close after saving
        """
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
        """Split content into chunks.

        Args:
            content: Content to split
            method: Split method (paragraphs, headings, chunks)
            chunk_size: Maximum chunk size

        Returns:
            List of content chunks
        """
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
