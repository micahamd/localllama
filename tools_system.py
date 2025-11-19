"""
Unified Tools System for Chat Application
Consolidates ToolsManager, EnhancedTools, PandaCSVAnalysisTool, and ToolStatusPanel.
"""

import asyncio
import threading
import time
import queue
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Union, Tuple
from concurrent.futures import ThreadPoolExecutor, Future
import tkinter as tk
from tkinter import ttk
import logging
import subprocess
import sys
import os
import hashlib
import requests
import pandas as pd
import re
from markitdown import MarkItDown

from error_handler import error_handler, safe_execute

# ==========================================
# Tools Manager Core
# ==========================================

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

# ==========================================
# Enhanced Tools Implementations
# ==========================================



class EnhancedWebSearchTool:
    """Enhanced web search tool with async execution and caching."""
    
    def __init__(self, tools_manager: ToolsManager):
        self.tools_manager = tools_manager
        self.session = None
        self.crawler_available = False
        self.playwright_installed = False
        
    def _check_dependencies(self) -> Dict[str, bool]:
        """Check if required dependencies are available."""
        status = {
            'crawl4ai': False,
            'playwright': False,
            'playwright_browsers': False
        }
        
        try:
            import crawl4ai
            status['crawl4ai'] = True
            self.crawler_available = True
        except ImportError:
            pass
        
        try:
            import playwright
            status['playwright'] = True
        except ImportError:
            pass
        
        # Check if playwright browsers are installed
        if status['playwright']:
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    # Try to launch a browser
                    browser = p.chromium.launch(headless=True)
                    browser.close()
                    status['playwright_browsers'] = True
                    self.playwright_installed = True
            except Exception:
                pass
        
        return status
    
    def install_dependencies_async(self, progress_callback=None) -> str:
        """Install web search dependencies asynchronously."""
        
        def install_task():
            """Installation task to run in thread pool."""
            steps = [
                ("Installing crawl4ai...", self._install_crawl4ai),
                ("Installing playwright...", self._install_playwright),
                ("Installing playwright browsers...", self._install_playwright_browsers)
            ]
            
            total_steps = len(steps)
            results = []
            
            for i, (step_name, step_func) in enumerate(steps):
                try:
                    if progress_callback:
                        progress = (i / total_steps) * 100
                        progress_callback(progress, step_name)
                    
                    result = step_func()
                    results.append(f"✅ {step_name}: {result}")
                    
                except Exception as e:
                    error_msg = f"❌ {step_name}: {str(e)}"
                    results.append(error_msg)
                    # Continue with other steps even if one fails
            
            if progress_callback:
                progress_callback(100.0, "Installation complete")
            
            return "\\n".join(results)
        
        # Submit installation task
        task_id = self.tools_manager.submit_tool_task(
            tool_name="Web Search",
            operation="Installing dependencies",
            func=install_task,
            timeout=600.0,  # 10 minutes for installation
            cancellable=False  # Don't allow cancellation during installation
        )
        
        return task_id
    
    def _install_crawl4ai(self) -> str:
        """Install crawl4ai package."""
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "crawl4ai"
            ], capture_output=True, text=True)
            return "Successfully installed"
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to install crawl4ai: {e.stderr}")
    
    def _install_playwright(self) -> str:
        """Install playwright package."""
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "playwright"
            ], capture_output=True, text=True)
            return "Successfully installed"
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to install playwright: {e.stderr}")
    
    def _install_playwright_browsers(self) -> str:
        """Install playwright browsers."""
        try:
            subprocess.check_call([
                sys.executable, "-m", "playwright", "install", "--with-deps"
            ], capture_output=True, text=True)
            return "Successfully installed"
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to install browsers: {e.stderr}")
    
    def search_web_async(self, query: str, max_results: int = 3) -> str:
        """Perform web search asynchronously."""
        
        # Create cache key
        cache_key = f"web_search_{hashlib.md5(query.encode()).hexdigest()}_{max_results}"
        
        def search_task():
            """Web search task to run in thread pool."""
            if not self.crawler_available:
                raise Exception("crawl4ai not available. Please install dependencies first.")
            
            return self._perform_crawl4ai_search(query, max_results)
        
        # Submit search task with caching
        task_id = self.tools_manager.submit_tool_task(
            tool_name="Web Search",
            operation=f"Searching: {query[:50]}...",
            func=search_task,
            timeout=120.0,  # 2 minutes for web search
            cancellable=True,
            cache_key=cache_key
        )
        
        return task_id
    
    def _perform_crawl4ai_search(self, query: str, max_results: int) -> str:
        """Perform the actual web search using crawl4ai."""
        import asyncio
        import crawl4ai
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
        
        async def run_search():
            # Configure browser
            browser_config = BrowserConfig(
                headless=True,
                verbose=False
            )
            
            # Configure crawler
            run_config = CrawlerRunConfig(
                cache_mode="ENABLED"
            )
            
            # Create search URL
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            
            results = []
            
            async with AsyncWebCrawler(config=browser_config) as crawler:
                # Get search results
                search_result = await crawler.arun(
                    url=search_url,
                    config=run_config
                )
                
                if search_result.success:
                    # Extract URLs from search results (simplified)
                    import re
                    url_pattern = r'https?://[^\\s<>"]+(?:[^\\s<>"])'
                    urls = re.findall(url_pattern, search_result.markdown)
                    
                    # Filter and limit URLs
                    filtered_urls = []
                    for url in urls:
                        if ('google.com' not in url and 
                            'youtube.com' not in url and
                            len(filtered_urls) < max_results):
                            filtered_urls.append(url)
                    
                    # Crawl each URL
                    for i, url in enumerate(filtered_urls):
                        try:
                            result = await crawler.arun(url=url, config=run_config)
                            if result.success and result.markdown:
                                results.append(f"Source {i+1}: {url}\\n{result.markdown[:1000]}...")
                        except Exception as e:
                            results.append(f"Source {i+1}: {url}\\nError: {str(e)}")
            
            return "\\n\\n".join(results) if results else "No results found"
        
        # Run the async search
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(run_search())
        finally:
            loop.close()


