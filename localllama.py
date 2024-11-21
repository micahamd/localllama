try:
    import ollama
except ImportError as e:
    print(f"Error importing ollama: {str(e)}")
    # Handle the error or exit the application
    exit(1)

import tkinter as tk
from tkinter import scrolledtext, filedialog
import threading
from tkinter import ttk, font
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
from docx import Document
import PyPDF2
import re
import markdown
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import BBCodeFormatter
import matplotlib.pyplot as plt
import io
from PIL import Image, ImageTk

class OllamaChatGUI:
    def on_temp_change(self, value):
        """Update temperature label when slider moves"""
        self.temp_label.config(text=f"{float(value):.2f}")   

    def __init__(self, root):
        self.root = root
        self.root.title("Ollama Chat")
        self.file_img = None
        self.file_content = None
        self.file_type = None
        self.word_count = 0
        self.selected_model = None
        
        # Create main chat frame first
        self.chat_frame = ttk.Frame(root)
        self.chat_frame.pack(padx=10, pady=10, expand=True, fill='both')
        
        # Create chat display with scrollbar
        self.chat_display = tk.Text(self.chat_frame, wrap=tk.WORD, width=50, height=20)
        self.chat_display.pack(side='left', expand=True, fill='both')
        scrollbar = ttk.Scrollbar(self.chat_frame, orient='vertical', command=self.chat_display.yview)
        scrollbar.pack(side='right', fill='y')
        self.chat_display['yscrollcommand'] = scrollbar.set
        
        # Make read-only but allow selection
        self.chat_display.bind("<Key>", lambda e: "break" if e.keysym not in ("c", "C", "Control_L", "Control_R") else "")
        
        # Create model frame and controls
        model_frame = ttk.Frame(root)
        model_frame.pack(side='top', padx=10, pady=5)
        
        # Model selector
        self.model_selector = ttk.Combobox(model_frame, state='readonly')        
        self.model_selector.pack(side='left', padx=(5,0))
        self.update_model_list()
        self.model_selector.bind('<<ComboboxSelected>>', self.on_model_selected)
        
        # Temperature controls
        temp_frame = ttk.Frame(model_frame)
        temp_frame.pack(side='left', padx=(10,0))
        
        ttk.Label(temp_frame, text="Temp:").pack(side='left')
        self.temperature = tk.DoubleVar(value=0.7)
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
        self.context_size = tk.IntVar(value=4096)  # Default size
        self.context_label = ttk.Label(context_frame, text="4096")
        self.context_label.pack(side='right', padx=(5,0))
        
        self.context_slider = ttk.Scale(
            context_frame,
            from_=100,
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

        # 4. Create input area
        input_frame = ttk.Frame(root)
        input_frame.pack(padx=10, pady=(0, 10), fill='x')
        
        self.input_field = ttk.Entry(input_frame)
        self.input_field.pack(side='left', expand=True, fill='x', padx=(0, 5))
        
        # Button frame
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(side='right', padx=(5, 0))
        
        clear_button = ttk.Button(button_frame, text="Clear Chat", command=self.clear_chat)
        clear_button.pack(side='right', padx=(5, 0))
        
        batch_button = ttk.Button(button_frame, text="Batch Process", command=self.start_batch_process)
        batch_button.pack(side='right', padx=(5, 0))
        
        send_button = ttk.Button(button_frame, text="Send", command=self.send_message)
        send_button.pack(side='right')
        
        # 5. Final setup
        self.is_processing = False
        self.input_field.bind('<Return>', lambda e: self.send_message())
        self.chat_display.drop_target_register(DND_FILES)
        self.chat_display.dnd_bind('<<Drop>>', self.handle_drop)
        
        # Configure tags and update status
        self.configure_tags()
        self.update_status()

    # Context tab
    def on_context_change(self, value):
        """Update context window label when slider moves"""
        self.context_label.config(text=f"{int(float(value))}")

    def handle_drop(self, event):
        file_path = event.data.strip('{}')
        self.file_type = self.get_file_type(file_path)
        
        if self.file_type == 'image':
            self.file_img = file_path
            self.file_content = None
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
        elif ext == '.docx':
            return 'docx'
        elif ext == '.pdf':
            return 'pdf'
        elif ext == '.txt':
            return 'txt'
        return None

    def extract_content(self, file_path):
        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext == '.docx':
                doc = Document(file_path)
                return ' '.join([paragraph.text for paragraph in doc.paragraphs])
            elif ext == '.pdf':
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    return ' '.join([page.extract_text() for page in pdf_reader.pages])
            elif ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()
            return None
        except Exception as e:
            print(f"Error extracting content: {str(e)}")
            return None

    def display_message(self, message, tags=None):
        """Display a message in the chat window with optional tags"""
        # Temporarily enable editing
        current_state = self.chat_display["state"]
        self.chat_display["state"] = "normal"
        
        # Insert the message
        self.chat_display.insert(tk.END, message, tags)
        
        # Restore state
        self.chat_display["state"] = current_state
        self.chat_display.see(tk.END)

    def update_status(self):
        if self.file_img:
            status = f"Image loaded: {self.file_img}"
        elif self.file_content:
            status = f"Document loaded: {self.file_type.upper()} - {self.word_count} words"
        else:
            status = "No file loaded"
        self.display_message(f"\n{status}\n", 'status')

    def send_message(self):
        user_input = self.input_field.get()
        if not user_input.strip():
            return
            
        # Display user message
        self.display_message("\nYou: ", 'user')
        self.display_message(f"{user_input}\n", 'user')
        
        self.input_field.delete(0, tk.END)
        
        # Prepare message content
        content = user_input
        if self.file_content:
            content += f"\n\nDocument content:\n{self.file_content}"
        if self.include_chat_var.get():
            chat_history = self.chat_display.get(1.0, tk.END).strip()
            content += f"\n\nChat history:\n{chat_history}"
        
        # Prepare message
        message = {
            'role': 'user',
            'content': content
        }
        
        # Add image if available
        if self.file_img:
            with open(self.file_img, 'rb') as img_file:
                message['images'] = [img_file.read()]
                
        # Send message in separate thread
        threading.Thread(target=self.get_response, args=(message,)).start()
        self.file_content = None
        self.file_img = None
        self.is_processing = False  # Stop any ongoing batch processing
        
    def get_response(self, message):
        try:
            self.display_message("\nAssistant: ", 'assistant')
            
            # Create a mark for the response start
            self.chat_display.mark_set("response_start", "end-1c")
            full_response = ""
            
            for chunk in ollama.chat(
                model=self.selected_model,
                messages=[message],
                stream=True,
                options={"temperature": self.temperature.get(),
                         "num_ctx": self.context_size.get()
                } 
            ):
                if chunk and 'message' in chunk and 'content' in chunk['message']:
                    content = chunk['message']['content']
                    full_response += content
                    self.chat_display.delete("response_start", "end-1c")
                    self.display_message(content, 'assistant')
                    
            self.display_message("\n", 'assistant')
            self.file_img = None
            self.update_status()
            
        except Exception as e:
            self.display_message(f"\nError: {str(e)}\n", 'error')
            
        self.chat_display.see(tk.END)

    def start_batch_process(self):
        if not self.input_field.get().strip():
            self.chat_display.insert(tk.END, "\nPlease enter a prompt first.\n")
            return
            
        directory = filedialog.askdirectory(title="Select Directory for Batch Processing")
        if directory:
            self.is_processing = True
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
        
        for idx, file_path in enumerate(files_to_process, 1):
            if not self.is_processing:
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
                self.chat_display.insert(tk.END, f"Assistant (for {os.path.basename(file_path)}): ")
                for chunk in ollama.chat(
                    model=self.selected_model,
                    messages=[message],
                    options={"temperature": self.temperature.get()}, 
                    stream=True
                ):
                    if not self.is_processing:
                        break
                    if chunk and 'message' in chunk and 'content' in chunk['message']:
                        self.chat_display.insert(tk.END, chunk['message']['content'])
                        self.chat_display.see(tk.END)
                self.chat_display.insert(tk.END, "\n")
            except Exception as e:
                self.chat_display.insert(tk.END, f"Error processing file: {str(e)}\n")
            
            self.chat_display.see(tk.END)
        
        self.is_processing = False
        self.chat_display.insert(tk.END, "\nBatch processing completed.\n")
        self.chat_display.see(tk.END)

    def update_model_list(self):
        try:
            models = ollama.list()
            model_names = [model['name'] for model in models['models']]
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

    def configure_tags(self):
        self.chat_display.tag_configure('user', foreground='#0077cc', font=('Arial', 10, 'bold'))
        self.chat_display.tag_configure('assistant', foreground='#800080', font=('Arial', 10))
        self.chat_display.tag_configure('code', font=('Courier', 10))
        self.chat_display.tag_configure('error', foreground='red')
        self.chat_display.tag_configure('status', foreground='gray')

    def format_markdown(self, text):
        # Convert markdown to plain text while preserving formatting
        try:
            # Remove HTML tags but keep content
            def clean_html(html_text):
                # Basic HTML tag removal while preserving content
                text = re.sub(r'<[^>]+>', '', html_text)
                # Convert HTML entities
                text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
                text = text.replace('&quot;', '"').replace('&apos;', "'")
                return text
    
            # Convert markdown to HTML first
            html = markdown.markdown(text, extensions=['fenced_code', 'tables'])
            
            # Process code blocks specially
            code_pattern = r'<pre><code.*?>(.*?)</code></pre>'
            result = ''
            last_end = 0
            
            for match in re.finditer(code_pattern, html, re.DOTALL):
                # Add cleaned text before code block
                result += clean_html(html[last_end:match.start()]) 
                
                # Format code block
                code = match.group(1)
                code = clean_html(code)
                # Add code block with proper formatting
                result += f"\n```\n{code}\n```\n"
                
                last_end = match.end()
            
            # Add remaining cleaned text
            result += clean_html(html[last_end:])
            
            return result.strip()
            
        except Exception:
            # Fallback to raw text if markdown processing fails
            return text

def main():
    root = TkinterDnD.Tk()
    app = OllamaChatGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()