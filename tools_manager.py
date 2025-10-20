"""
Advanced Tools Manager for Chat Application
Provides async tool execution, status tracking, and error recovery.
"""

import asyncio
import threading
import time
import queue
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Union
from concurrent.futures import ThreadPoolExecutor, Future
import tkinter as tk
from tkinter import ttk
import logging

from error_handler import error_handler


class ToolStatus(Enum):
    """Tool execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class ToolTask:
    """Represents a tool execution task."""
    id: str
    tool_name: str
    operation: str
    status: ToolStatus = ToolStatus.PENDING
    progress: float = 0.0
    message: str = ""
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    timeout: float = 300.0  # 5 minutes default
    cancellable: bool = True
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate task duration if completed."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def is_active(self) -> bool:
        """Check if task is currently active."""
        return self.status in [ToolStatus.PENDING, ToolStatus.RUNNING]


class ToolResultCache:
    """Simple LRU cache for tool results."""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache: Dict[str, Any] = {}
        self.access_order: List[str] = []
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached result."""
        if key in self.cache:
            # Move to end (most recently used)
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None
    
    def put(self, key: str, value: Any) -> None:
        """Cache a result."""
        if key in self.cache:
            # Update existing
            self.cache[key] = value
            self.access_order.remove(key)
            self.access_order.append(key)
        else:
            # Add new
            if len(self.cache) >= self.max_size:
                # Remove least recently used
                oldest = self.access_order.pop(0)
                del self.cache[oldest]
            
            self.cache[key] = value
            self.access_order.append(key)
    
    def clear(self) -> None:
        """Clear all cached results."""
        self.cache.clear()
        self.access_order.clear()


