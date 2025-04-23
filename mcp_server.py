"""
MCP (Memory Control Program) Server for the chatbot application.
This module provides memory persistence and knowledge base functionality.
"""

import os
import json
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
import threading
import asyncio
import mcp
from mcp.server import FastMCP
from mcp.client.session import ClientSession
from error_handler import error_handler, safe_execute

class MCPManager:
    """Manages the MCP server and client connections for the chatbot."""

    def __init__(self, host="127.0.0.1", port=8000, memory_dir="memories"):
        """Initialize the MCP manager.

        Args:
            host: The host to run the MCP server on
            port: The port to run the MCP server on
            memory_dir: Directory to store memories
        """
        self.host = host
        self.port = port
        self.memory_dir = memory_dir
        self.server_url = f"http://{host}:{port}"
        self.server = None
        self.client = None
        self.server_thread = None
        self.is_running = False
        self.memories = {}

        # Create memory directory if it doesn't exist
        os.makedirs(memory_dir, exist_ok=True)

        # Load existing memories
        self.load_memories()

    def load_memories(self):
        """Load existing memories from the memory directory."""
        try:
            memory_files = [f for f in os.listdir(self.memory_dir) if f.endswith('.json')]
            for file in memory_files:
                with open(os.path.join(self.memory_dir, file), 'r') as f:
                    memory_data = json.load(f)
                    memory_id = os.path.splitext(file)[0]
                    self.memories[memory_id] = memory_data
            print(f"Loaded {len(self.memories)} memories from {self.memory_dir}")
        except Exception as e:
            error_msg = error_handler.handle_error(e, "Loading memories")
            print(f"Error loading memories: {error_msg}")

    def start_server(self):
        """Start the MCP server in a separate thread."""
        if self.is_running:
            print("MCP server is already running")
            return

        try:
            # Define the async server start function
            async def run_server():
                # Create a FastMCP server
                self.server = FastMCP(name="Memory Control Program")

                # Add memory-related tools
                @self.server.tool("add_memory")
                async def add_memory(content: str, tags: Optional[List[str]] = None) -> str:
                    """Add a new memory to the knowledge base."""
                    memory_id = self.add_memory(content, tags or [])
                    return f"Memory added with ID: {memory_id}"

                @self.server.tool("search_memories")
                async def search_memories(query: str, limit: int = 5) -> List[Dict]:
                    """Search memories by content."""
                    return self.search_memories(query, limit)

                @self.server.tool("get_memory")
                async def get_memory(memory_id: str) -> Optional[Dict]:
                    """Get a memory by ID."""
                    return self.get_memory(memory_id)

                # Run the server
                await self.server.run_sse_async(host=self.host, port=self.port)

            # Run the server in a separate thread
            def server_thread_func():
                asyncio.run(run_server())

            self.server_thread = threading.Thread(target=server_thread_func, daemon=True)
            self.server_thread.start()

            # Wait a moment for the server to start
            time.sleep(1)
            self.is_running = True
            print(f"MCP server started at {self.server_url}")

            # Initialize the client
            self.init_client()

            return True
        except Exception as e:
            error_msg = error_handler.handle_error(e, "Starting MCP server")
            print(f"Error starting MCP server: {error_msg}")
            return False

    def init_client(self):
        """Initialize the MCP client."""
        try:
            # For now, we'll just use the server directly
            # In a real implementation, we would create a proper client connection
            self.client = None
            print("MCP client initialized (using server directly)")
            return True
        except Exception as e:
            error_msg = error_handler.handle_error(e, "Initializing MCP client")
            print(f"Error initializing MCP client: {error_msg}")
            return False

    def stop_server(self):
        """Stop the MCP server."""
        if not self.is_running:
            print("MCP server is not running")
            return

        try:
            # Just terminate the thread - FastMCP doesn't have a clean shutdown method
            if self.server_thread and self.server_thread.is_alive():
                # We can't cleanly stop the server, so we'll just set the flag
                self.is_running = False
                print("MCP server stopping (may take a moment to fully terminate)")

            self.server = None
            self.client = None
            print("MCP server stopped")
            return True
        except Exception as e:
            error_msg = error_handler.handle_error(e, "Stopping MCP server")
            print(f"Error stopping MCP server: {error_msg}")
            return False

    def add_memory(self, content: str, tags: List[str] = None) -> Optional[str]:
        """Add a new memory to the MCP server.

        Args:
            content: The content of the memory
            tags: Optional list of tags for the memory

        Returns:
            The ID of the created memory or None if failed
        """
        if not self.is_running:
            print("MCP server is not running")
            return None

        try:
            # Create a unique ID for the memory
            memory_id = f"memory_{int(time.time())}"

            # Create memory data
            memory_data = {
                "content": content,
                "tags": tags or [],
                "created_at": time.time(),
                "updated_at": time.time()
            }

            # Save memory to file
            with open(os.path.join(self.memory_dir, f"{memory_id}.json"), 'w') as f:
                json.dump(memory_data, f, indent=2)

            # Add to in-memory cache
            self.memories[memory_id] = memory_data

            # We're not using the MCP client for memory operations
            # Instead, we're just storing them locally

            print(f"Memory added with ID: {memory_id}")
            return memory_id
        except Exception as e:
            error_msg = error_handler.handle_error(e, "Adding memory")
            print(f"Error adding memory: {error_msg}")
            return None

    def get_memory(self, memory_id: str) -> Optional[Dict]:
        """Get a memory by ID.

        Args:
            memory_id: The ID of the memory to retrieve

        Returns:
            The memory data or None if not found
        """
        # First check in-memory cache
        if memory_id in self.memories:
            return self.memories[memory_id]

        # Then check file system
        try:
            memory_path = os.path.join(self.memory_dir, f"{memory_id}.json")
            if os.path.exists(memory_path):
                with open(memory_path, 'r') as f:
                    memory_data = json.load(f)
                    # Update cache
                    self.memories[memory_id] = memory_data
                    return memory_data
        except Exception as e:
            error_msg = error_handler.handle_error(e, "Getting memory")
            print(f"Error getting memory: {error_msg}")

        return None

    def search_memories(self, query: str, limit: int = 5) -> List[Dict]:
        """Search memories by content.

        Args:
            query: The search query
            limit: Maximum number of results to return

        Returns:
            List of matching memories
        """
        if not self.is_running:
            print("MCP server is not running")
            return []

        try:
            # For now, implement a simple search in the local memories
            # In the future, this could use the MCP server's search capabilities
            results = []
            for memory_id, memory_data in self.memories.items():
                content = memory_data.get("content", "")
                if query.lower() in content.lower():
                    results.append({
                        "id": memory_id,
                        "content": content,
                        "tags": memory_data.get("tags", []),
                        "created_at": memory_data.get("created_at")
                    })
                    if len(results) >= limit:
                        break

            return results
        except Exception as e:
            error_msg = error_handler.handle_error(e, "Searching memories")
            print(f"Error searching memories: {error_msg}")
            return []

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID.

        Args:
            memory_id: The ID of the memory to delete

        Returns:
            True if successful, False otherwise
        """
        if not memory_id in self.memories:
            print(f"Memory {memory_id} not found")
            return False

        try:
            # Remove from in-memory cache
            if memory_id in self.memories:
                del self.memories[memory_id]

            # Remove from file system
            memory_path = os.path.join(self.memory_dir, f"{memory_id}.json")
            if os.path.exists(memory_path):
                os.remove(memory_path)

            # We're not using the MCP client for memory operations
            # Instead, we're just removing them locally

            print(f"Memory {memory_id} deleted")
            return True
        except Exception as e:
            error_msg = error_handler.handle_error(e, "Deleting memory")
            print(f"Error deleting memory: {error_msg}")
            return False

    def get_all_memories(self) -> List[Dict]:
        """Get all memories.

        Returns:
            List of all memories
        """
        try:
            results = []
            for memory_id, memory_data in self.memories.items():
                results.append({
                    "id": memory_id,
                    "content": memory_data.get("content", ""),
                    "tags": memory_data.get("tags", []),
                    "created_at": memory_data.get("created_at")
                })

            # Sort by creation time (newest first)
            results.sort(key=lambda x: x.get("created_at", 0), reverse=True)

            return results
        except Exception as e:
            error_msg = error_handler.handle_error(e, "Getting all memories")
            print(f"Error getting all memories: {error_msg}")
            return []

    def update_memory(self, memory_id: str, content: str = None, tags: List[str] = None) -> bool:
        """Update a memory by ID.

        Args:
            memory_id: The ID of the memory to update
            content: New content (or None to keep existing)
            tags: New tags (or None to keep existing)

        Returns:
            True if successful, False otherwise
        """
        if not memory_id in self.memories:
            print(f"Memory {memory_id} not found")
            return False

        try:
            # Get existing memory
            memory_data = self.memories[memory_id]

            # Update fields
            if content is not None:
                memory_data["content"] = content

            if tags is not None:
                memory_data["tags"] = tags

            memory_data["updated_at"] = time.time()

            # Save to file
            with open(os.path.join(self.memory_dir, f"{memory_id}.json"), 'w') as f:
                json.dump(memory_data, f, indent=2)

            # Update in-memory cache
            self.memories[memory_id] = memory_data

            # We're not using the MCP client for memory operations
            # Instead, we're just updating them locally

            print(f"Memory {memory_id} updated")
            return True
        except Exception as e:
            error_msg = error_handler.handle_error(e, "Updating memory")
            print(f"Error updating memory: {error_msg}")
            return False

    def get_relevant_memories(self, query: str, limit: int = 3) -> str:
        """Get memories relevant to a query, formatted as a string.

        Args:
            query: The query to find relevant memories for
            limit: Maximum number of memories to return

        Returns:
            Formatted string of relevant memories
        """
        if not self.is_running:
            return "Memory system is not active."

        try:
            # Search for relevant memories
            memories = self.search_memories(query, limit=limit)

            if not memories:
                return "No relevant memories found."

            # Format the memories as a string
            result = "Relevant memories:\n\n"
            for i, memory in enumerate(memories, 1):
                result += f"{i}. {memory['content']}\n\n"

            return result
        except Exception as e:
            error_msg = error_handler.handle_error(e, "Getting relevant memories")
            print(f"Error getting relevant memories: {error_msg}")
            return f"Error retrieving memories: {error_msg}"
