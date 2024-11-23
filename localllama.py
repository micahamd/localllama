try:
    import ollama  # Attempt to import the ollama library
except ImportError as e:
    print(f"Error importing ollama: {str(e)}")  # Print error message if import fails
    # Handle the error or exit the application
    exit(1)  # Exit the program with status code 1

import tkinter as tk  # Import tkinter for GUI components
from tkinter import scrolledtext, filedialog  # Import specific tkinter modules
import threading  # Import threading for concurrent execution
from tkinter import ttk, font  # Import themed tkinter widgets and font module
from tkinterdnd2 import DND_FILES, TkinterDnD  # Import drag-and-drop support for tkinter
import os  # Import os for operating system related functions
from docx import Document  # Import Document from python-docx for .docx file handling
import PyPDF2  # Import PyPDF2 for PDF file handling
import re  # Import regular expressions module
import markdown  # Import markdown for processing markdown text
from pygments import highlight  # Import highlight function from pygments for syntax highlighting
from pygments.lexers import get_lexer_by_name  # Import lexer retrieval by name
from pygments.formatters import BBCodeFormatter  # Import BBCodeFormatter for formatting code
import matplotlib.pyplot as plt  # Import matplotlib for plotting
import io  # Import io for handling streams
from PIL import Image, ImageTk  # Import PIL modules for image handling