class EnhancedFileTools:
    """Enhanced file read/write tools with async execution."""
    
    def __init__(self, tools_manager: ToolsManager):
        self.tools_manager = tools_manager
        self.markitdown = MarkItDown()
    
    def read_file_async(self, file_path: str) -> str:
        """Read file asynchronously."""
        
        # Create cache key
        cache_key = f"file_read_{hashlib.md5(file_path.encode()).hexdigest()}"
        
        def read_task():
            """File read task to run in thread pool."""
            return self._read_file_content(file_path)
        
        # Submit read task with caching
        task_id = self.tools_manager.submit_tool_task(
            tool_name="File Reader",
            operation=f"Reading: {os.path.basename(file_path)}",
            func=read_task,
            timeout=60.0,  # 1 minute for file reading
            cancellable=True,
            cache_key=cache_key
        )
        
        return task_id
    
    def write_file_async(self, file_path: str, content: str) -> str:
        """Write file asynchronously."""
        
        def write_task():
            """File write task to run in thread pool."""
            return self._write_file_content(file_path, content)
        
        # Submit write task
        task_id = self.tools_manager.submit_tool_task(
            tool_name="File Writer",
            operation=f"Writing: {os.path.basename(file_path)}",
            func=write_task,
            timeout=30.0,  # 30 seconds for file writing
            cancellable=False  # Don't allow cancellation during write
        )
        
        return task_id
    
    def _read_file_content(self, file_path: str) -> str:
        """Read file content using MarkItDown."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not os.path.isfile(file_path):
            raise ValueError(f"Path is not a file: {file_path}")
        
        # Check file size (limit to 10MB)
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:
            raise ValueError(f"File too large: {file_size} bytes (max 10MB)")
        
        try:
            # Use MarkItDown for processing
            result = self.markitdown.convert(file_path)
            return result.text_content
        except Exception as e:
            # Check if it's an encoding error
            error_str = str(e)
            if "UnicodeDecodeError" in error_str or "ascii" in error_str.lower() or "codec can't decode" in error_str.lower():
                return self._fallback_file_read(file_path)
            else:
                # Fallback to simple text reading for other errors
                return self._fallback_file_read(file_path)
    
    def _fallback_file_read(self, file_path: str) -> str:
        """Fallback file reading with multiple encoding strategies."""
        # Try different encodings in order of preference
        encodings_to_try = [
            ('utf-8', 'replace'),
            ('utf-8', 'ignore'), 
            ('latin1', 'replace'),
            ('cp1252', 'replace'),  # Windows default
            ('iso-8859-1', 'replace')
        ]
        
        for encoding, error_handling in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=encoding, errors=error_handling) as f:
                    return f.read()
            except Exception:
                continue
        
        # If all encodings fail, try binary read and decode with error replacement
        try:
            with open(file_path, 'rb') as f:
                raw_content = f.read()
                # Try to decode as UTF-8 with replacement
                return raw_content.decode('utf-8', errors='replace')
        except Exception as final_error:
            raise Exception(f"All fallback reading methods failed for {file_path}: {str(final_error)}")
    
    def _write_file_content(self, file_path: str, content: str) -> str:
        """Write file content safely."""
        # Validate content size (limit to 10MB)
        if len(content) > 10 * 1024 * 1024:
            raise ValueError(f"Content too large: {len(content)} characters (max 10MB)")
        
        # Ensure directory exists
        directory = os.path.dirname(file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        
        # Create backup if file exists
        backup_created = False
        if os.path.exists(file_path):
            backup_path = f"{file_path}.backup"
            try:
                import shutil
                shutil.copy2(file_path, backup_path)
                backup_created = True
            except Exception:
                pass  # Continue without backup
        
        # Write the file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Verify the write
            with open(file_path, 'r', encoding='utf-8') as f:
                written_content = f.read()
            
            if written_content != content:
                raise Exception("File write verification failed")
            
            result = f"Successfully wrote {len(content)} characters to {file_path}"
            if backup_created:
                result += f" (backup created: {backup_path})"
            
            return result
            
        except Exception as e:
            # Try to restore backup if write failed
            if backup_created:
                try:
                    import shutil
                    shutil.copy2(backup_path, file_path)
                except Exception:
                    pass
            raise Exception(f"Failed to write file: {str(e)}")


class EnhancedDependencyManager:
    """Enhanced dependency manager with background installation."""
    
    def __init__(self, tools_manager: ToolsManager):
        self.tools_manager = tools_manager
        self.installation_cache = {}
    
    def install_package_async(self, package_name: str, pip_args: List[str] = None) -> str:
        """Install a Python package asynchronously."""
        pip_args = pip_args or []
        
        # Check if already installed
        if self._is_package_installed(package_name):
            return f"Package {package_name} is already installed"
        
        def install_task():
            """Package installation task."""
            return self._install_package(package_name, pip_args)
        
        # Submit installation task
        task_id = self.tools_manager.submit_tool_task(
            tool_name="Package Installer",
            operation=f"Installing: {package_name}",
            func=install_task,
            timeout=300.0,  # 5 minutes for package installation
            cancellable=False  # Don't allow cancellation during installation
        )
        
        return task_id

    def manage_dependencies(self, dependencies: List[str], on_success=None, on_error=None) -> str:
        """Install multiple dependencies asynchronously with callbacks."""
        
        def install_dependencies_task():
            """Task to install all dependencies."""
            results = []
            failed_packages = []
            
            for package in dependencies:
                try:
                    if package == "playwright":
                        # Special handling for playwright - install both package and browsers
                        if not self._is_package_installed("playwright"):
                            result = self._install_package("playwright", [])
                            results.append(result)
                        
                        # Install playwright browsers
                        browser_result = self._install_playwright_browsers()
                        results.append(browser_result)
                    else:
                        if not self._is_package_installed(package):
                            result = self._install_package(package, [])
                            results.append(result)
                        else:
                            results.append(f"Package {package} already installed")
                            
                except Exception as e:
                    failed_packages.append(f"{package}: {str(e)}")
            
            if failed_packages:
                error_msg = "Failed to install: " + ", ".join(failed_packages)
                if on_error:
                    # Call error callback (will be called in background thread)
                    try:
                        on_error(error_msg)
                    except Exception:
                        pass  # Ignore callback errors
                raise Exception(error_msg)
            else:
                # All succeeded
                if on_success:
                    # Call success callback (will be called in background thread)
                    try:
                        on_success()
                    except Exception:
                        pass  # Ignore callback errors
                return "All dependencies installed successfully"
        
        # Submit batch installation task
        task_id = self.tools_manager.submit_tool_task(
            tool_name="Dependency Manager",
            operation=f"Installing {len(dependencies)} dependencies",
            func=install_dependencies_task,
            timeout=600.0,  # 10 minutes for multiple packages
            cancellable=False
        )
        
        return task_id

    def _install_playwright_browsers(self) -> str:
        """Install playwright browsers."""
        cmd = [sys.executable, "-m", "playwright", "install", "--with-deps"]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for browser installation
            )
            
            if result.returncode == 0:
                return "Successfully installed Playwright browsers"
            else:
                raise Exception(f"Playwright browser installation failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            raise Exception("Playwright browser installation timeout")
        except Exception as e:
            raise Exception(f"Playwright browser installation error: {str(e)}")
    
    def _is_package_installed(self, package_name: str) -> bool:
        """Check if a package is already installed."""
        try:
            __import__(package_name)
            return True
        except ImportError:
            return False
    
    def _install_package(self, package_name: str, pip_args: List[str]) -> str:
        """Install a package using pip."""
        cmd = [sys.executable, "-m", "pip", "install"] + pip_args + [package_name]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                self.installation_cache[package_name] = True
                return f"Successfully installed {package_name}"
            else:
                raise Exception(f"Installation failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            raise Exception(f"Installation timeout for {package_name}")
        except Exception as e:
            raise Exception(f"Installation error: {str(e)}")


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_backoff: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_backoff = exponential_backoff


def with_retry(retry_config: RetryConfig = None):
    """Decorator to add retry logic to tool functions."""
    if retry_config is None:
        retry_config = RetryConfig()
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(retry_config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < retry_config.max_attempts - 1:
                        # Calculate delay
                        if retry_config.exponential_backoff:
                            delay = min(
                                retry_config.base_delay * (2 ** attempt),
                                retry_config.max_delay
                            )
                        else:
                            delay = retry_config.base_delay
                        
                        time.sleep(delay)
                    else:
                        # Last attempt failed
                        break
            
            # All attempts failed
            raise last_exception
        
        return wrapper
    return decorator
# ==========================================
# Panda CSV Analysis Tool
# ==========================================



class PandaCSVAnalysisTool:
    """
    Manages CSV loading, prompt processing, and result writing.
    Preserves all existing chatbot settings and tool integrations.
    """
    
    def __init__(self):
        """Initialize the CSV analysis tool."""
        self.csv_data: Optional[pd.DataFrame] = None
        self.csv_path: Optional[str] = None
        self.original_headers: List[str] = []
        self.num_rows: int = 0
        self.num_cols: int = 0
        self.is_active: bool = False
        self.rows_processed: int = 0
        self.rows_updated: int = 0
        
    def load_csv(self, file_path: str) -> Dict[str, Any]:
        """
        Load a CSV file and prepare it for processing.
        
        Args:
            file_path: Absolute path to the CSV file
            
        Returns:
            dict: Metadata about the loaded CSV
                {
                    "success": bool,
                    "rows": [start, end],
                    "cols": [start, end],
                    "headers": List[str],
                    "error": str (if success=False)
                }
        """
        try:
            # Load CSV
            self.csv_data = pd.read_csv(file_path)
            self.csv_path = file_path
            
            # Store original headers
            self.original_headers = list(self.csv_data.columns)
            
            # Relabel columns numerically (1, 2, 3...)
            self.csv_data.columns = range(1, len(self.csv_data.columns) + 1)
            
            # Store metadata
            self.num_rows = len(self.csv_data)
            self.num_cols = len(self.csv_data.columns)
            self.is_active = True
            self.rows_processed = 0
            self.rows_updated = 0
            
            return {
                "success": True,
                "rows": [2, self.num_rows + 1],  # Row 1 is header, data starts at 2
                "cols": [1, self.num_cols],
                "headers": self.original_headers,
                "total_rows": self.num_rows,
                "total_cols": self.num_cols
            }
            
        except FileNotFoundError:
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }
        except pd.errors.EmptyDataError:
            return {
                "success": False,
                "error": "CSV file is empty"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error loading CSV: {str(e)}"
            }
    
    def clear(self):
        """Clear all loaded CSV data and reset state."""
        self.csv_data = None
        self.csv_path = None
        self.original_headers = []
        self.num_rows = 0
        self.num_cols = 0
        self.is_active = False
        self.rows_processed = 0
        self.rows_updated = 0
    
    def has_data(self) -> bool:
        """Check if CSV data is loaded."""
        return self.csv_data is not None and self.is_active
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get current CSV metadata."""
        if not self.has_data():
            return {"loaded": False}
        
        return {
            "loaded": True,
            "file_path": self.csv_path,
            "rows": self.num_rows,
            "cols": self.num_cols,
            "headers": self.original_headers,
            "original_headers": self.original_headers,
            "rows_processed": self.rows_processed,
            "rows_updated": self.rows_updated
        }
    
    def extract_row_specification(self, prompt: str) -> Tuple[Optional[str], str]:
        """
        Extract row specification from prompt.
        
        Args:
            prompt: The prompt text potentially containing {R...}
            
        Returns:
            tuple: (row_spec or None, cleaned_prompt without {R...})
            
        Example:
            "{R1-5} Grade these answers" → ("1-5", "Grade these answers")
            "Grade all answers" → (None, "Grade all answers")
        """
        # Pattern: {R followed by row spec} - matches {R1}, {R1-5}, {R1,3,5}, etc.
        pattern = r'\{R([^}]+)\}'
        match = re.search(pattern, prompt)
        
        if match:
            row_spec = match.group(1).strip()
            # Remove the {R...} from prompt
            cleaned_prompt = re.sub(pattern, '', prompt)
            # Clean up common leftover patterns
            # Handle "For {R...}, " -> just remove the whole phrase
            cleaned_prompt = re.sub(r'^For\s*,\s*', '', cleaned_prompt, flags=re.IGNORECASE)
            # Handle leading/trailing commas and extra whitespace
            cleaned_prompt = re.sub(r'^\s*,\s*', '', cleaned_prompt)  # Leading comma
            cleaned_prompt = re.sub(r'\s*,\s*$', '', cleaned_prompt)  # Trailing comma
            cleaned_prompt = re.sub(r'\s+', ' ', cleaned_prompt).strip()  # Multiple spaces
            return row_spec, cleaned_prompt
        
        return None, prompt
    
    def process_prompt_for_row(self, user_prompt: str, row_idx: int) -> Tuple[str, List[int], Dict[str, str]]:
        """
        Process user prompt for a specific row by substituting column references.
        
        Args:
            user_prompt: Raw user prompt with {CX} and {{CX}} references
            row_idx: 0-based row index in the DataFrame
            
        Returns:
            Tuple containing:
                - processed_prompt: Prompt with substitutions for the model
                - output_columns: List of column indices to expect in response
                - substitutions: Dict of what was substituted (for logging)
        
        Syntax:
            {CX}   - INPUT: Read from column X, substitute with actual value
            {{CX}} - OUTPUT: Write to column X, convert to COLUMN_X marker
        
        Example:
            Input:  "Grade {C4} based on {C3}. Write to {{C5}} and {{C6}}."
            Output: "Grade 'Four' based on 'What is 2+2?'. Write to COLUMN_5 and COLUMN_6."
                    [5, 6], {"C3": "What is 2+2?", "C4": "Four"}
        """
        if not self.has_data():
            raise ValueError("No CSV data loaded")
        
        if row_idx < 0 or row_idx >= self.num_rows:
            raise IndexError(f"Row index {row_idx} out of range (0-{self.num_rows-1})")
        
        processed_prompt = user_prompt
        output_columns = []
        substitutions = {}
        
        # Step 1: Process OUTPUT columns (double braces) FIRST
        # Use regex to find all {{CX}} patterns
        output_pattern = r'\{\{C(\d+)\}\}'
        output_refs = re.findall(output_pattern, user_prompt)
        
        for col_num in output_refs:
            col_idx = int(col_num)
            output_columns.append(col_idx)
            
            # Replace {{CX}} with COLUMN_X for model clarity
            processed_prompt = processed_prompt.replace(
                f"{{{{C{col_num}}}}}", 
                f"COLUMN_{col_num}"
            )
            substitutions[f"{{C{col_num}}}"] = f"COLUMN_{col_num}"
        
        # Step 2: Process INPUT columns (single braces)
        # Note: We've already replaced {{}} above, so only single braces remain
        input_pattern = r'\{C(\d+)\}'
        input_refs = re.findall(input_pattern, processed_prompt)
        
        for col_num in input_refs:
            col_idx = int(col_num)
            
            # Get cell value
            cell_value = self._get_cell_value(row_idx, col_idx)
            
            # Substitute in prompt
            processed_prompt = processed_prompt.replace(
                f"{{C{col_num}}}", 
                f"'{cell_value}'"
            )
            substitutions[f"C{col_num}"] = cell_value
        
        return processed_prompt, output_columns, substitutions
    
    def _get_cell_value(self, row_idx: int, col_idx: int) -> str:
        """
        Get formatted cell value from DataFrame.
        
        Args:
            row_idx: 0-based row index
            col_idx: 1-based column index (as stored in DataFrame)
            
        Returns:
            str: Formatted cell value
        """
        if col_idx > self.num_cols:
            return "[Column does not exist]"
        
        try:
            cell_value = self.csv_data.at[row_idx, col_idx]
            
            # Handle NaN, None, and empty strings
            if pd.isna(cell_value):
                return "[Empty]"
            
            cell_str = str(cell_value).strip()
            if cell_str == "":
                return "[Empty]"
            
            return cell_str
            
        except Exception as e:
            return f"[Error: {str(e)}]"
    
    def parse_model_response(self, response: str, expected_columns: List[int]) -> Dict[int, str]:
        """
        Parse model response for COLUMN_X: value patterns.
        
        Args:
            response: Raw model response text
            expected_columns: List of column indices we expect to find
            
        Returns:
            dict: {column_index: value} mapping
        
        Example:
            Input:  "The answer is correct.\nCOLUMN_5: 3.0\nCOLUMN_6: Well done!"
            Output: {5: "3.0", 6: "Well done!"}
        """
        updates = {}
        
        # Pattern: COLUMN_X: value (capture everything after colon until newline or end)
        pattern = r'COLUMN[_\s](\d+):\s*(.+?)(?:\n|$)'
        
        matches = re.finditer(pattern, response, re.IGNORECASE | re.MULTILINE)
        
        for match in matches:
            col_num = int(match.group(1))
            value = match.group(2).strip()
            
            # Only accept expected columns (prevents accidental writes)
            if col_num in expected_columns:
                updates[col_num] = value
        
        return updates
    
    def update_cell(self, row_idx: int, col_idx: int, value: str) -> bool:
        """
        Update a cell in the DataFrame.
        
        Args:
            row_idx: 0-based row index
            col_idx: 1-based column index
            value: Value to write
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.has_data():
            return False
        
        try:
            # Create column if it doesn't exist
            if col_idx > self.num_cols:
                # Add missing columns
                for new_col in range(self.num_cols + 1, col_idx + 1):
                    self.csv_data[new_col] = ""
                self.num_cols = col_idx
            
            # Update cell
            self.csv_data.at[row_idx, col_idx] = value
            return True
            
        except Exception as e:
            print(f"Error updating cell [{row_idx}, {col_idx}]: {e}")
            return False
    
    def save_csv(self, output_path: Optional[str] = None) -> bool:
        """
        Save the DataFrame back to CSV.
        
        Args:
            output_path: Optional custom output path. If None, overwrites original file.
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        if not self.has_data():
            return False
        
        try:
            # Use original path if no output specified
            save_path = output_path or self.csv_path
            
            # Restore original headers (first N columns) and add generic names for new columns
            restored_headers = []
            for col_idx in range(1, self.num_cols + 1):
                if col_idx - 1 < len(self.original_headers):
                    restored_headers.append(self.original_headers[col_idx - 1])
                else:
                    restored_headers.append(f"Column_{col_idx}")
            
            # Create a copy with original headers
            output_df = self.csv_data.copy()
            output_df.columns = restored_headers
            
            # Save
            output_df.to_csv(save_path, index=False)
            return True
            
        except Exception as e:
            print(f"Error saving CSV: {e}")
            return False
    
    def get_row_summary(self, row_idx: int, max_cols: int = 5) -> str:
        """
        Get a human-readable summary of a row for display.
        
        Args:
            row_idx: 0-based row index
            max_cols: Maximum columns to display (truncate if more)
            
        Returns:
            str: Formatted row summary
        """
        if not self.has_data():
            return "[No data loaded]"
        
        if row_idx < 0 or row_idx >= self.num_rows:
            return "[Invalid row index]"
        
        summary_parts = []
        display_cols = min(max_cols, self.num_cols)
        
        for col_idx in range(1, display_cols + 1):
            header = self.original_headers[col_idx - 1] if col_idx - 1 < len(self.original_headers) else f"Col{col_idx}"
            value = self._get_cell_value(row_idx, col_idx)
            
            # Truncate long values
            if len(value) > 30:
                value = value[:27] + "..."
            
            summary_parts.append(f"  C{col_idx} ({header}): {value}")
        
        if self.num_cols > max_cols:
            summary_parts.append(f"  ... and {self.num_cols - max_cols} more columns")
        
        return "\n".join(summary_parts)


