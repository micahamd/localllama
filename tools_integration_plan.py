"""
Integration patch for enhanced tools system.
This file contains the modifications needed to integrate the new tools system into main.py.
"""

# Add these imports to the top of main.py (after existing imports)
integration_imports = """
# Enhanced tools system imports
from tools_manager import ToolsManager, ToolTask, ToolStatus
from tool_status_panel import ToolStatusPanel
from enhanced_tools import (
    EnhancedWebSearchTool, 
    EnhancedFileTools, 
    EnhancedDependencyManager,
    with_retry,
    RetryConfig
)
"""

# Add this to the __init__ method of OllamaChat class (after line 418)
integration_init = """
        # Initialize enhanced tools system
        self.tools_manager = ToolsManager(max_concurrent_tools=3)
        self.tool_status_panel = None  # Will be created after UI is ready
        
        # Enhanced tool instances
        self.enhanced_web_search = EnhancedWebSearchTool(self.tools_manager)
        self.enhanced_file_tools = EnhancedFileTools(self.tools_manager)
        self.enhanced_dependency_manager = EnhancedDependencyManager(self.tools_manager)
        
        # Tool task tracking
        self.active_tool_tasks = {}  # Maps operation type to task_id
"""

# Add this to setup_theme method (after UI is created)
integration_ui_setup = """
        # Create tool status panel after UI is ready
        self.tool_status_panel = ToolStatusPanel(self.root, self.tools_manager)
        self.tool_status_panel.configure_styles(style)
        
        # Register tool completion callback
        self.tools_manager.register_completion_callback(self.on_tool_task_completed)
"""

# Replace the existing on_advanced_web_access_toggle method
replacement_web_toggle = """
    def on_advanced_web_access_toggle(self):
        \"\"\"Handle web search toggle with enhanced dependency management.\"\"\"
        advanced_web_access = self.advanced_web_access_var.get()
        self.settings.set("advanced_web_access", advanced_web_access)

        if advanced_web_access:
            # Check dependencies asynchronously
            self.check_web_search_dependencies()
        else:
            self.display_message("\\nAdvanced web search disabled.\\n", "status")
    
    def check_web_search_dependencies(self):
        \"\"\"Check and install web search dependencies if needed.\"\"\"
        # Check current status
        deps = self.enhanced_web_search._check_dependencies()
        
        missing_deps = []
        if not deps['crawl4ai']:
            missing_deps.append('crawl4ai')
        if not deps['playwright']:
            missing_deps.append('playwright')
        if not deps['playwright_browsers']:
            missing_deps.append('playwright browsers')
        
        if not missing_deps:
            self.display_message("\\nAdvanced web search enabled. All dependencies are available.\\n", "status")
            return
        
        # Ask user for permission to install
        import tkinter.messagebox as msgbox
        install_deps = msgbox.askyesno(
            "Install Dependencies",
            f"Advanced web search requires the following dependencies:\\n"
            f"{'\\n'.join(f'• {dep}' for dep in missing_deps)}\\n\\n"
            f"This may take several minutes. Install now?",
            default='yes'
        )
        
        if install_deps:
            self.display_message("\\nStarting dependency installation in background...\\n", "status")
            task_id = self.enhanced_web_search.install_dependencies_async(
                progress_callback=self.on_dependency_install_progress
            )
            self.active_tool_tasks['web_dependencies'] = task_id
        else:
            # Disable web search
            self.advanced_web_access_var.set(False)
            self.settings.set("advanced_web_access", False)
            self.display_message("\\nAdvanced web search disabled. Dependencies not installed.\\n", "status")
    
    def on_dependency_install_progress(self, progress: float, message: str):
        \"\"\"Handle dependency installation progress updates.\"\"\"
        self.display_message(f"\\r{message} ({progress:.1f}%)\\n", "status")
"""

# Replace the existing perform_advanced_web_search method
replacement_web_search = """
    def perform_advanced_web_search(self, query):
        \"\"\"Perform advanced web search using enhanced tools.\"\"\"
        try:
            # Submit search task
            task_id = self.enhanced_web_search.search_web_async(query, max_results=3)
            self.active_tool_tasks['web_search'] = task_id
            
            # Wait for result with timeout
            task = self.wait_for_tool_task(task_id, timeout=120.0)
            
            if task and task.status == ToolStatus.COMPLETED:
                return task.result
            elif task and task.status == ToolStatus.FAILED:
                raise Exception(task.error)
            elif task and task.status == ToolStatus.TIMEOUT:
                raise Exception("Web search timed out")
            else:
                raise Exception("Web search was cancelled or failed")
                
        except Exception as e:
            error_handler.handle_error(e, "Enhanced web search")
            return None
"""