class OllamaChatGUI:
    def on_temp_change(self, value):
        """Update temperature label when slider moves"""
        self.temp_label.config(text=f"{float(value):.2f}")  # Update temperature label with slider value
    
    def __init__(self, root):
        self.root = root  # Set the root window
        self.root.title("Ollama Chat")  # Set window title
        self.file_img = None  # Initialize file image variable
        self.file_content = None  # Initialize file content variable
        self.file_type = None  # Initialize file type variable
        self.word_count = 0  # Initialize word count
        self.selected_model = None  # Initialize selected model variable
        
        # Create main chat frame first
        self.chat_frame = ttk.Frame(root)  # Create a frame for chat
        self.chat_frame.pack(padx=10, pady=10, expand=True, fill='both')  # Pack the chat frame with padding and expansion
        
        # Create chat display with scrollbar
        self.chat_display = tk.Text(self.chat_frame, wrap=tk.WORD, width=50, height=20)  # Create a Text widget for chat display
        self.chat_display.pack(side='left', expand=True, fill='both')  # Pack the chat display on the left
        scrollbar = ttk.Scrollbar(self.chat_frame, orient='vertical', command=self.chat_display.yview)  # Create a vertical scrollbar
        scrollbar.pack(side='right', fill='y')  # Pack the scrollbar on the right
        self.chat_display['yscrollcommand'] = scrollbar.set  # Link scrollbar to chat display
        
        # Make read-only but allow selection
        self.chat_display.bind("<Key>", lambda e: "break" if e.keysym not in ("c", "C", "Control_L", "Control_R") else "")  # Bind keys to prevent editing
        
        # Create model frame and controls
        model_frame = ttk.Frame(root)  # Create a frame for model controls
        model_frame.pack(side='top', padx=10, pady=5)  # Pack the model frame at the top with padding
        
        # Model selector
        self.model_selector = ttk.Combobox(model_frame, state='readonly')  # Create a Combobox for model selection
        self.model_selector.pack(side='left', padx=(5,0))  # Pack the Combobox on the left with padding
        self.update_model_list()  # Populate the model list
        self.model_selector.bind('<<ComboboxSelected>>', self.on_model_selected)  # Bind selection event to handler
        
        # Temperature controls
        temp_frame = ttk.Frame(model_frame)  # Create a frame for temperature controls
        temp_frame.pack(side='left', padx=(10,0))  # Pack the temperature frame on the left with padding
        
        ttk.Label(temp_frame, text="Temp:").pack(side='left')  # Create and pack a label for temperature
        self.temperature = tk.DoubleVar(value=0.7)  # Initialize temperature variable with default value
        self.temp_label = ttk.Label(temp_frame, text="0.70")  # Create a label to display temperature value
        self.temp_label.pack(side='right', padx=(5,0))  # Pack the temperature label on the right with padding
        
        self.temp_slider = ttk.Scale(
            temp_frame,
            from_=0.0,
            to=1.0,
            orient='horizontal',
            length=100,
            variable=self.temperature,
            command=self.on_temp_change  # Add callback for slider movement
        )  # Create a slider for temperature adjustment
        self.temp_slider.pack(side='left')  # Pack the slider on the left
        
        # Context window controls
        context_frame = ttk.Frame(model_frame)  # Create a frame for context window controls
        context_frame.pack(side='left', padx=(10,0))  # Pack the context frame on the left with padding
        
        ttk.Label(context_frame, text="Context:").pack(side='left')  # Create and pack a label for context size
        self.context_size = tk.IntVar(value=4096)  # Initialize context size variable with default value
        self.context_label = ttk.Label(context_frame, text="4096")  # Create a label to display context size
        self.context_label.pack(side='right', padx=(5,0))  # Pack the context label on the right with padding
        
        self.context_slider = ttk.Scale(
            context_frame,
            from_=100,
            to=128000,
            orient='horizontal',
            length=100,
            variable=self.context_size,
            command=self.on_context_change  # Add callback for slider movement
        )  # Create a slider for context window size adjustment
        self.context_slider.pack(side='left')  # Pack the slider on the left
        
        # Chat history checkbox
        self.include_chat_var = tk.BooleanVar()  # Initialize a boolean variable for including chat history
        self.include_chat_checkbox = ttk.Checkbutton(
            model_frame, 
            text="Include chat?",
            variable=self.include_chat_var  # Link checkbox to variable
        )  # Create a checkbox to include chat history
        self.include_chat_checkbox.pack(side='left', padx=(10,0))  # Pack the checkbox on the left with padding
        
        # 4. Create input area
        input_frame = ttk.Frame(root)  # Create a frame for input area
        input_frame.pack(padx=10, pady=(0, 10), fill='x')  # Pack the input frame with padding and fill horizontally
        
        self.input_field = ttk.Entry(input_frame)  # Create an Entry widget for user input
        self.input_field.pack(side='left', expand=True, fill='x', padx=(0, 5))  # Pack the input field on the left with expansion and padding
        
        # Button frame
        button_frame = ttk.Frame(input_frame)  # Create a frame for buttons
        button_frame.pack(side='right', padx=(5, 0))  # Pack the button frame on the right with padding
        
        clear_button = ttk.Button(button_frame, text="Clear Chat", command=self.clear_chat)  # Create a button to clear chat
        clear_button.pack(side='right', padx=(5, 0))  # Pack the clear button on the right with padding
        
        batch_button = ttk.Button(button_frame, text="Batch Process", command=self.start_batch_process)  # Create a button for batch processing
        batch_button.pack(side='right', padx=(5, 0))  # Pack the batch button on the right with padding
        
        send_button = ttk.Button(button_frame, text="Send", command=self.send_message)  # Create a button to send message
        send_button.pack(side='right')  # Pack the send button on the right
        
        # 5. Final setup
        self.is_processing = False  # Initialize processing flag
        self.input_field.bind('<Return>', lambda e: self.send_message())  # Bind Enter key to send message
        self.chat_display.drop_target_register(DND_FILES)  # Register drop target for files
        self.chat_display.dnd_bind('<<Drop>>', self.handle_drop)  # Bind drop event to handler
        
        # Configure tags and update status
        self.configure_tags()  # Configure text tags for styling
        self.update_status()  # Update status display
    
    # Context tab
    def on_context_change(self, value):
        """Update context window label when slider moves"""
        self.context_label.config(text=f"{int(float(value))}")  # Update context label with slider value
    
    def handle_drop(self, event):
        file_path = event.data.strip('{}')  # Get the dropped file path and remove braces
        self.file_type = self.get_file_type(file_path)  # Determine the file type
        
        if self.file_type == 'image':
            self.file_img = file_path  # Set image path
            self.file_content = None  # Reset file content
        else:
            self.file_img = None  # Reset image path
            self.file_content = self.extract_content(file_path)  # Extract content from file
            if self.file_content:
                self.word_count = len(re.findall(r'\w+', self.file_content))  # Count words in content
        
        self.update_status()  # Update status display
    
    def get_file_type(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()  # Get file extension in lowercase
        if ext in ['.jpg', '.jpeg', '.png', '.gif']:
            return 'image'  # Return image type
        elif ext == '.docx':
            return 'docx'  # Return docx type
        elif ext == '.pdf':
            return 'pdf'  # Return pdf type
        elif ext == '.txt':
            return 'txt'  # Return txt type
        return None  # Return None if unsupported
    
    def extract_content(self, file_path):
        try:
            ext = os.path.splitext(file_path)[1].lower()  # Get file extension in lowercase
            if ext == '.docx':
                doc = Document(file_path)  # Open .docx file
                return ' '.join([paragraph.text for paragraph in doc.paragraphs])  # Extract and join text
            elif ext == '.pdf':
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)  # Read PDF file
                    return ' '.join([page.extract_text() for page in pdf_reader.pages])  # Extract and join text
            elif ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()  # Read and return text
            return None  # Return None if unsupported
        except Exception as e:
            print(f"Error extracting content: {str(e)}")  # Print extraction error
            return None  # Return None on failure
    
    def display_message(self, message, tags=None):
        """Display a message in the chat window with optional tags"""
        current_state = self.chat_display["state"]
        self.chat_display["state"] = "normal"
        
        if tags == 'assistant':
            # Process potential code blocks in assistant responses
            parts = message.split('```')
            for i, part in enumerate(parts):
                if i % 2 == 0:  # Regular text
                    self.chat_display.insert(tk.END, part, 'assistant')
                else:  # Code block
                    self.chat_display.insert(tk.END, '\n')  # Add newline before code
                    self.chat_display.insert(tk.END, part.strip(), 'code')
                    self.chat_display.insert(tk.END, '\n')  # Add newline after code
        else:
            self.chat_display.insert(tk.END, message, tags)
        
        self.chat_display["state"] = current_state
        self.chat_display.see(tk.END)
    
    def update_status(self):
        if self.file_img:
            status = f"Image loaded: {self.file_img}"  # Status message for image
        elif self.file_content:
            status = f"Document loaded: {self.file_type.upper()} - {self.word_count} words"  # Status for document
        else:
            status = "No file loaded"  # Status when no file is loaded
        self.display_message(f"\n{status}\n", 'status')  # Display status message with 'status' tag
    
    def send_message(self):
        user_input = self.input_field.get()  # Get user input from entry field
        if not user_input.strip():
            return  # Do nothing if input is empty
                
        # Display user message
        self.display_message("\nYou: ", 'user')  # Display "You: " with 'user' tag
        self.display_message(f"{user_input}\n", 'user')  # Display the actual user input
        
        self.input_field.delete(0, tk.END)  # Clear the input field
        
        # Prepare message content
        content = user_input  # Start with user input
        if self.file_content:
            content += f"\n\nDocument content:\n{self.file_content}"  # Append document content if available
        if self.include_chat_var.get():
            chat_history = self.chat_display.get(1.0, tk.END).strip()  # Get chat history
            content += f"\n\nChat history:\n{chat_history}"  # Append chat history if checkbox is selected
        
        # Prepare message
        message = {
            'role': 'user',
            'content': content  # Set message content
        }
        
        # Add image if available
        if self.file_img:
            with open(self.file_img, 'rb') as img_file:
                message['images'] = [img_file.read()]  # Attach image data to message
                
        # Send message in separate thread
        threading.Thread(target=self.get_response, args=(message,)).start()  # Start thread for response
        self.file_content = None  # Reset file content
        self.file_img = None  # Reset file image
        self.is_processing = False  # Stop any ongoing batch processing
            
    def get_response(self, message):
        try:
            self.display_message("\nAssistant: ", 'assistant')  # Display "Assistant: " with 'assistant' tag
            
            # Create a mark for the response start
            self.chat_display.mark_set("response_start", "end-1c")  # Mark the start position of the response
            full_response = ""  # Initialize full response string
            
            for chunk in ollama.chat(
                model=self.selected_model,  # Use the selected model
                messages=[message],  # Send the message
                stream=True,  # Enable streaming of response
                options={"temperature": self.temperature.get(),
                         "num_ctx": self.context_size.get()
                }  # Set temperature and context size
            ):
                if chunk and 'message' in chunk and 'content' in chunk['message']:
                    content = chunk['message']['content']  # Get content from chunk
                    full_response += content  # Append to full response
                    self.chat_display.delete("response_start", "end-1c")  # Delete previous response text
                    self.display_message(content, 'assistant')  # Display new content with 'assistant' tag
                        
            self.display_message("\n", 'assistant')  # Add a newline after response
            self.file_img = None  # Reset file image
            self.update_status()  # Update status display
                
        except Exception as e:
            self.display_message(f"\nError: {str(e)}\n", 'error')  # Display error message with 'error' tag
                
        self.chat_display.see(tk.END)  # Scroll to the end
    
    def start_batch_process(self):
        if not self.input_field.get().strip():
            self.chat_display.insert(tk.END, "\nPlease enter a prompt first.\n")  # Prompt user to enter input
            return  # Exit if input is empty
                
        directory = filedialog.askdirectory(title="Select Directory for Batch Processing")  # Open directory selection dialog
        if directory:
            self.is_processing = True  # Set processing flag
            threading.Thread(target=self.process_directory, args=(directory,)).start()  # Start batch processing in a new thread
    
    def process_directory(self, directory):
        prompt = self.input_field.get()  # Get the prompt from input field
        self.chat_display.insert(tk.END, f"\nStarting batch processing of directory: {directory}\n")  # Inform user about start
        
        # Collect all files
        files_to_process = []
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)  # Get full file path
                if self.get_file_type(file_path):
                    files_to_process.append(file_path)  # Add supported files to the list
        
        total_files = len(files_to_process)  # Get total number of files
        self.chat_display.insert(tk.END, f"Found {total_files} files to process.\n")  # Display number of files
        self.chat_display.see(tk.END)  # Scroll to the end
        
        for idx, file_path in enumerate(files_to_process, 1):
            if not self.is_processing:
                break  # Exit loop if processing is stopped
                
            self.chat_display.insert(tk.END, f"\nProcessing file {idx}/{total_files}: {os.path.basename(file_path)}\n")  # Inform about current file
            self.chat_display.see(tk.END)  # Scroll to the end
                
            file_type = self.get_file_type(file_path)  # Determine file type
            message = {'role': 'user', 'content': prompt}  # Initialize message with prompt
                
            if file_type == 'image':
                with open(file_path, 'rb') as img_file:
                    message['images'] = [img_file.read()]  # Attach image data to message
            else:
                content = prompt  # Start with prompt
                if self.extract_content(file_path):
                    content += f"\n\nDocument content:\n{self.extract_content(file_path)}"  # Append document content
                if self.include_chat_var.get():
                    chat_history = self.chat_display.get(1.0, tk.END).strip()  # Get chat history
                    content += f"\n\nChat history:\n{chat_history}"  # Append chat history if selected
                message['content'] = content  # Update message content
                
        try:
            self.display_message(f"Assistant (for {os.path.basename(file_path)}): ", 'assistant')
            for chunk in ollama.chat(
                model=self.selected_model,
                messages=[message],
                options={"temperature": self.temperature.get(),
                         "num_ctx": self.context_size.get()
                }, 
                stream=True
            ):
                if not self.is_processing:
                    break
                if chunk and 'message' in chunk and 'content' in chunk['message']:
                    # Use display_message instead of direct insert
                    self.display_message(chunk['message']['content'], 'assistant')
            self.display_message("\n", 'assistant')
        except Exception as e:
            self.display_message(f"Error processing file: {str(e)}\n", 'error')
                
            self.chat_display.see(tk.END)  # Scroll to the end
        
        self.is_processing = False  # Reset processing flag
        self.chat_display.insert(tk.END, "\nBatch processing completed.\n")  # Inform user about completion
        self.chat_display.see(tk.END)  # Scroll to the end
    
    def update_model_list(self):
        try:
            models = ollama.list()  # Retrieve list of available models
            model_names = [model['name'] for model in models['models']]  # Extract model names
            self.model_selector['values'] = model_names  # Set model names in Combobox
            if model_names:
                self.model_selector.set(model_names[0])  # Select the first model by default
                self.selected_model = model_names[0]  # Set selected model variable
        except Exception as e:
            self.chat_display.insert(tk.END, f"\nError fetching models: {str(e)}\n")  # Display error message
            self.chat_display.see(tk.END)  # Scroll to the end
    
    def on_model_selected(self, event):
        self.selected_model = self.model_selector.get()  # Get selected model from Combobox
        self.chat_display.insert(tk.END, f"\nSwitched to model: {self.selected_model}\n")  # Inform user about model switch
        self.chat_display.see(tk.END)  # Scroll to the end
    
    def clear_chat(self):
        self.chat_display.delete(1.0, tk.END)  # Clear all text in chat display
        self.update_status()  # Update status display
    
    def configure_tags(self):
        self.chat_display.tag_configure('user', foreground='#0077cc', font=('Arial', 10, 'bold'))  # Configure 'user' text style
        self.chat_display.tag_configure('assistant', foreground='#800080', font=('Arial', 10))  # Configure 'assistant' text style
            # Enhanced code block styling
        self.chat_display.tag_configure('code', 
            font=('Consolas', 10, 'bold'),         # Monospaced bold font
            background='#e0e0e0',                  # Slightly darker gray background
            foreground='black',                    # Black text for contrast
            spacing1=10,                           # Space above
            spacing3=10,                           # Space below
            lmargin1=20,                           # Left margin for first line
            lmargin2=20,                           # Left margin for wrapped lines
            relief='raised',                       # Raised border for distinction
            borderwidth=1,                         # Border width
            wrap='none'                            # Prevent text wrapping within code blocks
        )
        self.chat_display.tag_configure('error', foreground='red')  # Configure 'error' text style
        self.chat_display.tag_configure('status', foreground='gray')  # Configure 'status' text style
    
    def format_markdown(self, text):
        # Convert markdown to plain text while preserving formatting
        try:
            # Remove HTML tags but keep content
            def clean_html(html_text):
                # Basic HTML tag removal while preserving content
                text = re.sub(r'<[^>]+>', '', html_text)  # Remove HTML tags
                # Convert HTML entities
                text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')  # Replace HTML entities
                text = text.replace('&quot;', '"').replace('&apos;', "'")  # Replace more HTML entities
                return text
        
            # Convert markdown to HTML first
            html = markdown.markdown(text, extensions=['fenced_code', 'tables'])  # Convert markdown to HTML with extensions
            
            # Process code blocks specially
            code_pattern = r'<pre><code.*?>(.*?)</code></pre>'  # Regex pattern to find code blocks
            result = ''  # Initialize result string
            last_end = 0  # Initialize last end position
            
            for match in re.finditer(code_pattern, html, re.DOTALL):
                # Add cleaned text before code block
                result += clean_html(html[last_end:match.start()])  # Append text before code block
                
                # Format code block
                code = match.group(1)  # Extract code content
                code = clean_html(code)  # Clean code content
                # Add code block with proper formatting
                result += f"\n```\n{code}\n```\n"  # Append formatted code block
                
                last_end = match.end()  # Update last end position
            
            # Add remaining cleaned text
            result += clean_html(html[last_end:])  # Append any remaining text after last code block
                
            return result.strip()  # Return the formatted result stripped of leading/trailing whitespace
                
        except Exception:
            # Fallback to raw text if markdown processing fails
            return text  # Return original text if an error occurs

def main():
    root = TkinterDnD.Tk()  # Initialize the main TkinterDnD root window
    app = OllamaChatGUI(root)  # Create an instance of the OllamaChatGUI class
    root.mainloop()  # Start the Tkinter main event loop

if __name__ == "__main__":
    main()  # Execute the main function if the script is run directly