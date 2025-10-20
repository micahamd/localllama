import logging
import traceback
import tkinter as tk
import sys
from typing import Callable, Optional, Any
from datetime import datetime
import functools
import os

class ErrorHandler:
    """Centralized error handling for the application."""
    
    def __init__(self, log_file=None):
        """Initialize the error handler with optional log file."""
        self.display_callback = None
        self.log_file = log_file or os.path.join(os.getcwd(), "error_log.txt")
        self.setup_logging()
        
    def setup_logging(self):
        """Configure logging to file."""
        logging.basicConfig(
            filename=self.log_file,
            level=logging.ERROR,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def set_display_callback(self, callback):
        """Set the callback function for displaying errors in the UI."""
        self.display_callback = callback
    
    def handle_error(self, error, context=""):
        """Handle an error by logging it and optionally displaying it."""
        error_msg = f"{context} error: {str(error)}"
        
        # Get the full traceback
        tb = traceback.format_exc()
        
        # Log the error
        logging.error(f"{error_msg}\n{tb}")
        
        # Print to console
        print(f"ERROR: {error_msg}")
        
        # Display in UI if callback is set
        if self.display_callback:
            self.display_callback(error_msg, "error")
        
        return error_msg
    
    def log_info(self, message, context=""):
        """Log an informational message."""
        info_msg = f"{context}: {message}"
        logging.info(info_msg)
        
    def log_warning(self, message, context=""):
        """Log a warning message."""
        warning_msg = f"{context}: {message}"
        logging.warning(warning_msg)
        print(f"WARNING: {warning_msg}")

# Create a singleton instance
error_handler = ErrorHandler()

def safe_execute(context=""):
    """Decorator to safely execute a function and handle any exceptions."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler.handle_error(e, context)
                return None
        return wrapper
    return decorator
