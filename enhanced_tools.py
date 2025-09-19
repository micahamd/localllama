"""
Enhanced tool implementations with async execution and error recovery.
Replaces the blocking tool operations in main.py with non-blocking alternatives.
"""

import asyncio
import subprocess
import sys
import os
import time
import hashlib
from typing import Optional, Dict, Any, List
import threading
from concurrent.futures import ThreadPoolExecutor
import requests
from markitdown import MarkItDown

from tools_manager import ToolsManager, ToolTask, ToolStatus
from error_handler import error_handler, safe_execute


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