import ollama
import tkinter as tk
from tkinter import scrolledtext, filedialog
import threading
from tkinter import ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
from docx import Document
import PyPDF2
import re

class OllamaChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Ollama Chat")
        self.file_img = None
        self.file_content = None
        self.file_type = None
        self.word_count = 0
        
        # Create main chat display
        self.chat_display = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=50, height=20)
        self.chat_display.pack(padx=10, pady=10, expand=True, fill='both')
        
        # Create input frame
        input_frame = ttk.Frame(root)
        input_frame.pack(padx=10, pady=(0, 10), fill='x')
        
        # Create input field
        self.input_field = ttk.Entry(input_frame)
        self.input_field.pack(side='left', expand=True, fill='x', padx=(0, 5))
        
        # Create button frame
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(side='right', padx=(5, 0))
        
        # Create batch process button
        batch_button = ttk.Button(button_frame, text="Batch Process", command=self.start_batch_process)
        batch_button.pack(side='right', padx=(5, 0))
        
        # Create send button
        send_button = ttk.Button(button_frame, text="Send", command=self.send_message)
        send_button.pack(side='right')
        
        self.is_processing = False
        
        # Bind Enter key to send
        self.input_field.bind('<Return>', lambda e: self.send_message())
        
        # Setup drag and drop
        self.chat_display.drop_target_register(DND_FILES)
        self.chat_display.dnd_bind('<<Drop>>', self.handle_drop)
        
        self.update_status()

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

    def update_status(self):
        if self.file_img:
            status = f"Image loaded: {self.file_img}"
        elif self.file_content:
            status = f"Document loaded: {self.file_type.upper()} - {self.word_count} words"
        else:
            status = "No file loaded"
        self.chat_display.insert(tk.END, f"\n{status}\n")
        self.chat_display.see(tk.END)

    def send_message(self):
        user_input = self.input_field.get()
        if not user_input.strip():
            return
            
        # Display user message
        self.chat_display.insert(tk.END, f"\nYou: {user_input}\n")
        self.chat_display.see(tk.END)
        
        # Clear input field
        self.input_field.delete(0, tk.END)
        
        # Prepare message
        message = {
            'role': 'user',
            'content': user_input + (f"\n\nDocument content:\n{self.file_content}" if self.file_content else "")
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
            self.chat_display.insert(tk.END, "\nAssistant: ")
            
            # Stream the response
            for chunk in ollama.chat(
                model="minicpm-v:latest",
                messages=[message],
                stream=True
            ):
                if chunk and 'message' in chunk and 'content' in chunk['message']:
                    self.chat_display.insert(tk.END, chunk['message']['content'])
                    self.chat_display.see(tk.END)
                    
            self.chat_display.insert(tk.END, "\n")
            self.file_img = None  # Clear image after sending
            self.update_status()
            
        except Exception as e:
            self.chat_display.insert(tk.END, f"\nError: {str(e)}\n")
            
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
                content = self.extract_content(file_path)
                if content:
                    message['content'] = f"{prompt}\n\nDocument content:\n{content}"
            
            try:
                self.chat_display.insert(tk.END, f"Assistant (for {os.path.basename(file_path)}): ")
                for chunk in ollama.chat(
                    model="minicpm-v:latest",
                    messages=[message],
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

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = OllamaChatGUI(root)
    root.mainloop()