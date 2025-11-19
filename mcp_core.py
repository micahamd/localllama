"""
MCP Core - Consolidated Backend Module
=====================================

This module consolidates all MCP backend functionality from:
- mcp_server.py (Core MCPManager class)
- mcp_enhancements.py (Enhanced memory structures and classes)
- mcp_manager_enhanced.py (Enhanced manager wrapper)

Maintains 100% backward compatibility while reducing file count.
"""

import os
import json
import time
import threading
import asyncio
import numpy as np
import hashlib
import re
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict

import mcp
from mcp.server import FastMCP
from mcp.client.session import ClientSession
from error_handler import error_handler, safe_execute


# =============================================================================
# ENHANCED MEMORY STRUCTURES
# =============================================================================

class MemoryType(Enum):
    """Types of memories for categorization."""
    CONVERSATION = "conversation"
    DOCUMENT = "document" 
    CODE_SNIPPET = "code_snippet"
    REFERENCE = "reference"
    TASK = "task"
    NOTE = "note"
    LEARNING = "learning"


class MemoryPriority(Enum):
    """Memory priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class EnhancedMemory:
    """Enhanced memory structure with metadata and relationships."""
    id: str
    content: str
    memory_type: MemoryType
    priority: MemoryPriority
    tags: List[str]
    created_at: datetime
    last_accessed: datetime
    access_count: int
    embedding: Optional[List[float]] = None
    related_memories: List[str] = None
    metadata: Dict[str, Any] = None
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.related_memories is None:
            self.related_memories = []
        if self.metadata is None:
            self.metadata = {}


# =============================================================================
# BASE MCP MANAGER
# =============================================================================

class MCPManager:
    """Base MCP manager - handles core memory persistence and server functionality."""

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


# =============================================================================
# ENHANCED MCP MANAGER (extends base with advanced features)
# =============================================================================

class MCPManagerEnhanced(MCPManager):
    """
    Enhanced MCP Manager that extends original functionality.
    Maintains 100% backward compatibility while adding new features.
    """
    
    def __init__(self, memories_dir="memories"):
        # Initialize parent class first (critical for compatibility)
        super().__init__(memory_dir=memories_dir)
        
        # Enhanced features (all optional)
        self.feature_flags = {
            "semantic_search": False,
            "auto_categorization": False, 
            "memory_relationships": False,
            "lifecycle_management": False,
            "enhanced_analytics": False
        }
        
        # Enhanced data cache (lazy loaded)
        self._enhanced_cache = {}
        self._embeddings_cache = {}
        self._relationships_cache = {}
        
        # Statistics tracking (non-intrusive)
        self.stats = {
            "total_memories": 0,
            "access_counts": {},
            "search_history": [],
            "last_cleanup": None
        }
    
    # ==========================================================================
    # BACKWARD COMPATIBLE API (Exact Same Signatures)
    # ==========================================================================
    
    def add_memory(self, content: str, tags: List[str] = None) -> Optional[str]:
        """
        Enhanced add_memory that maintains exact compatibility.
        
        SAFETY: Falls back to parent method if enhancement fails.
        """
        try:
            # Try enhanced functionality first
            if self.feature_flags.get("auto_categorization", False):
                return self._add_memory_enhanced(content, tags)
            else:
                # Use original implementation
                return super().add_memory(content, tags)
                
        except Exception as e:
            # SAFETY: Always fall back to original on any error
            print(f"Enhanced add_memory failed, using original: {e}")
            return super().add_memory(content, tags)
    
    def get_relevant_memories(self, query: str, limit: int = 3) -> str:
        """
        Enhanced memory retrieval with semantic search option.
        
        SAFETY: Falls back to parent method if enhancement fails.
        """
        try:
            # Try semantic search if enabled
            if self.feature_flags.get("semantic_search", False):
                return self._get_relevant_memories_semantic(query, limit)
            else:
                # Use original text-based search
                return super().get_relevant_memories(query, limit)
                
        except Exception as e:
            # SAFETY: Always fall back to original on any error
            print(f"Enhanced search failed, using original: {e}")
            return super().get_relevant_memories(query, limit)
    
    def search_memories(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Enhanced search with filtering and ranking options.
        
        SAFETY: Falls back to parent method if enhancement fails.
        """
        try:
            # Try enhanced search if enabled
            if self.feature_flags.get("semantic_search", False):
                return self._search_memories_enhanced(query, limit)
            else:
                # Use original implementation
                return super().search_memories(query, limit)
                
        except Exception as e:
            # SAFETY: Always fall back to original on any error
            print(f"Enhanced search failed, using original: {e}")
            return super().search_memories(query, limit)
    
    # ==========================================================================
    # ENHANCED FUNCTIONALITY (New Features)
    # ==========================================================================
    
    def _add_memory_enhanced(self, content: str, tags: List[str] = None) -> Optional[str]:
        """Enhanced add_memory with auto-categorization and relationships."""
        
        # Generate memory ID
        memory_id = str(int(time.time() * 1000))
        
        # Create enhanced memory structure
        enhanced_memory = EnhancedMemory(
            id=memory_id,
            content=content,
            memory_type=self._auto_categorize(content) if self.feature_flags.get("auto_categorization") else MemoryType.NOTE,
            priority=MemoryPriority.NORMAL,
            tags=tags or [],
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=1,
            embedding=None,  # Will be computed lazily
            related_memories=[],
            metadata={"source": "user_input", "enhanced": True},
            expires_at=None
        )
        
        # Convert to original format for storage compatibility
        memory_data = {
            "content": enhanced_memory.content,
            "tags": enhanced_memory.tags,
            "created_at": enhanced_memory.created_at.timestamp(),
            "updated_at": enhanced_memory.last_accessed.timestamp(),
            # Enhanced fields (optional)
            "memory_type": enhanced_memory.memory_type.value,
            "priority": enhanced_memory.priority.value,
            "access_count": enhanced_memory.access_count,
            "last_accessed": enhanced_memory.last_accessed.timestamp(),
            "metadata": enhanced_memory.metadata,
            "expires_at": enhanced_memory.expires_at.timestamp() if enhanced_memory.expires_at else None
        }
        
        # Use original storage mechanism for compatibility
        memory_path = os.path.join(self.memory_dir, f"{memory_id}.json")
        
        try:
            with open(memory_path, 'w', encoding='utf-8') as f:
                json.dump(memory_data, f, indent=2, ensure_ascii=False)
            
            # Update caches
            self._enhanced_cache[memory_id] = enhanced_memory
            self.stats["total_memories"] += 1
            
            # Find relationships in background (non-blocking)
            if self.feature_flags.get("memory_relationships"):
                self._update_relationships_async(memory_id, content)
            
            return memory_id
            
        except Exception as e:
            print(f"Enhanced storage failed: {e}")
            # Fall back to original method
            return super().add_memory(content, tags)
    
    def _get_relevant_memories_semantic(self, query: str, limit: int = 3) -> str:
        """Enhanced semantic search for relevant memories."""
        
        # For now, fall back to original until semantic search is implemented
        # This allows gradual feature rollout
        return super().get_relevant_memories(query, limit)
    
    def _search_memories_enhanced(self, query: str, limit: int = 5) -> List[Dict]:
        """Enhanced search with better ranking and filtering."""
        
        # Get original results
        original_results = super().search_memories(query, limit)
        
        # Add enhanced fields if available
        enhanced_results = []
        for memory in original_results:
            memory_id = None
            # Try to find memory ID from file system
            for filename in os.listdir(self.memory_dir):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(self.memory_dir, filename), 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if data.get('content') == memory.get('content'):
                                memory_id = filename[:-5]  # Remove .json
                                break
                    except:
                        continue
            
            # Add enhanced fields if available
            enhanced_memory = dict(memory)
            enhanced_memory['memory_type'] = memory.get('memory_type', 'note')
            enhanced_memory['priority'] = memory.get('priority', 2)
            enhanced_memory['access_count'] = memory.get('access_count', 1)
            enhanced_memory['enhanced'] = True
            
            enhanced_results.append(enhanced_memory)
        
        return enhanced_results
    
    # ==========================================================================
    # UTILITY METHODS (Private)
    # ==========================================================================
    
    def _auto_categorize(self, content: str) -> MemoryType:
        """Auto-categorize memory based on content (simple rule-based for now)."""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['todo', 'task', 'reminder', 'do:']):
            return MemoryType.TASK
        elif any(word in content_lower for word in ['idea', 'brainstorm', 'concept', 'thought']):
            return MemoryType.NOTE  # Use NOTE instead of IDEA
        elif any(word in content_lower for word in ['fact', 'info', 'data', 'research']):
            return MemoryType.REFERENCE
        elif any(word in content_lower for word in ['meeting', 'call', 'discussion']):
            return MemoryType.NOTE  # Use NOTE instead of MEETING
        else:
            return MemoryType.NOTE
    
    def _update_relationships_async(self, memory_id: str, content: str):
        """Update memory relationships in background (placeholder for now)."""
        # Placeholder for relationship discovery
        # Will be implemented in later phase
        pass
    
    def _migrate_memory_format(self, memory_data: Dict) -> Dict:
        """Migrate old format to new format (backward compatible)."""
        # If memory already has enhanced fields, return as-is
        if 'memory_type' in memory_data:
            return memory_data
        
        # Add enhanced fields with sensible defaults
        enhanced_data = dict(memory_data)
        enhanced_data.update({
            'memory_type': 'note',
            'priority': 2,  # NORMAL
            'access_count': enhanced_data.get('access_count', 1),
            'last_accessed': enhanced_data.get('last_accessed', enhanced_data.get('created_at')),
            'metadata': enhanced_data.get('metadata', {}),
            'expires_at': None
        })
        
        return enhanced_data
    
    # ==========================================================================
    # FEATURE MANAGEMENT
    # ==========================================================================
    
    def enable_feature(self, feature_name: str) -> bool:
        """Safely enable an enhanced feature."""
        if feature_name in self.feature_flags:
            self.feature_flags[feature_name] = True
            print(f"Enhanced feature '{feature_name}' enabled")
            return True
        else:
            print(f"Unknown feature: {feature_name}")
            return False
    
    def disable_feature(self, feature_name: str) -> bool:
        """Safely disable an enhanced feature."""
        if feature_name in self.feature_flags:
            self.feature_flags[feature_name] = False
            print(f"Enhanced feature '{feature_name}' disabled")
            return True
        else:
            print(f"Unknown feature: {feature_name}")
            return False
    
    def get_feature_status(self) -> Dict[str, bool]:
        """Get current status of all enhanced features."""
        return dict(self.feature_flags)
    
    def get_enhanced_stats(self) -> Dict[str, Any]:
        """Get enhanced statistics and analytics."""
        try:
            # Count current memories (use self.memory_dir from parent class)
            memory_count = len([f for f in os.listdir(self.memory_dir) if f.endswith('.json')])
            
            # Update stats
            self.stats.update({
                "total_memories": memory_count,
                "enhanced_features_active": sum(self.feature_flags.values()),
                "last_stats_update": time.time()
            })
            
            return dict(self.stats)
            
        except Exception as e:
            print(f"Stats calculation failed: {e}")
            return {"error": str(e)}
