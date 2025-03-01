import logging
import traceback
import tkinter as tk
import sys
from typing import Callable, Optional, Any
from datetime import datetime

class ErrorHandler:
    """Handles errors and provides user-friendly error messages."""
    
    def __init__(self, log_file: str = "error_log.txt"):
        """Initialize the error handler with a log file."""
        self.log_file = log_file
        self.setup_logging()
        self.display_callback: Optional[Callable[[str, str], None]] = None
        
    def setup_logging(self):
        """Set up logging to file and console."""
        logging.basicConfig(
            level=logging.ERROR,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def set_display_callback(self, callback: Callable[[str, str], None]):
        """Set a callback function to display errors in the UI."""
        self.display_callback = callback
        
    def handle_error(self, error: Exception, context: str = "", user_msg: Optional[str] = None) -> str:
        """Handle an exception by logging it and returning a user-friendly message."""
        # Get detailed error info
        error_type = type(error).__name__
        error_msg = str(error)
        stack_trace = traceback.format_exc()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create a detailed log message
        log_message = (
            f"[{timestamp}] {error_type} in {context}: {error_msg}\n"
            f"Stack trace:\n{stack_trace}"
        )
        
        # Log the error
        self.logger.error(log_message)
        
        # Create a user-friendly message
        if not user_msg:
            user_messages = {
                'ConnectionError': "Connection failed. Please check your internet connection and ensure the model server is running.",
                'ValueError': "Invalid value provided. Please check your inputs.",
                'FileNotFoundError': "File not found. Please check the file path.",
                'PermissionError': "Permission denied. Please check file permissions.",
                'KeyError': "A required value is missing. Please try again.",
                'IndexError': "Data index out of range. This might be a data format issue.",
                'TypeError': "Incompatible data types. Please check your inputs.",
                'ModuleNotFoundError': "A required module is missing. Please check your installation.",
                'ImportError': "Failed to import a module. Please check your installation.",
            }
            user_msg = user_messages.get(error_type, f"An error occurred: {error_msg}")
        
        # If there's a display callback, call it
        if self.display_callback:
            self.display_callback(user_msg, "error")
            
        return user_msg
        
    def display_error(self, text_widget: tk.Text, error_msg: str):
        """Display an error message in the provided text widget."""
        text_widget["state"] = "normal"
        text_widget.insert(tk.END, f"\nError: {error_msg}\n", "error")
        text_widget.see(tk.END)
        text_widget["state"] = "disabled"


# Global error handler instance
error_handler = ErrorHandler()


def safe_execute(context: str):
    """Decorator that wraps a function in a try-except block."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler.handle_error(e, context)
                return None
        return wrapper
    return decorator