class ToolsManager:
    """Advanced tools manager with async execution and status tracking."""
    
    def __init__(self, max_concurrent_tools: int = 3):
        """Initialize the tools manager."""
        self.max_concurrent_tools = max_concurrent_tools
        self.active_tasks: Dict[str, ToolTask] = {}
        self.completed_tasks: Dict[str, ToolTask] = {}
        self.task_futures: Dict[str, Future] = {}
        self.result_cache = ToolResultCache()
        
        # Thread pool for executing tools
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_tools)
        
        # Event handlers
        self.status_callbacks: List[Callable[[ToolTask], None]] = []
        self.completion_callbacks: List[Callable[[ToolTask], None]] = []
        
        # UI update queue for thread-safe UI updates
        self.ui_update_queue = queue.Queue()
        
        # Shutdown flag
        self._shutdown = False
        
        # Background thread for monitoring tasks
        self.monitor_thread = threading.Thread(target=self._monitor_tasks, daemon=True)
        self.monitor_thread.start()
    
    def register_status_callback(self, callback: Callable[[ToolTask], None]) -> None:
        """Register a callback for status updates."""
        self.status_callbacks.append(callback)
    
    def register_completion_callback(self, callback: Callable[[ToolTask], None]) -> None:
        """Register a callback for task completion."""
        self.completion_callbacks.append(callback)
    
    def _notify_status_change(self, task: ToolTask) -> None:
        """Notify all registered callbacks of status change."""
        for callback in self.status_callbacks:
            try:
                callback(task)
            except Exception as e:
                error_handler.handle_error(e, "Tool status callback")
    
    def _notify_completion(self, task: ToolTask) -> None:
        """Notify all registered callbacks of task completion."""
        for callback in self.completion_callbacks:
            try:
                callback(task)
            except Exception as e:
                error_handler.handle_error(e, "Tool completion callback")
    
    def submit_tool_task(
        self,
        tool_name: str,
        operation: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        timeout: float = 300.0,
        cancellable: bool = True,
        cache_key: Optional[str] = None
    ) -> str:
        """
        Submit a tool task for execution.
        
        Returns:
            str: Task ID for tracking
        """
        kwargs = kwargs or {}
        
        # Check cache first
        if cache_key:
            cached_result = self.result_cache.get(cache_key)
            if cached_result is not None:
                # Return cached result immediately
                task_id = str(uuid.uuid4())
                task = ToolTask(
                    id=task_id,
                    tool_name=tool_name,
                    operation=operation,
                    status=ToolStatus.COMPLETED,
                    progress=100.0,
                    message="Retrieved from cache",
                    result=cached_result,
                    started_at=time.time(),
                    completed_at=time.time(),
                    timeout=timeout,
                    cancellable=False
                )
                self.completed_tasks[task_id] = task
                self._notify_completion(task)
                return task_id
        
        # Check if we're at capacity
        if len(self.active_tasks) >= self.max_concurrent_tools:
            raise RuntimeError(f"Maximum concurrent tools ({self.max_concurrent_tools}) reached")
        
        # Create new task
        task_id = str(uuid.uuid4())
        task = ToolTask(
            id=task_id,
            tool_name=tool_name,
            operation=operation,
            timeout=timeout,
            cancellable=cancellable
        )
        
        self.active_tasks[task_id] = task
        
        # Submit to thread pool
        future = self.executor.submit(self._execute_tool_task, task, func, args, kwargs, cache_key)
        self.task_futures[task_id] = future
        
        # Notify status change
        self._notify_status_change(task)
        
        return task_id
    
    def _execute_tool_task(
        self,
        task: ToolTask,
        func: Callable,
        args: tuple,
        kwargs: dict,
        cache_key: Optional[str]
    ) -> Any:
        """Execute a tool task in the thread pool."""
        try:
            # Update status to running
            task.status = ToolStatus.RUNNING
            task.started_at = time.time()
            task.message = f"Executing {task.operation}..."
            self._notify_status_change(task)
            
            # Execute the function with timeout
            start_time = time.time()
            result = func(*args, **kwargs)
            
            # Check if task was cancelled during execution
            if task.status == ToolStatus.CANCELLED:
                return None
            
            # Update progress and complete
            task.progress = 100.0
            task.status = ToolStatus.COMPLETED
            task.completed_at = time.time()
            task.result = result
            task.message = f"Completed {task.operation} in {task.duration:.2f}s"
            
            # Cache result if cache key provided
            if cache_key and result is not None:
                self.result_cache.put(cache_key, result)
            
            return result
            
        except Exception as e:
            task.status = ToolStatus.FAILED
            task.completed_at = time.time()
            task.error = str(e)
            task.message = f"Failed: {task.error}"
            error_handler.handle_error(e, f"Tool execution ({task.tool_name})")
            return None
            
        finally:
            # Move task to completed and notify
            if task.id in self.active_tasks:
                del self.active_tasks[task.id]
            self.completed_tasks[task.id] = task
            
            # Clean up future
            if task.id in self.task_futures:
                del self.task_futures[task.id]
            
            self._notify_status_change(task)
            self._notify_completion(task)
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            if task.cancellable and task.status in [ToolStatus.PENDING, ToolStatus.RUNNING]:
                task.status = ToolStatus.CANCELLED
                task.completed_at = time.time()
                task.message = "Cancelled by user"
                
                # Cancel the future if possible
                if task_id in self.task_futures:
                    self.task_futures[task_id].cancel()
                
                self._notify_status_change(task)
                return True
        return False
    
    def get_task_status(self, task_id: str) -> Optional[ToolTask]:
        """Get current status of a task."""
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]
        elif task_id in self.completed_tasks:
            return self.completed_tasks[task_id]
        return None
    
    def get_active_tasks(self) -> List[ToolTask]:
        """Get all currently active tasks."""
        return list(self.active_tasks.values())
    
    def get_completed_tasks(self, limit: int = 10) -> List[ToolTask]:
        """Get recent completed tasks."""
        tasks = sorted(
            self.completed_tasks.values(),
            key=lambda t: t.completed_at or 0,
            reverse=True
        )
        return tasks[:limit]
    
    def clear_completed_tasks(self) -> None:
        """Clear completed task history."""
        self.completed_tasks.clear()
    
    def _monitor_tasks(self) -> None:
        """Background thread to monitor task timeouts."""
        while not self._shutdown:
            try:
                current_time = time.time()
                
                # Check for timeouts
                for task_id, task in list(self.active_tasks.items()):
                    if (task.started_at and 
                        current_time - task.started_at > task.timeout):
                        
                        task.status = ToolStatus.TIMEOUT
                        task.completed_at = current_time
                        task.message = f"Timeout after {task.timeout}s"
                        
                        # Cancel the future
                        if task_id in self.task_futures:
                            self.task_futures[task_id].cancel()
                        
                        # Move to completed
                        del self.active_tasks[task_id]
                        self.completed_tasks[task_id] = task
                        
                        self._notify_status_change(task)
                        self._notify_completion(task)
                
                # Clean up old completed tasks (keep last 50)
                if len(self.completed_tasks) > 50:
                    old_tasks = sorted(
                        self.completed_tasks.items(),
                        key=lambda x: x[1].completed_at or 0
                    )[:-50]
                    
                    for task_id, _ in old_tasks:
                        del self.completed_tasks[task_id]
                
                time.sleep(1.0)  # Check every second
                
            except Exception as e:
                error_handler.handle_error(e, "Task monitor")
                time.sleep(5.0)  # Wait longer on error
    
    def shutdown(self) -> None:
        """Shutdown the tools manager."""
        self._shutdown = True
        
        # Cancel all active tasks
        for task_id in list(self.active_tasks.keys()):
            self.cancel_task(task_id)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)