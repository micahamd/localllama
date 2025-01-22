import tkinter as tk
from tkinter import scrolledtext, filedialog, StringVar
import threading
from tkinter import ttk, font
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
from markitdown import MarkItDown
import re
import markdown
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import BBCodeFormatter
import matplotlib.pyplot as plt
import io
from PIL import Image, ImageTk
import ollama
from sentence_transformers import SentenceTransformer
from gemini_module import GeminiChat

class OllamaChatGUI:
    def on_temp_change(self, value):
        """Update temperature label when slider moves"""
        self.temp_label.config(text=f"{float(value):.2f}")  # Update temperature label with slider value

    def __init__(self, root):
        self.root = root
        self.root.title("Local(o)llama Chat")
        self.file_img = None
        self.file_content = None
        self.file_type = None
        self.word_count = 0
        self.selected_model = None
        self.selected_embedding_model = None # new attribute
        self.developer = StringVar(value="ollama")  # Default to ollama
        self.gemini_chat = GeminiChat()  # Initialize Gemini chat
        self.stop_event = threading.Event()
        
        # Main chat frame
        self.chat_frame = ttk.Frame(root)
        self.chat_frame.pack(padx=10, pady=10, expand=True, fill='both')
        
        # Chat display
        self.chat_display = tk.Text(self.chat_frame, wrap=tk.WORD, width=50, height=20, font=("Arial", 12), padx=5, pady=5)
        self.chat_display.pack(side='left', expand=True, fill='both')
        scrollbar = ttk.Scrollbar(self.chat_frame, orient='vertical', command=self.chat_display.yview)
        scrollbar.pack(side='right', fill='y')
        self.chat_display['yscrollcommand'] = scrollbar.set
        
        # Make read-only but allow selection
        self.chat_display.bind("<Key>", lambda e: "break" if e.keysym not in ("c", "C", "Control_L", "Control_R") else "")
        self.chat_display.bind("<Control-c>", lambda e: self.chat_display.event_generate("<<Copy>>"))
        
        # Model and Embedding Frame
        model_frame = ttk.Frame(root)
        model_frame.pack(side='top', padx=10, pady=5)
        
        # Developer selector
        ttk.Label(model_frame, text="Developer:").pack(side='left', padx=(0,5))
        developer_selector = ttk.Combobox(model_frame, textvariable=self.developer, values=['ollama', 'google'], state='readonly')
        developer_selector.pack(side='left', padx=(0,10))
        developer_selector.bind('<<ComboboxSelected>>', self.on_developer_changed)
        
        # LLM Model selector
        ttk.Label(model_frame, text="LLM Model:").pack(side='left', padx=(0,5))
        self.model_selector = ttk.Combobox(model_frame, state='readonly')
        self.model_selector.pack(side='left', padx=(5,0))
        self.model_selector.bind('<<ComboboxSelected>>', self.on_model_selected)
        
        # Embedding Model selector
        ttk.Label(model_frame, text="Embed Model:").pack(side='left', padx=(10,5))
        self.embedding_selector = ttk.Combobox(model_frame, state='readonly')
        self.embedding_selector.pack(side='left', padx=(5,0))
        self.embedding_selector.bind('<<ComboboxSelected>>', self.on_embedding_model_selected)
        
        self.update_model_list()
        
        
        # System instructions frame
        system_frame = ttk.LabelFrame(root, text="System Instructions")
        system_frame.pack(padx=10, pady=5, fill='x')

        # System instructions text box with scrollbar
        self.system_text = scrolledtext.ScrolledText(system_frame, height=3, wrap=tk.WORD)
        self.system_text.pack(padx=5, pady=5, fill='x')
        self.system_text.insert('1.0', "You are a helpful AI assistant who only gives accurate and objective information.")
        
        # Temperature controls
        temp_frame = ttk.Frame(model_frame)
        temp_frame.pack(side='left', padx=(10,0))
        
        ttk.Label(temp_frame, text="Creativity:").pack(side='left')
        self.temperature = tk.DoubleVar(value=0.4)
        self.temp_label = ttk.Label(temp_frame, text="0.70")
        self.temp_label.pack(side='right', padx=(5,0))
        
        self.temp_slider = ttk.Scale(
            temp_frame,
            from_=0.0,
            to=2.0,
            orient='horizontal',
            length=100,
            variable=self.temperature,
            command=self.on_temp_change
        )
        self.temp_slider.pack(side='left')
        
        # Context window controls
        context_frame = ttk.Frame(model_frame)
        context_frame.pack(side='left', padx=(10,0))
        ttk.Label(context_frame, text="Context:").pack(side='left')
        self.context_size = tk.IntVar(value=4096)
        self.context_label = ttk.Label(context_frame, text="4096")
        self.context_label.pack(side='right', padx=(5,0))
        
        self.context_slider = ttk.Scale(
            context_frame,
            from_=1000,
            to=128000,
            orient='horizontal',
            length=100,
            variable=self.context_size,
            command=self.on_context_change
        )
        self.context_slider.pack(side='left')

        # Chunk Size control
        chunk_frame = ttk.Frame(model_frame)
        chunk_frame.pack(side='left', padx=(10, 0))
        ttk.Label(chunk_frame, text="RAG Chunk Size:").pack(side='left')
        self.chunk_size = tk.IntVar(value=128)
        self.chunk_entry = ttk.Entry(chunk_frame, textvariable=self.chunk_size, width=5)
        self.chunk_entry.pack(side='left', padx=(5, 0))

        # Semantic Chunking control
        self.semantic_chunking_var = tk.BooleanVar(value=False)
        semantic_chunking_checkbox = ttk.Checkbutton(
            model_frame,
            text="Semantic Chunking for RAG? (Slow)",
            variable=self.semantic_chunking_var
        )
        semantic_chunking_checkbox.pack(side='left', padx=(10, 0))
        
        # Chat history checkbox
        self.include_chat_var = tk.BooleanVar()
        self.include_chat_checkbox = ttk.Checkbutton(
            model_frame, 
            text="Include chat?",
            variable=self.include_chat_var
        )
        self.include_chat_checkbox.pack(side='left', padx=(10,0))
        
        # Show image checkbox
        self.show_image_var = tk.BooleanVar(value=True)
        show_image_checkbox = ttk.Checkbutton(model_frame, text="Show Image?", variable=self.show_image_var)
        show_image_checkbox.pack(side='left', padx=(10,0))
        self.show_image_var.trace_add("write", self.on_show_image_toggle)
        
        # File content checkbox
        self.include_file_var = tk.BooleanVar(value=True)
        self.include_file_checkbox = ttk.Checkbutton(
            model_frame,
            text="Include file content?",
            variable=self.include_file_var
        )
        self.include_file_checkbox.pack(side='left', padx=(10,0))

        # Create input area
        input_frame = ttk.Frame(root, style='InputFrame.TFrame')
        input_frame.pack(padx=10, pady=(0, 10), fill='x')
        self.input_field = scrolledtext.ScrolledText(input_frame, wrap=tk.WORD, height=3, borderwidth=1, relief="solid", font=("Arial", 12))
        self.input_field.pack(side='left', expand=True, fill='both', padx=5, pady=5)
        self.input_field.config(borderwidth=1, relief="solid", highlightthickness=1, highlightbackground="#cccccc")
        
        # Button frame
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(side='right', padx=(5, 0))
        clear_button = ttk.Button(button_frame, text="Clear Chat", command=self.clear_chat)
        clear_button.pack(side='right', padx=(5, 0))
        batch_button = ttk.Button(button_frame, text="Batch Process", command=self.start_batch_process)
        batch_button.pack(side='right', padx=(5, 0))
        send_button = ttk.Button(button_frame, text="Send", command=self.send_message)
        send_button.pack(side='right')
        
        stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_processing)
        stop_button.pack(side='right', padx=(5, 0))
        
        # Add "Clear File" button
        clear_file_button = ttk.Button(button_frame, text="Clear File", command=self.clear_file)
        clear_file_button.pack(side='right', padx=(5, 0))
        
        # Add "RAG" button
        self.rag_button = ttk.Button(button_frame, text="RAG", command=self.select_rag_files)  # RAG button
        self.rag_button.pack(side='right', padx=(5, 0))
        self.rag_files = [] # list of selected files for RAG
        
        # Input processing
        self.is_processing = False
        self.active_stream = None
        self.input_field.bind('<Control-Return>', lambda e: self.send_message())
        self.chat_display.drop_target_register(DND_FILES)
        self.chat_display.dnd_bind('<<Drop>>', self.handle_drop)
        
        # Configure tags and update status
        self.configure_tags()
        self.update_status()

        # Image preview
        self.image_preview = tk.Label(root)
        self.image_preview.pack()
    
    def on_developer_changed(self, event):
        """Handle developer selection change"""
        developer = self.developer.get()
        self.update_model_list()
        self.chat_display.insert(tk.END, f"\nSwitched to {developer} models\n")
        self.chat_display.see(tk.END)
    
    # Context tab
    def on_context_change(self, value):
        """Update context window label when slider moves"""
        self.context_label.config(text=f"{int(float(value))}")  # Update context label with slider value
    
    def handle_drop(self, event):
        file_path = event.data.strip('{}')
        self.file_type = self.get_file_type(file_path)
        
        # Enable the include file checkbox when a file is dropped
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
                self.image_preview.config(image="")
        else:
            self.file_img = None
            self.file_content = self.extract_content(file_path)
            if self.file_content:
                self.word_count = len(re.findall(r'\w+', self.file_content))
        
        self.update_status()
    
    def get_file_type(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif']:
            return 'image'
        return 'document'
    
    def extract_content(self, file_path):
        try:
            if self.get_file_type(file_path) == 'document':
                md = MarkItDown()
                result = md.convert(file_path)
                return result.text_content
            return None
        except Exception as e:
            print(f"Error extracting content: {str(e)}")
            return None
    
    def display_message(self, message, tags=None):
        """Display a message in the chat window with optional tags"""
        current_state = self.chat_display["state"]
        self.chat_display["state"] = "normal"
        
        if tags == 'assistant':
            # Process potential code blocks in assistant responses
            parts = message.split('```')
            for i, part in enumerate(parts):
                if i % 2 == 0:  # Regular text
                    # Always insert regular text, even if empty
                    self.chat_display.insert(tk.END, part, 'assistant')
                else:  # Code block
                    self.chat_display.insert(tk.END, '\n', 'assistant')  # Newline before code
                    self.chat_display.insert(tk.END, part.strip(), 'code')  # Code with code tag
                    self.chat_display.insert(tk.END, '\n', 'assistant')  # Newline after code
        else:
            self.chat_display.insert(tk.END, message, tags)
        
        self.chat_display["state"] = current_state
        self.chat_display.see(tk.END)
    
    def update_status(self):
        """Update status display with current file information."""
        if self.file_img:
            status = f"Image loaded: {self.file_img}"
        elif self.file_content:
            status = f"Document loaded: {self.file_type.upper()} - {self.word_count} words"
        else:
            status = ""
            
        # Only display status if there's actually a file loaded
        if status:
            self.display_message(f"\n{status}\n", 'status')
    
    def send_message(self):
        user_input = self.input_field.get("1.0", tk.END)
        if not user_input.strip():
            return
                
        # Display user message
        self.display_message("\nYou: ", 'user')
        self.display_message(f"{user_input}\n", 'user')
        
        self.input_field.delete("1.0", tk.END)
        
        # Prepare message content
        content = user_input

        # Include file content based on the checkbox
        if self.include_file_var.get() and self.file_content:
            content += f"\n\nDocument content:\n{self.file_content}"
            content += f"\n\nFile path: {self.file_img}"

        # Include chat history if selected
        if self.include_chat_var.get():
            chat_history = self.chat_display.get(1.0, tk.END).strip()
            # Exclude file content from chat history if not including it
            if not self.include_file_var.get() and self.file_content:
                chat_history = chat_history.replace(self.file_content, '')
            content += f"\n\nChat history:\n{chat_history}"
            
        # Include RAG context
        if self.rag_files:
             rag_context = rag.retrieve_context(query=user_input)
             content += f"\n\nRAG Context:\n{rag_context}"
             
        # Prepare message
        message = {
            'role': 'user',
            'content': content
        }
        
        # Add image if available and included
        if self.include_file_var.get() and self.file_img:
            with open(self.file_img, 'rb') as img_file:
                message['images'] = [img_file.read()]
                
        # Send message in separate thread
        threading.Thread(target=self.get_response, args=(message,)).start()
            
    def get_response(self, message):
        self.stop_event.clear()
        try:
            self.display_message("\nAssistant: ", 'assistant')

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

            # Create a mark for the response start
            self.chat_display.mark_set("response_start", "end-1c")
            full_response = ""

            if self.developer.get() == 'ollama':
                stream = ollama.chat(
                    model=self.selected_model,
                    messages=messages,
                    stream=True,
                    options={
                        "temperature": self.temperature.get(),
                        "num_ctx": self.context_size.get()
                    }
                )
                self.active_stream = stream

                try:
                    for chunk in stream:
                        if self.stop_event.is_set():
                            break
                        if chunk and 'message' in chunk and 'content' in chunk['message']:
                            content = chunk['message']['content']
                            full_response += content
                            self.chat_display.delete("response_start", "end-1c")
                            self.display_message(content, 'assistant')
                finally:
                    self.active_stream = None
            else:  # google
                stream = self.gemini_chat.get_response(
                    messages=messages,
                    temperature=self.temperature.get(),
                    max_tokens=self.context_size.get()
                )
                self.active_stream = stream

                try:
                    for chunk in stream:
                        if self.stop_event.is_set():
                            break
                        if chunk and 'message' in chunk and 'content' in chunk['message']:
                            content = chunk['message']['content']
                            full_response += content
                            self.chat_display.delete("response_start", "end-1c")
                            self.display_message(content, 'assistant')
                finally:
                    self.active_stream = None

        except Exception as e:
            self.display_message(f"\nError: {str(e)}\n", 'error')
            self.chat_display.see(tk.END)
    
    def start_batch_process(self):
        if not self.input_field.get("1.0", tk.END).strip():
            self.chat_display.insert(tk.END, "\nPlease enter a prompt first.\n")
            return

        if not self.selected_model:
            self.chat_display.insert(tk.END, "\nNo model selected!\n")
            return

        files = filedialog.askopenfilenames(title="Select Files for Batch Processing")
        if files:
            threading.Thread(target=self.process_files, args=(files,)).start()

    def process_files(self, files):
        prompt = self.input_field.get("1.0", tk.END).strip()
        self.chat_display.insert(tk.END, f"\nStarting batch processing of {len(files)} files\nFile paths: {files}\n")

        for idx, file_path in enumerate(files, 1):
            if self.stop_event.is_set():
                break

            self.chat_display.insert(tk.END, f"\nProcessing file {idx}/{len(files)}: {os.path.basename(file_path)}\n")
            self.chat_display.see(tk.END)

            file_type = self.get_file_type(file_path)
            message = {'role': 'user', 'content': prompt}

            if file_type == 'image':
                with open(file_path, 'rb') as img_file:
                    message['images'] = [img_file.read()]
            else:
                content = prompt
                file_content = self.extract_content(file_path)
                if file_content:
                    word_count = len(re.findall(r'\w+', file_content))
                    self.chat_display.insert(tk.END, f"\nProcessing file {idx}/{len(files)}: {os.path.basename(file_path)} - {word_count} words\n")
                    content += f"\n\nDocument content:\n{file_content}"
                    content += f"\n\nFile path: {file_path}"
                message['content'] = content

            try:
                self.display_message(f"Assistant (for {os.path.basename(file_path)}): ", 'assistant')

                system_msg = self.system_text.get('1.0', tk.END).strip()
                messages = []
                if system_msg:
                    messages.append({
                        'role': 'system',
                        'content': system_msg
                    })
                messages.append(message)

                if self.developer.get() == 'ollama':
                    stream = ollama.chat(
                        model=self.selected_model,
                        messages=messages,
                        stream=True,
                        options={
                            "temperature": self.temperature.get(),
                            "num_ctx": self.context_size.get()
                        }
                    )
                else:  # google
                    stream = self.gemini_chat.get_response(
                        messages=messages,
                        temperature=self.temperature.get(),
                        max_tokens=self.context_size.get()
                    )

                self.active_stream = stream

                try:
                    for chunk in stream:
                        if self.stop_event.is_set():
                            break
                        if chunk and 'message' in chunk and 'content' in chunk['message']:
                            self.display_message(chunk['message']['content'], 'assistant')
                finally:
                    self.active_stream = None
            except Exception as e:
                self.display_message(f"Error processing file: {str(e)}\n", 'error')

            self.chat_display.see(tk.END)

        self.display_message("\nBatch processing completed.\n", 'status')
        self.chat_display.see(tk.END)
        
    def update_model_list(self):
        """Update model list based on selected developer"""
        if self.developer.get() == 'ollama':
            try:
                models = ollama.list()
                all_model_names = [model.model for model in models.models]
                
                # Filter model names into LLMs and embedding models
                llm_models = [name for name in all_model_names if 'embed' not in name]
                embedding_models = [name for name in all_model_names if 'embed' in name]
                
                # Update the LLM combobox
                self.model_selector['values'] = llm_models
                if llm_models:
                    self.model_selector.set(llm_models[0])
                    self.selected_model = llm_models[0]
                
                # Update the embedding combobox
                self.embedding_selector['state'] = 'readonly'
                self.embedding_selector['values'] = embedding_models
                if embedding_models:
                    self.embedding_selector.set(embedding_models[0])
                    self.selected_embedding_model = embedding_models[0]
                
                if not all_model_names:
                   self.chat_display.insert(tk.END, "\nNo models found.\nPlease ensure ollama is running\n")
                   self.chat_display.see(tk.END)
                   
            except Exception as e:
                self.chat_display.insert(tk.END, f"\nError fetching ollama models: {str(e)}\n")
                self.chat_display.see(tk.END)
        else:  # google
            try:
                # Get Gemini models
                gemini_models = self.gemini_chat.list_models()
                
                # Update the LLM combobox
                self.model_selector['values'] = gemini_models
                if gemini_models:
                    self.model_selector.set(gemini_models[0])
                    self.selected_model = gemini_models[0]
                
                # Enable embedding selector for Gemini and set its value
                self.embedding_selector['state'] = 'readonly'
                self.embedding_selector['values'] = ['models/text-embedding-004']
                self.embedding_selector.set('models/text-embedding-004')
                self.selected_embedding_model = 'models/text-embedding-004'
                
            except Exception as e:
                self.chat_display.insert(tk.END, f"\nError fetching Gemini models: {str(e)}\n")
                self.chat_display.see(tk.END)
    
    def on_model_selected(self, event):
        self.selected_model = self.model_selector.get()
        self.chat_display.insert(tk.END, f"\nSwitched to model: {self.selected_model}\n")
        self.chat_display.see(tk.END)
    
    def on_embedding_model_selected(self, event):
        if self.developer.get() == 'ollama':
            self.selected_embedding_model = self.embedding_selector.get()
            self.chat_display.insert(tk.END, f"\nSwitched to embedding model: {self.selected_embedding_model}\n")
            self.chat_display.see(tk.END)
        else: # google
            self.selected_embedding_model = 'models/text-embedding-004'
            self.chat_display.insert(tk.END, f"\nUsing Gemini embedding model: {self.selected_embedding_model}\n")
            self.chat_display.see(tk.END)
        
        # Update the embedding function in the RAG class and clear db
        rag.update_embedding_function(self.selected_embedding_model)
        self.rag_files = []
        self.rag_button.config(text="RAG")
    
    def clear_chat(self):
        self.chat_display.delete(1.0, tk.END)
        self.update_status()
    
    def stop_processing(self):
        """Stop any ongoing process."""
        self.stop_event.set()
        self.display_message("\nStopped ongoing processes.\n", 'status')
    
    def clear_file(self):
        """Clear the uploaded file or image from memory."""
        # Clear all file-related variables
        self.file_content = None
        self.file_img = None
        self.file_type = None
        self.word_count = 0
        
        # Clear image preview
        self.image_preview.config(image="")
        self.preview_image = None  # Clear the reference to prevent memory leaks
        
        # Disable the include file checkbox since there's no file
        self.include_file_checkbox.state(['!selected', 'disabled'])
        self.include_file_var.set(False)
        
        # Clear any previous status messages about files
        current_text = self.chat_display.get("1.0", tk.END)
        lines = current_text.split('\n')
        # Remove status lines about files
        filtered_lines = [line for line in lines 
                         if not (line.startswith("Image loaded:") or 
                                line.startswith("Document loaded:"))]
        
        # Update chat display without file status
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.insert("1.0", "\n".join(filtered_lines))

    def configure_tags(self):
        self.chat_display.tag_configure('user', foreground='#0077cc')
        self.chat_display.tag_configure('assistant', foreground='#800080')
        self.chat_display.tag_configure('error', foreground='red')
        self.chat_display.tag_configure('status', foreground='gray')
        self.chat_display.tag_configure('code', font=("Consolas", 12), background="#f0f0f0")
        
    def on_show_image_toggle(self, *args):
        """Show or hide the image preview depending on the checkbox."""
        if self.show_image_var.get() and self.file_type == 'image' and self.file_img:
            pil_img = Image.open(self.file_img)
            pil_img.thumbnail((300, 300))
            self.preview_image = ImageTk.PhotoImage(pil_img)
            self.image_preview.config(image=self.preview_image)
        else:
            self.image_preview.config(image="")
    
    def select_rag_files(self):
      """Handles the selection of files for RAG."""
      selected_files = filedialog.askopenfiles(title="Select files for RAG", mode="r")
      if selected_files:
          # Clear any previous RAG cache
          rag.clear_db()
          self.rag_files = [file.name for file in selected_files]
          rag.ingest_data(self.rag_files) # ingest the new files for RAG
          self.rag_button.config(text=f"RAG ({len(self.rag_files)})")
      else:
         # Clear RAG if cancelled
         rag.clear_db()
         self.rag_files = [] # remove the stored files
         self.rag_button.config(text="RAG")

def main():
    root = TkinterDnD.Tk()
    app = OllamaChatGUI(root)
    # Get the initial embedding model from the combobox
    app.update_model_list()
    initial_embedding_model = app.embedding_selector.get()
    
    # Get the initial chunk size
    initial_chunk_size = app.chunk_size.get()
    
    # Get initial semantic chunking state
    initial_semantic_chunking = app.semantic_chunking_var.get()
    
    from rag_module import RAG
    global rag
    rag = RAG(embedding_model_name = initial_embedding_model, chunk_size = initial_chunk_size, use_semantic_chunking = initial_semantic_chunking)
    
    # Track changes in chunk size
    def update_rag_chunk_size(*args):
      global rag
      rag.chunk_size = app.chunk_size.get() # update the chunk size
      
    app.chunk_size.trace_add("write", update_rag_chunk_size)
    
    # Track changes in semantic chunking
    def update_rag_semantic_chunking(*args):
       global rag
       rag.use_semantic_chunking = app.semantic_chunking_var.get() # update semantic chunking state
       
       # Re-initialize the sentence transformer if semantic chunking is enabled
       if rag.use_semantic_chunking:
            try:
                rag.sentence_transformer = SentenceTransformer('all-mpnet-base-v2')
            except Exception as e:
                print(f"Error loading sentence transformer model: {e}")
                rag.sentence_transformer = None
       else:
          rag.sentence_transformer = None # set to none if semantic chunking is disabled
    
    app.semantic_chunking_var.trace_add("write", update_rag_semantic_chunking)
    
    root.mainloop()

if __name__ == "__main__":
    main()