# Utility functions

def parse_column_ref(ref: str) -> int:
    """
    Parse a column reference string to numeric index.
    
    Args:
        ref: Column reference (e.g., "C3", "3", "Question")
        
    Returns:
        int: 1-based column index
        
    Raises:
        ValueError: If reference is invalid
    """
    # Try direct numeric
    if ref.isdigit():
        return int(ref)
    
    # Try CX format
    if ref.upper().startswith('C') and ref[1:].isdigit():
        return int(ref[1:])
    
    raise ValueError(f"Invalid column reference: {ref}")


def parse_row_specification(spec: str, total_rows: int) -> List[int]:
    """
    Parse row specification string into list of row indices (0-based).
    
    Supported formats:
        {R1}      - Single row (1-indexed input → 0-indexed output)
        {R1-5}    - Range from row 1 to 5 inclusive
        {R1,3,5}  - Specific rows 1, 3, and 5
        {R5-}     - From row 5 to end
        {R-5}     - From start to row 5
        {R1-3,7,9-11} - Mixed ranges and singles
    
    Args:
        spec: Row specification string (e.g., "1-5", "1,3,5", "5-")
        total_rows: Total number of rows in CSV
        
    Returns:
        List[int]: List of 0-based row indices
        
    Raises:
        ValueError: If specification is invalid
    """
    rows = set()
    
    # Split by comma for multiple parts
    parts = spec.split(',')
    
    for part in parts:
        part = part.strip()
        
        if '-' in part:
            # Range specification
            range_parts = part.split('-', 1)
            
            if range_parts[0] == '':
                # {R-5} - from start to N
                start = 1
                end = int(range_parts[1])
            elif range_parts[1] == '':
                # {R5-} - from N to end
                start = int(range_parts[0])
                end = total_rows
            else:
                # {R5-10} - from N to M
                start = int(range_parts[0])
                end = int(range_parts[1])
            
            # Validate range
            if start < 1 or end > total_rows or start > end:
                raise ValueError(f"Invalid row range: {part} (total rows: {total_rows})")
            
            # Add all rows in range (convert to 0-based)
            for i in range(start - 1, end):
                rows.add(i)
        else:
            # Single row specification
            row_num = int(part)
            if row_num < 1 or row_num > total_rows:
                raise ValueError(f"Row {row_num} out of range (total rows: {total_rows})")
            rows.add(row_num - 1)  # Convert to 0-based
    
    return sorted(list(rows))


def format_cell_value(value: Any, max_length: int = 50) -> str:
    """
    Format a cell value for display.
    
    Args:
        value: Raw cell value
        max_length: Maximum display length
        
    Returns:
        str: Formatted value
    """
    if pd.isna(value):
        return "[Empty]"
    
    str_value = str(value).strip()
    
    if str_value == "":
        return "[Empty]"
    
    if len(str_value) > max_length:
        return str_value[:max_length - 3] + "..."
    
    return str_value

# ==========================================
# Tool Status Panel
# ==========================================



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