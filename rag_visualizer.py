import tkinter as tk
from tkinter import ttk
import re
from typing import Dict, List, Any, Optional
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

class RAGVisualizerPanel:
    """Visualization panel for RAG system showing chunks and their relevance."""
    
    def __init__(self, parent):
        """Initialize the visualizer panel."""
        self.parent = parent
        self.window = None
        self.chunks = []
        self.metrics = {}
        self.sources = []
        
    def show(self):
        """Show the RAG visualizer window."""
        if self.window is None or not self.window.winfo_exists():
            self.create_window()
        else:
            self.window.lift()
            
    def create_window(self):
        """Create the RAG visualizer window."""
        self.window = tk.Toplevel(self.parent)
        self.window.title("RAG Visualization")
        self.window.geometry("800x600")
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.chunks_tab = ttk.Frame(self.notebook)
        self.sources_tab = ttk.Frame(self.notebook)
        self.metrics_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.chunks_tab, text="Chunks")
        self.notebook.add(self.sources_tab, text="Sources")
        self.notebook.add(self.metrics_tab, text="Metrics")
        
        # Setup the chunks tab
        self.setup_chunks_tab()
        
        # Setup the sources tab
        self.setup_sources_tab()
        
        # Setup the metrics tab
        self.setup_metrics_tab()
        
        # Update the display with current data
        self.update_display()
    
    def setup_chunks_tab(self):
        """Set up the chunks tab with a treeview."""
        # Create the treeview
        self.chunks_tree = ttk.Treeview(self.chunks_tab, columns=("score", "source", "length"), show="headings")
        self.chunks_tree.heading("score", text="Relevance Score")
        self.chunks_tree.heading("source", text="Source")
        self.chunks_tree.heading("length", text="Length")
        
        # Add scrollbars
        scroll_y = ttk.Scrollbar(self.chunks_tab, orient="vertical", command=self.chunks_tree.yview)
        scroll_x = ttk.Scrollbar(self.chunks_tab, orient="horizontal", command=self.chunks_tree.xview)
        self.chunks_tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        
        # Layout
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.chunks_tree.pack(fill=tk.BOTH, expand=True)
        
        # Add details frame for selected chunk
        self.chunk_details_frame = ttk.LabelFrame(self.chunks_tab, text="Chunk Details")
        self.chunk_details_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.chunk_text = tk.Text(self.chunk_details_frame, wrap=tk.WORD, height=10)
        self.chunk_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bind selection event
        self.chunks_tree.bind("<<TreeviewSelect>>", self.on_chunk_selected)
    
    def setup_sources_tab(self):
        """Set up the sources tab with a visualization."""
        # Create a figure for matplotlib
        self.sources_figure = plt.Figure(figsize=(6, 4), dpi=100)
        self.sources_ax = self.sources_figure.add_subplot(111)
        
        # Create canvas
        self.sources_canvas = FigureCanvasTkAgg(self.sources_figure, self.sources_tab)
        self.sources_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add explanation text
        self.sources_info = ttk.Label(
            self.sources_tab, 
            text="This graph shows the source files and their relevance to the query.",
            wraplength=600
        )
        self.sources_info.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_metrics_tab(self):
        """Set up the metrics tab to display performance metrics."""
        # Create frame for metrics
        self.metrics_frame = ttk.Frame(self.metrics_tab)
        self.metrics_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Processing time
        ttk.Label(self.metrics_frame, text="Processing Time:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.processing_time_label = ttk.Label(self.metrics_frame, text="N/A")
        self.processing_time_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Embedding model
        ttk.Label(self.metrics_frame, text="Embedding Model:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.embedding_model_label = ttk.Label(self.metrics_frame, text="N/A")
        self.embedding_model_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Chunk count
        ttk.Label(self.metrics_frame, text="Total Chunks:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.total_chunks_label = ttk.Label(self.metrics_frame, text="N/A")
        self.total_chunks_label.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Average score
        ttk.Label(self.metrics_frame, text="Average Relevance:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.avg_relevance_label = ttk.Label(self.metrics_frame, text="N/A")
        self.avg_relevance_label.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
    
    def update_chunks(self, chunks: List[Dict[str, Any]]):
        """Update the chunks data."""
        self.chunks = chunks
        if self.window and self.window.winfo_exists():
            self.update_display()
    
    def update_metrics(self, metrics: Dict[str, Any]):
        """Update the metrics data."""
        self.metrics = metrics
        if self.window and self.window.winfo_exists():
            self.update_metrics_display()
    
    def update_sources(self, sources: List[Dict[str, Any]]):
        """Update the sources data."""
        self.sources = sources
        if self.window and self.window.winfo_exists():
            self.update_sources_display()
    
    def update_display(self):
        """Update all displays with current data."""
        self.update_chunks_display()
        self.update_sources_display()
        self.update_metrics_display()
    
    def update_chunks_display(self):
        """Update the chunks tree with current data."""
        if not hasattr(self, 'chunks_tree'):
            return
            
        # Clear existing items
        for item in self.chunks_tree.get_children():
            self.chunks_tree.delete(item)
        
        # Add new items
        for idx, chunk in enumerate(self.chunks):
            score = chunk.get('score', 0)
            source = chunk.get('source', 'Unknown')
            text = chunk.get('text', '')
            
            # Format the score for display
            score_str = f"{score:.3f}" if isinstance(score, (int, float)) else str(score)
            
            self.chunks_tree.insert(
                "", 
                "end", 
                iid=idx, 
                values=(score_str, source, len(text)),
                tags=(f"chunk{idx}",)
            )
    
    def update_sources_display(self):
        """Update the sources visualization."""
        if not hasattr(self, 'sources_ax') or not self.sources:
            return
            
        # Clear the figure
        self.sources_ax.clear()
        
        # Extract data
        source_names = [s.get('file', 'Unknown') for s in self.sources]
        relevances = [s.get('relevance', 0) for s in self.sources]
        chunk_counts = [s.get('chunk_count', 0) for s in self.sources]
        
        # Calculate positions and width
        x = np.arange(len(source_names))
        width = 0.35
        
        # Create bars
        relevance_bars = self.sources_ax.bar(x - width/2, relevances, width, label='Relevance', color='#6699cc')
        count_bars = self.sources_ax.bar(x + width/2, chunk_counts, width, label='Chunks', color='#99cc99')
        
        # Add labels and title
        self.sources_ax.set_title('Source Files Relevance and Chunk Count')
        self.sources_ax.set_xlabel('Source Files')
        self.sources_ax.set_xticks(x)
        self.sources_ax.set_xticklabels(source_names, rotation=45, ha='right')
        self.sources_ax.legend()
        
        # Add value labels on top of bars
        for bar in relevance_bars:
            height = bar.get_height()
            self.sources_ax.text(
                bar.get_x() + bar.get_width() / 2.,
                height + 0.02,
                f'{height:.2f}',
                ha='center', va='bottom', fontsize=8
            )
        
        for bar in count_bars:
            height = bar.get_height()
            self.sources_ax.text(
                bar.get_x() + bar.get_width() / 2.,
                height + 0.02,
                f'{int(height)}',
                ha='center', va='bottom', fontsize=8
            )
        
        # Adjust layout
        self.sources_figure.tight_layout()
        
        # Refresh canvas
        self.sources_canvas.draw()
    
    def update_metrics_display(self):
        """Update the metrics display with current data."""
        if not hasattr(self, 'processing_time_label'):
            return
            
        # Update processing time
        processing_time = self.metrics.get('processing_time', 'N/A')
        if isinstance(processing_time, (int, float)):
            self.processing_time_label.config(text=f"{processing_time:.2f} ms")
        else:
            self.processing_time_label.config(text=str(processing_time))
        
        # Update embedding model
        embedding_model = self.metrics.get('embedding_model', 'N/A')
        self.embedding_model_label.config(text=str(embedding_model))
        
        # Update total chunks
        if self.chunks and len(self.chunks) > 0 and 'total_chunks' in self.chunks[0]:
            self.total_chunks_label.config(text=str(self.chunks[0]['total_chunks']))
        elif self.chunks:
            self.total_chunks_label.config(text=str(len(self.chunks)))
        else:
            self.total_chunks_label.config(text="0")
        
        # Update average relevance
        if self.chunks:
            scores = [chunk.get('score', 0) for chunk in self.chunks if 'score' in chunk]
            if scores:
                avg_score = sum(scores) / len(scores)
                self.avg_relevance_label.config(text=f"{avg_score:.3f}")
            else:
                self.avg_relevance_label.config(text="N/A")
        else:
            self.avg_relevance_label.config(text="N/A")
    
    def on_chunk_selected(self, event):
        """Handler for when a chunk is selected in the treeview."""
        selected_id = self.chunks_tree.selection()
        if selected_id:
            idx = int(selected_id[0])
            if idx < len(self.chunks):
                chunk = self.chunks[idx]
                self.chunk_text.delete('1.0', tk.END)
                self.chunk_text.insert('1.0', chunk.get('text', 'No text available'))
    
    def highlight_rag_matches(self, text_widget, query, rag_results):
        """Highlight potential matches between query and RAG chunks in the response."""
        if not rag_results:
            return
            
        # Extract all words from the query (excluding common words)
        stop_words = {'the', 'and', 'is', 'in', 'to', 'a', 'of', 'for', 'with', 'by', 'as', 'on', 'at'}
        query_words = set()
        for word in re.findall(r'\b\w+\b', query.lower()):
            if len(word) > 3 and word not in stop_words:
                query_words.add(word)
        
        # Extract all important phrases from RAG chunks
        rag_phrases = set()
        for chunk in rag_results:
            text = chunk.get('text', '')
            # Split into sentences to find key phrases
            sentences = text.split('.')
            for sentence in sentences:
                if len(sentence.strip()) > 10:  # Skip very short sentences
                    rag_phrases.add(sentence.strip().lower())
        
        # Try to find these key phrases in the response
        # NOTE: This is a simple implementation and may miss some matches
        # A more sophisticated approach would use semantic matching
        
        try:
            # Make text widget temporarily editable
            text_widget_state = text_widget.cget('state')
            text_widget.config(state=tk.NORMAL)
            
            # Get full text
            full_text = text_widget.get("1.0", tk.END).lower()
            
            # Search for important query words and highlight them
            for word in query_words:
                if len(word) < 4:  # Skip very short words
                    continue
                    
                # Find all occurrences
                start_pos = "1.0"
                while True:
                    start_pos = text_widget.search(word, start_pos, tk.END, nocase=True)
                    if not start_pos:
                        break
                    
                    end_pos = f"{start_pos}+{len(word)}c"
                    text_widget.tag_add("rag_match", start_pos, end_pos)
                    start_pos = end_pos
                    
            # Configure the tag
            text_widget.tag_configure("rag_match", background="#555555")
            
        finally:
            # Restore original state
            text_widget.config(state=text_widget_state)