# Replace the existing process_file_read_requests method
replacement_file_read = """
    def process_file_read_requests(self, user_input):
        \"\"\"Process file read requests using enhanced file tools.\"\"\"
        if not self.read_file_var.get():
            return user_input

        # Pattern 1: <<\"path\">> format (with quotes)
        pattern1 = r'<<\\\"([^\\\"]+)\\\">>'
        # Pattern 2: <<path>> format (without quotes)  
        pattern2 = r'<<([^>\\\"]+)>>'

        # Find all file read requests
        matches1 = re.findall(pattern1, user_input)
        matches2 = re.findall(pattern2, user_input)

        # Combine and deduplicate matches
        all_paths = list(set(matches1 + matches2))

        if not all_paths:
            return user_input

        self.display_message(f"\\n📖 Processing {len(all_paths)} file read request(s)...\\n", 'status')

        processed_input = user_input
        files_read = 0

        for path in all_paths:
            # Clean the path
            clean_path = path.strip().strip('\"').strip(\"'\")

            try:
                # Submit read task
                task_id = self.enhanced_file_tools.read_file_async(clean_path)
                
                # Wait for result
                task = self.wait_for_tool_task(task_id, timeout=60.0)
                
                if task and task.status == ToolStatus.COMPLETED:
                    file_content = task.result
                    files_read += 1

                    # Replace the file reference with the content
                    for pattern in [f'<<\"{path}\">>', f\"<<'{path}'>>\", f'<<{path}>>']:
                        if pattern in processed_input:
                            replacement = f\"\\n\\n--- Content from {clean_path} ---\\n{file_content}\\n--- End of {clean_path} ---\\n\\n\"
                            processed_input = processed_input.replace(pattern, replacement)
                            break

                    if self.truncate_file_display_var.get():
                        filename = os.path.basename(clean_path)
                        self.display_message(f\"{filename} read\\n\", 'status')
                    else:
                        self.display_message(f\"\\n✅ Successfully read '{clean_path}'\\n\", 'status')
                        preview = file_content[:100] + \"...\" if len(file_content) > 100 else file_content
                        self.display_message(f\"Preview: {preview}\\n\", 'status')
                        
                elif task and task.status == ToolStatus.FAILED:
                    self.display_message(f\"\\n❌ Failed to read '{clean_path}': {task.error}\\n\", 'error')
                else:
                    self.display_message(f\"\\n⚠️ Reading '{clean_path}' was cancelled or timed out\\n\", 'warning')
                    
            except Exception as e:
                error_msg = error_handler.handle_error(e, f\"Reading file {clean_path}\")
                self.display_message(f\"\\n❌ Error reading '{clean_path}': {error_msg}\\n\", 'error')

        if files_read > 0:
            self.display_message(f\"\\n🎉 Successfully read {files_read} file(s)!\\n\", 'status')

        return processed_input
"""

# Replace the existing write_file_safely method
replacement_file_write = """
    def write_file_safely(self, file_path, content):
        \"\"\"Write file using enhanced file tools.\"\"\"
        try:
            # Submit write task
            task_id = self.enhanced_file_tools.write_file_async(file_path, content)
            
            # Wait for result
            task = self.wait_for_tool_task(task_id, timeout=30.0)
            
            if task and task.status == ToolStatus.COMPLETED:
                return True, task.result
            elif task and task.status == ToolStatus.FAILED:
                return False, task.error
            else:
                return False, \"File write was cancelled or timed out\"
                
        except Exception as e:
            error_msg = error_handler.handle_error(e, f\"Writing file {file_path}\")
            return False, error_msg
"""

