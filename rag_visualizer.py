import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Tuple, Any, Optional
import os
import re

class RAGVisualizerPanel:
    """Panel for visualizing RAG results and sources."""
    
    def __init__(self, parent_window):
        """Initialize the RAG visualizer panel."""
        self.window = tk.Toplevel(parent_window)
        self.window.title("RAG Visualization")
        self.window.geometry("800x600")
        self.window.withdraw()  # Hide initially
        
        # Create the notebook for multiple tabs
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create the chunks tab
        self.chunks_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.chunks_frame, text="Retrieved Chunks")
        
        # Create the sources tab
        self.sources_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.sources_frame, text="Source Files")
        
        # Create the metrics tab
        self.metrics_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.metrics_frame, text="Metrics")
        
        self._setup_chunks_tab()
        self._setup_sources_tab()
        self._setup_metrics_tab()
        
        # List to track highlighted text tags
        self.highlight_tags = []
        
    def _setup_chunks_tab(self):
        """Set up the chunks tab with a text widget for displaying retrieved chunks."""
        # Main frame for chunks list and details
        chunks_main_frame = ttk.Frame(self.chunks_frame)
        chunks_main_frame.pack(fill='both', expand=True)
        
        # Left side: Chunk list
        chunks_list_frame = ttk.Frame(chunks_main_frame)
        chunks_list_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        ttk.Label(chunks_list_frame, text="Retrieved Chunks").pack(side='top', anchor='w')
        
        self.chunks_listbox = tk.Listbox(chunks_list_frame, selectmode=tk.SINGLE)
        self.chunks_listbox.pack(side='left', fill='both', expand=True)
        chunks_scrollbar = ttk.Scrollbar(chunks_list_frame, orient="vertical", command=self.chunks_listbox.yview)
        chunks_scrollbar.pack(side='right', fill='y')
        self.chunks_listbox.config(yscrollcommand=chunks_scrollbar.set)
        self.chunks_listbox.bind('<<ListboxSelect>>', self._on_chunk_selected)
        
        # Right side: Chunk details
        chunk_details_frame = ttk.Frame(chunks_main_frame)
        chunk_details_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)
        
        ttk.Label(chunk_details_frame, text="Chunk Details").pack(side='top', anchor='w')
        
        self.chunk_details = tk.Text(chunk_details_frame, wrap='word', height=20)
        self.chunk_details.pack(side='left', fill='both', expand=True)
        details_scrollbar = ttk.Scrollbar(chunk_details_frame, orient="vertical", command=self.chunk_details.yview)
        details_scrollbar.pack(side='right', fill='y')
        self.chunk_details.config(yscrollcommand=details_scrollbar.set)
        
    def _setup_sources_tab(self):
        """Set up the sources tab with a treeview widget."""
        # Create treeview for source files
        self.sources_tree = ttk.Treeview(self.sources_frame, columns=("file", "chunks", "relevance"))
        self.sources_tree.heading("#0", text="ID")
        self.sources_tree.heading("file", text="File")
        self.sources_tree.heading("chunks", text="Chunks")
        self.sources_tree.heading("relevance", text="Relevance")
        self.sources_tree.column("#0", width=50)
        self.sources_tree.column("file", width=300)
        self.sources_tree.column("chunks", width=100)
        self.sources_tree.column("relevance", width=100)
        
        # Add scrollbar for treeview
        sources_scrollbar = ttk.Scrollbar(self.sources_frame, orient="vertical", command=self.sources_tree.yview)
        self.sources_tree.configure(yscrollcommand=sources_scrollbar.set)
        
        sources_scrollbar.pack(side='right', fill='y')
        self.sources_tree.pack(fill='both', expand=True)
        
    def _setup_metrics_tab(self):
        """Set up the metrics tab with visualizations of RAG metrics."""
        metrics_controls = ttk.Frame(self.metrics_frame)
        metrics_controls.pack(fill='x', expand=False, padx=5, pady=5)
        
        ttk.Label(metrics_controls, text="RAG Performance Metrics").pack(side='left')
        
        # Stats frame
        stats_frame = ttk.LabelFrame(self.metrics_frame, text="Statistics")
        stats_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Grid layout for statistics
        row = 0
        for metric in ["Total Chunks", "Retrieved Chunks", "Avg. Relevance Score", "Processing Time", "Embedding Model"]:
            ttk.Label(stats_frame, text=f"{metric}:").grid(row=row, column=0, sticky='w', padx=5, pady=2)
            row += 1
            
        # Create variables for the metrics
        self.total_chunks_var = tk.StringVar(value="0")
        self.retrieved_chunks_var = tk.StringVar(value="0")
        self.avg_relevance_var = tk.StringVar(value="0.0")
        self.processing_time_var = tk.StringVar(value="0.0 ms")
        self.embedding_model_var = tk.StringVar(value="N/A")
        
        # Add the values
        ttk.Label(stats_frame, textvariable=self.total_chunks_var).grid(row=0, column=1, sticky='w', padx=5, pady=2)
        ttk.Label(stats_frame, textvariable=self.retrieved_chunks_var).grid(row=1, column=1, sticky='w', padx=5, pady=2)
        ttk.Label(stats_frame, textvariable=self.avg_relevance_var).grid(row=2, column=1, sticky='w', padx=5, pady=2)
        ttk.Label(stats_frame, textvariable=self.processing_time_var).grid(row=3, column=1, sticky='w', padx=5, pady=2)
        ttk.Label(stats_frame, textvariable=self.embedding_model_var).grid(row=4, column=1, sticky='w', padx=5, pady=2)
        
    def _on_chunk_selected(self, event):
        """Handle chunk selection in the listbox."""
        selection = event.widget.curselection()
        if selection:
            index = selection[0]
            chunk_data = self.chunks_data[index]
            
            # Clear the details text
            self.chunk_details.delete(1.0, tk.END)
            
            # Insert chunk details
            self.chunk_details.insert(tk.END, f"Chunk #{index+1}\n", "heading")
            self.chunk_details.insert(tk.END, f"Relevance Score: {chunk_data.get('score', 'N/A')}\n", "metadata")
            self.chunk_details.insert(tk.END, f"Source: {chunk_data.get('source', 'Unknown')}\n\n", "metadata")
            self.chunk_details.insert(tk.END, chunk_data.get('text', 'No content'), "content")
            
            # Configure tags
            self.chunk_details.tag_configure("heading", font=("Arial", 12, "bold"))
            self.chunk_details.tag_configure("metadata", font=("Arial", 10, "italic"))
            self.chunk_details.tag_configure("content", font=("Arial", 11))
    
    def update_chunks(self, chunks_data: List[Dict[str, Any]]):
        """Update the chunks tab with new data."""
        # Clear previous data
        self.chunks_listbox.delete(0, tk.END)
        self.chunk_details.delete(1.0, tk.END)
        self.chunks_data = chunks_data
        
        # Add new chunks to listbox
        for i, chunk in enumerate(chunks_data):
            text_preview = chunk.get('text', 'No content')[:50] + "..." if len(chunk.get('text', '')) > 50 else chunk.get('text', 'No content')
            self.chunks_listbox.insert(tk.END, f"Chunk {i+1}: {text_preview}")
            
        # Update stats
        self.total_chunks_var.set(str(chunks_data[0].get('total_chunks', 0)) if chunks_data else "0")
        self.retrieved_chunks_var.set(str(len(chunks_data)))
        
        # Calculate average relevance score
        if chunks_data:
            scores = [chunk.get('score', 0) for chunk in chunks_data]
            avg_score = sum(scores) / len(scores) if scores else 0
            self.avg_relevance_var.set(f"{avg_score:.4f}")
        else:
            self.avg_relevance_var.set("0.0")
            
    def update_sources(self, sources_data: List[Dict[str, Any]]):
        """Update the sources tab with new data."""
        # Clear previous data
        for item in self.sources_tree.get_children():
            self.sources_tree.delete(item)
            
        # Add new source data
        for i, source in enumerate(sources_data):
            file_name = os.path.basename(source.get('file', 'Unknown'))
            chunks_count = source.get('chunk_count', 0)
            relevance = f"{source.get('relevance', 0.0):.4f}"
            
            self.sources_tree.insert("", tk.END, text=str(i+1),
                                   values=(file_name, chunks_count, relevance))
            
    def update_metrics(self, metrics_data: Dict[str, Any]):
        """Update the metrics tab with new data."""
        self.processing_time_var.set(f"{metrics_data.get('processing_time', 0.0):.2f} ms")
        self.embedding_model_var.set(metrics_data.get('embedding_model', 'N/A'))
        
    def show(self):
        """Show the RAG visualizer panel."""
        self.window.deiconify()
        self.window.lift()
        
    def hide(self):
        """Hide the RAG visualizer panel."""
        self.window.withdraw()
        
    def highlight_rag_matches(self, text_widget: tk.Text, query: str, rag_results: List[Dict[str, Any]]):
        """Highlight RAG matches in a text widget."""
        # Clear previous highlights
        for tag in self.highlight_tags:
            text_widget.tag_delete(tag)
        self.highlight_tags = []
        
        # Create a new tag for RAG highlights
        tag_name = f"rag_highlight_{len(self.highlight_tags)}"
        text_widget.tag_configure(tag_name, background="#FFFF00", foreground="#000000")
        self.highlight_tags.append(tag_name)
        
        # For each RAG chunk, find and highlight matches in the text
        for chunk in rag_results:
            chunk_text = chunk.get('text', '')
            if not chunk_text:
                continue
                
            # Try to find the chunk in the text
            start_idx = "1.0"
            while True:
                match_start = text_widget.search(chunk_text[:50], start_idx, stopindex=tk.END)
                if not match_start:
                    break
                    
                line, col = map(int, match_start.split('.'))
                match_end = f"{line}.{col + len(chunk_text)}"
                text_widget.tag_add(tag_name, match_start, match_end)
                
                # Move start position for next search
                start_idx = match_end
