"""
Tool Status Panel UI Component
Provides visual feedback for tool operations with progress bars and status updates.
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Dict, Optional, List
from tools_manager import ToolsManager, ToolTask, ToolStatus


class ToolStatusPanel:
    """UI panel for displaying tool execution status and progress."""
    
    def __init__(self, parent, tools_manager: ToolsManager):
        """Initialize the tool status panel."""
        self.parent = parent
        self.tools_manager = tools_manager
        self.task_widgets: Dict[str, Dict] = {}
        self.panel_visible = False
        
        # Create the main panel (initially hidden)
        self.panel_frame = None
        self.create_panel()
        
        # Register callbacks with tools manager
        self.tools_manager.register_status_callback(self.on_task_status_update)
        self.tools_manager.register_completion_callback(self.on_task_completion)
        
        # Auto-hide timer
        self.auto_hide_timer = None
    
    def create_panel(self):
        """Create the status panel UI."""
        # Create floating panel frame
        self.panel_frame = ttk.Frame(self.parent, style="StatusPanel.TFrame")
        
        # Header with title and close button
        header_frame = ttk.Frame(self.panel_frame)
        header_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        self.title_label = ttk.Label(
            header_frame,
            text="Tool Operations",
            font=("Segoe UI", 10, "bold")
        )
        self.title_label.pack(side=tk.LEFT)
        
        # Close button
        self.close_button = ttk.Button(
            header_frame,
            text="✕",
            width=3,
            command=self.hide_panel
        )
        self.close_button.pack(side=tk.RIGHT)
        
        # Clear completed button
        self.clear_button = ttk.Button(
            header_frame,
            text="Clear",
            command=self.clear_completed_tasks
        )
        self.clear_button.pack(side=tk.RIGHT, padx=(0, 5))
        
        # Scrollable content area
        self.canvas = tk.Canvas(
            self.panel_frame,
            height=200,
            highlightthickness=0
        )
        self.scrollbar = ttk.Scrollbar(
            self.panel_frame,
            orient="vertical",
            command=self.canvas.yview
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.content_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.content_frame,
            anchor="nw"
        )
        
        # Pack scrollable area
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Bind canvas resize
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        self.content_frame.bind('<Configure>', self.on_frame_configure)
        
        # Position panel (initially hidden)
        self.hide_panel()
    
    def on_canvas_configure(self, event):
        """Handle canvas resize."""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def on_frame_configure(self, event):
        """Handle content frame resize."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def show_panel(self):
        """Show the status panel."""
        if not self.panel_visible:
            self.panel_visible = True
            
            # Position panel in bottom-right corner
            self.parent.update_idletasks()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
            
            panel_width = 350
            panel_height = 250
            
            x = parent_width - panel_width - 20
            y = parent_height - panel_height - 20
            
            self.panel_frame.place(
                x=x,
                y=y,
                width=panel_width,
                height=panel_height
            )
            
            # Bring to front
            self.panel_frame.lift()
            
            # Cancel auto-hide timer
            if self.auto_hide_timer:
                self.parent.after_cancel(self.auto_hide_timer)
                self.auto_hide_timer = None
    
    def hide_panel(self):
        """Hide the status panel."""
        if self.panel_visible:
            self.panel_visible = False
            self.panel_frame.place_forget()
            
            # Cancel auto-hide timer
            if self.auto_hide_timer:
                self.parent.after_cancel(self.auto_hide_timer)
                self.auto_hide_timer = None
    
    def schedule_auto_hide(self, delay_ms: int = 5000):
        """Schedule panel to auto-hide after delay."""
        if self.auto_hide_timer:
            self.parent.after_cancel(self.auto_hide_timer)
        
        self.auto_hide_timer = self.parent.after(delay_ms, self.auto_hide_if_no_active)
    
    def auto_hide_if_no_active(self):
        """Auto-hide panel if no active tasks."""
        active_tasks = self.tools_manager.get_active_tasks()
        if not active_tasks:
            self.hide_panel()
    
    def on_task_status_update(self, task: ToolTask):
        """Handle task status update."""
        # Schedule UI update on main thread
        self.parent.after(0, lambda: self._update_task_widget(task))
    
    def on_task_completion(self, task: ToolTask):
        """Handle task completion."""
        # Schedule UI update on main thread
        self.parent.after(0, lambda: self._on_task_completed(task))
    
    def _update_task_widget(self, task: ToolTask):
        """Update or create task widget (main thread only)."""
        if task.id not in self.task_widgets:
            self._create_task_widget(task)
        
        widgets = self.task_widgets[task.id]
        
        # Update progress bar
        widgets['progress']['value'] = task.progress
        
        # Update status text
        status_text = f"{task.tool_name} - {task.operation}"
        if task.status == ToolStatus.RUNNING:
            status_text += f" ({task.progress:.0f}%)"
        widgets['status_label']['text'] = status_text
        
        # Update message
        widgets['message_label']['text'] = task.message
        
        # Update colors based on status
        if task.status == ToolStatus.RUNNING:
            widgets['progress']['style'] = "Running.Horizontal.TProgressbar"
        elif task.status == ToolStatus.COMPLETED:
            widgets['progress']['style'] = "Success.Horizontal.TProgressbar"
        elif task.status in [ToolStatus.FAILED, ToolStatus.TIMEOUT]:
            widgets['progress']['style'] = "Error.Horizontal.TProgressbar"
        elif task.status == ToolStatus.CANCELLED:
            widgets['progress']['style'] = "Warning.Horizontal.TProgressbar"
        
        # Show panel if not visible and task is active
        if task.is_active and not self.panel_visible:
            self.show_panel()
    
    def _create_task_widget(self, task: ToolTask):
        """Create UI widget for a task."""
        # Task frame
        task_frame = ttk.Frame(self.content_frame, style="TaskFrame.TFrame")
        task_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Status label
        status_label = ttk.Label(
            task_frame,
            text=f"{task.tool_name} - {task.operation}",
            font=("Segoe UI", 9, "bold")
        )
        status_label.pack(anchor=tk.W)
        
        # Progress bar
        progress_bar = ttk.Progressbar(
            task_frame,
            mode='determinate',
            length=300,
            style="Default.Horizontal.TProgressbar"
        )
        progress_bar.pack(fill=tk.X, pady=(2, 0))
        
        # Message label
        message_label = ttk.Label(
            task_frame,
            text=task.message,
            font=("Segoe UI", 8),
            foreground="gray"
        )
        message_label.pack(anchor=tk.W)
        
        # Cancel button (if cancellable)
        cancel_button = None
        if task.cancellable and task.is_active:
            button_frame = ttk.Frame(task_frame)
            button_frame.pack(fill=tk.X, pady=(2, 0))
            
            cancel_button = ttk.Button(
                button_frame,
                text="Cancel",
                width=8,
                command=lambda: self.cancel_task(task.id)
            )
            cancel_button.pack(side=tk.RIGHT)
        
        # Store widget references
        self.task_widgets[task.id] = {
            'frame': task_frame,
            'status_label': status_label,
            'progress': progress_bar,
            'message_label': message_label,
            'cancel_button': cancel_button
        }
        
        # Update scroll region
        self.content_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_task_completed(self, task: ToolTask):
        """Handle task completion UI updates."""
        if task.id in self.task_widgets:
            widgets = self.task_widgets[task.id]
            
            # Hide cancel button
            if widgets['cancel_button']:
                widgets['cancel_button'].destroy()
                widgets['cancel_button'] = None
            
            # Update final status
            self._update_task_widget(task)
        
        # Schedule auto-hide if no more active tasks
        active_tasks = self.tools_manager.get_active_tasks()
        if not active_tasks and self.panel_visible:
            self.schedule_auto_hide(3000)  # Hide after 3 seconds
    
    def cancel_task(self, task_id: str):
        """Cancel a task."""
        success = self.tools_manager.cancel_task(task_id)
        if success and task_id in self.task_widgets:
            widgets = self.task_widgets[task_id]
            if widgets['cancel_button']:
                widgets['cancel_button']['state'] = 'disabled'
                widgets['cancel_button']['text'] = "Cancelling..."
    
    def clear_completed_tasks(self):
        """Clear completed task widgets."""
        completed_task_ids = []
        
        for task_id, widgets in self.task_widgets.items():
            task = self.tools_manager.get_task_status(task_id)
            if task and not task.is_active:
                completed_task_ids.append(task_id)
        
        for task_id in completed_task_ids:
            widgets = self.task_widgets[task_id]
            widgets['frame'].destroy()
            del self.task_widgets[task_id]
        
        # Clear from tools manager
        self.tools_manager.clear_completed_tasks()
        
        # Update scroll region
        self.content_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # Hide panel if empty
        if not self.task_widgets:
            self.hide_panel()
    
    def configure_styles(self, style):
        """Configure custom styles for the status panel."""
        # Panel frame style
        style.configure(
            "StatusPanel.TFrame",
            background="#f8f9fa",
            relief="raised",
            borderwidth=2
        )
        
        # Task frame style
        style.configure(
            "TaskFrame.TFrame",
            background="#ffffff",
            relief="solid",
            borderwidth=1
        )
        
        # Progress bar styles
        style.configure(
            "Running.Horizontal.TProgressbar",
            background="#007bff",
            troughcolor="#e9ecef"
        )
        
        style.configure(
            "Success.Horizontal.TProgressbar",
            background="#28a745",
            troughcolor="#e9ecef"
        )
        
        style.configure(
            "Error.Horizontal.TProgressbar",
            background="#dc3545",
            troughcolor="#e9ecef"
        )
        
        style.configure(
            "Warning.Horizontal.TProgressbar",
            background="#ffc107",
            troughcolor="#e9ecef"
        )