# Add new helper methods
helper_methods = """
    def wait_for_tool_task(self, task_id: str, timeout: float = 30.0) -> Optional[ToolTask]:
        \"\"\"Wait for a tool task to complete with timeout.\"\"\"
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            task = self.tools_manager.get_task_status(task_id)
            if task and not task.is_active:
                return task
            
            # Allow UI to update
            self.root.update()
            time.sleep(0.1)
        
        # Timeout - try to cancel the task
        self.tools_manager.cancel_task(task_id)
        return self.tools_manager.get_task_status(task_id)
    
    def on_tool_task_completed(self, task: ToolTask):
        \"\"\"Handle tool task completion.\"\"\"
        # Remove from active tasks
        for op_type, task_id in list(self.active_tool_tasks.items()):
            if task_id == task.id:
                del self.active_tool_tasks[op_type]
                break
        
        # Handle specific completion events
        if task.tool_name == \"Web Search\" and \"Installing dependencies\" in task.operation:
            if task.status == ToolStatus.COMPLETED:
                self.display_message(\"\\n✅ Web search dependencies installed successfully!\\n\", \"status\")
                self.display_message(\"Advanced web search is now ready to use.\\n\", \"status\")
            else:
                self.display_message(f\"\\n❌ Dependency installation failed: {task.error}\\n\", \"error\")
                self.advanced_web_access_var.set(False)
                self.settings.set(\"advanced_web_access\", False)
    
    def cancel_active_tool_operations(self):
        \"\"\"Cancel all active tool operations.\"\"\"
        for task_id in self.active_tool_tasks.values():
            self.tools_manager.cancel_task(task_id)
        self.active_tool_tasks.clear()
    
    def get_tool_status_summary(self) -> str:
        \"\"\"Get a summary of current tool operations.\"\"\"
        active_tasks = self.tools_manager.get_active_tasks()
        if not active_tasks:
            return \"No active tool operations\"
        
        summary = f\"{len(active_tasks)} active tool operation(s):\\n\"
        for task in active_tasks:
            summary += f\"• {task.tool_name}: {task.operation} ({task.progress:.0f}%)\\n\"
        
        return summary
"""

# Add cleanup to existing methods
cleanup_additions = """
# Add to the end of __init__ method (before setup_theme call):
        # Register cleanup on window close
        self.root.protocol(\"WM_DELETE_WINDOW\", self.on_closing)

# Add this new method:
    def on_closing(self):
        \"\"\"Handle application closing with cleanup.\"\"\"
        try:
            # Cancel any active tool operations
            self.cancel_active_tool_operations()
            
            # Shutdown tools manager
            if hasattr(self, 'tools_manager'):
                self.tools_manager.shutdown()
            
            # Save settings
            self.save_settings()
            
        except Exception as e:
            error_handler.handle_error(e, \"Application cleanup\")
        finally:
            self.root.destroy()
"""

print("📋 **DETAILED INTEGRATION PLAN FOR ENHANCED TOOLS SYSTEM**")
print("=" * 60)
print()
print("The integration plan above provides all necessary code modifications to safely")
print("integrate the enhanced tools system into the existing application.")
print()
print("🔧 **KEY IMPROVEMENTS PROVIDED:**")
print()
print("1. **Non-blocking Operations**: All tool operations now run in background threads")
print("2. **Visual Progress Tracking**: Tool status panel shows real-time progress")
print("3. **Cancellation Support**: Users can cancel long-running operations")
print("4. **Error Recovery**: Automatic retry with exponential backoff")
print("5. **Result Caching**: Avoid repeated expensive operations")
print("6. **Dependency Management**: Background installation with user consent")
print("7. **Timeout Handling**: Operations timeout gracefully with cleanup")
print("8. **Memory Management**: Automatic cleanup of completed tasks")
print()
print("🚀 **IMPLEMENTATION STEPS:**")
print()
print("1. Add the new files: tools_manager.py, tool_status_panel.py, enhanced_tools.py")
print("2. Add integration imports to main.py")
print("3. Initialize tools system in OllamaChat.__init__")
print("4. Replace existing tool methods with enhanced versions")
print("5. Add helper methods for task management")
print("6. Add cleanup handling for graceful shutdown")
print()
print("✅ **SAFETY MEASURES:**")
print()
print("- All changes are backwards compatible")
print("- Existing functionality is preserved")
print("- Error handling prevents crashes")
print("- User consent required for installations")
print("- Graceful degradation when tools unavailable")
print()
print("The enhanced tools system provides a robust, user-friendly foundation")
print("for all tool operations while maintaining the existing API.")