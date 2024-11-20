import ollama
import tkinter as tk
from tkinter import scrolledtext
import threading
from tkinter import ttk
from tkinterdnd2 import DND_FILES, TkinterDnD

class OllamaChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Ollama Chat")
        self.file_img = None
        
        # Create main chat display
        self.chat_display = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=50, height=20)
        self.chat_display.pack(padx=10, pady=10, expand=True, fill='both')
        
        # Create input frame
        input_frame = ttk.Frame(root)
        input_frame.pack(padx=10, pady=(0, 10), fill='x')
        
        # Create input field
        self.input_field = ttk.Entry(input_frame)
        self.input_field.pack(side='left', expand=True, fill='x', padx=(0, 5))
        
        # Create send button
        send_button = ttk.Button(input_frame, text="Send", command=self.send_message)
        send_button.pack(side='right')
        
        # Bind Enter key to send
        self.input_field.bind('<Return>', lambda e: self.send_message())
        
        # Setup drag and drop
        self.chat_display.drop_target_register(DND_FILES)
        self.chat_display.dnd_bind('<<Drop>>', self.handle_drop)
        
        self.update_status()

    def handle_drop(self, event):
        self.file_img = event.data.strip('{}')  # Remove curly braces from the path
        self.update_status()
        
    def update_status(self):
        status = "Image loaded: " + (self.file_img if self.file_img else "No image")
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
            'content': user_input
        }
        
        # Add image if available
        if self.file_img:
            with open(self.file_img, 'rb') as img_file:
                message['images'] = [img_file.read()]
                
        # Send message in separate thread
        threading.Thread(target=self.get_response, args=(message,)).start()
        
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

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = OllamaChatGUI(root)
    root.mainloop()