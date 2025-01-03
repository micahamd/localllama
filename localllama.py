import tkinter as tk
from tkinter import scrolledtext, filedialog
import threading
from tkinter import ttk, font
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import re
import markdown
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import BBCodeFormatter
import matplotlib.pyplot as plt
import io
from PIL import Image, ImageTk
import ollama
from rag_module import RAG  # Import the RAG class
from markitdown import MarkItDown  # Import MarkItDown

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
        self.stop_event = threading.Event()
        self.rag_files = []  # List to store selected RAG file paths
        self.rag_button_text = "RAG"  # Initial text for the RAG button
        
        # Create RAG instance
        self.rag = RAG()

        # Create main chat frame first
        self.chat_frame = ttk.Frame(root)
        self.chat_frame.pack(padx=10, pady=10, expand=True, fill='both')
        
        # Create chat display with scrollbar
        self.chat_display = tk.Text(self.chat_frame, wrap=tk.WORD, width=50, height=20, font=("Arial", 12), padx=5, pady=5)
        self.chat_display.pack(side='left', expand=True, fill='both')
        scrollbar = ttk.Scrollbar(self.chat_frame, orient='vertical', command=self.chat_display.yview)
        scrollbar.pack(side='right', fill='y')
        self.chat_display['yscrollcommand'] = scrollbar.set
        
        # Make read-only but allow selection
        self.chat_display.bind("<Key>", lambda e: "break" if e.keysym not in ("c", "C", "Control_L", "Control_R") else "")
        self.chat_display.bind("<Control-c>", lambda e: self.chat_display.event_generate("<<Copy>>"))
        
        # Create model frame and controls
        model_frame = ttk.Frame(root)
        model_frame.pack(side='top', padx=10, pady=5)
        
        # Model selector
        self.model_selector = ttk.Combobox(model_frame, state='readonly')
        self.model_selector.pack(side='left', padx=(5,0))
        self.update_model_list()
        self.model_selector.bind('<<ComboboxSelected>>', self.on_model_selected)

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
            to=1.0,
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
            to=30000,
            orient='horizontal',
            length=100,
            variable=self.context_size,
            command=self.on_context_change
        )
        self.context_slider.pack(side='left')
        
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

        # Add RAG button
        self.rag_button = ttk.Button(button_frame, text=self.rag_button_text, command=self.toggle_rag)
        self.rag_button.pack(side='right', padx=(5, 0))
        
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
    
    # Context tab
    def on_context_change(self, value):
        """Update context window label when slider moves"""
        self.context_label.config(text=f"{int(float(value))}")
    
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

        # Include chat history if selected
        if self.include_chat_var.get():
            chat_history = self.chat_display.get(1.0, tk.END).strip()
            # Exclude file content from chat history if not including it
            if not self.include_file_var.get() and self.file_content:
                chat_history = chat_history.replace(self.file_content, '')
            content += f"\n\nChat history:\n{chat_history}"

        # Prepare message
        message = {
            'role': 'user',
            'content': content
        }
        
        # Add image if available and included
        if self.include_file_var.get() and self.file_img:
            with open(self.file_img, 'rb') as img_file:
                message['images'] = [img_file.read()]
                
        # Retrieve context for RAG if RAG files are available
        if self.rag_files:
              rag_context = self.rag.retrieve_context(user_input)
              message['content'] += f"\n\nContext:\n{rag_context}"

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
        except Exception as e:
            self.display_message(f"\nError: {str(e)}\n", 'error')
            self.chat_display.see(tk.END)
    
    def start_batch_process(self):
        if not self.input_field.get().strip():
            self.chat_display.insert(tk.END, "\nPlease enter a prompt first.\n")
            return
                
        directory = filedialog.askdirectory(title="Select Directory for Batch Processing")
        if directory:
            threading.Thread(target=self.process_directory, args=(directory,)).start()
    
    def process_directory(self, directory):
        prompt = self.input_field.get()
        self.chat_display.insert(tk.END, f"\nStarting batch processing of directory: {directory}\n")
        
        # Collect all files
        files_to_process = []
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if self.get_file_type(file_path):
                    files_to_process.append(file_path)
        
        total_files = len(files_to_process)
        self.chat_display.insert(tk.END, f"Found {total_files} files to process.\n")
        self.chat_display.see(tk.END)
        
        self.stop_event.clear()

        for idx, file_path in enumerate(files_to_process, 1):
            if self.stop_event.is_set():
                break
                
            self.chat_display.insert(tk.END, f"\nProcessing file {idx}/{total_files}: {os.path.basename(file_path)}\n")
            self.chat_display.see(tk.END)
                
            file_type = self.get_file_type(file_path)
            message = {'role': 'user', 'content': prompt}
                
            if file_type == 'image':
                with open(file_path, 'rb') as img_file:
                    message['images'] = [img_file.read()]
            else:
                content = prompt
                if self.extract_content(file_path):
                    content += f"\n\nDocument content:\n{self.extract_content(file_path)}"
                if self.include_chat_var.get():
                    chat_history = self.chat_display.get(1.0, tk.END).strip()
                    content += f"\n\nChat history:\n{chat_history}"
                message['content'] = content
                
        try:
            self.display_message(f"Assistant (for {os.path.basename(file_path)}): ", 'assistant')

            # Add system instructions
            system_msg = self.system_text.get('1.0', tk.END).strip()
            messages = []
            if system_msg:
                messages.append({
                    'role': 'system',
                    'content': system_msg
                })
            messages.append(message)
                
            stream = ollama.chat(
                model=self.selected_model,
                messages=messages,
                options={"temperature": self.temperature.get(),
                         "num_ctx": self.context_size.get()
                }, 
                stream=True
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
        try:
            models = ollama.list()
            model_names = [model.model for model in models.models]
            self.model_selector['values'] = model_names
            if model_names:
                self.model_selector.set(model_names[0])
                self.selected_model = model_names[0]
        except Exception as e:
            self.chat_display.insert(tk.END, f"\nError fetching models: {str(e)}\n")
            self.chat_display.see(tk.END)
    
    def on_model_selected(self, event):
        self.selected_model = self.model_selector.get()
        self.chat_display.insert(tk.END, f"\nSwitched to model: {self.selected_model}\n")
        self.chat_display.see(tk.END)
    
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

    def toggle_rag(self):
        """Toggles RAG functionality by selecting files or clearing the cache"""
        if self.rag_files:
           # Clear the RAG cache
            self.rag.clear_db()
            self.rag_files = []
            self.rag_button_text = "RAG"
            self.rag_button.config(text=self.rag_button_text)
            self.display_message("\nRAG cache cleared.\n", 'status')
            self.chat_display.see(tk.END)
        else:
            # Open file dialog to select files for RAG
            file_paths = filedialog.askopenfilenames(title="Select files for RAG")
            if file_paths:
                self.rag_files = list(file_paths)  # Store selected file paths as a list
                self.rag.ingest_data(self.rag_files) # ingest data
                self.rag_button_text = f"RAG ({len(self.rag_files)})"
                self.rag_button.config(text=self.rag_button_text)
                self.display_message(f"\nRAG enabled with {len(self.rag_files)} file(s).\n", 'status')
                self.chat_display.see(tk.END)

def main():
    root = TkinterDnD.Tk()
    app = OllamaChatGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()