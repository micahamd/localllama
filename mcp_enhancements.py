"""
Enhanced MCP (Memory Control Program) improvements.
This module provides enhanced memory management with semantic search, 
categorization, and intelligent memory lifecycle management.
"""

import numpy as np
import json
import time
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import re
from collections import defaultdict


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


class EnhancedMCPManager:
    """Enhanced MCP manager with semantic search and intelligent memory management."""
    
    def __init__(self, memory_dir: str = "memories", embedding_model=None):
        """Initialize enhanced MCP manager."""
        self.memory_dir = memory_dir
        self.embedding_model = embedding_model
        self.memories: Dict[str, EnhancedMemory] = {}
        self.memory_index = {}  # For fast searching
        self.category_index = defaultdict(list)
        self.tag_index = defaultdict(list)
        
        # Load existing memories
        self.load_memories()
        
    def add_memory(
        self, 
        content: str, 
        memory_type: MemoryType = MemoryType.NOTE,
        priority: MemoryPriority = MemoryPriority.NORMAL,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
        expires_in_days: Optional[int] = None
    ) -> str:
        """Add enhanced memory with full metadata."""
        memory_id = self._generate_memory_id(content)
        
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)
            
        memory = EnhancedMemory(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            priority=priority,
            tags=tags or [],
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=1,
            metadata=metadata or {},
            expires_at=expires_at
        )
        
        # Generate embedding if model available
        if self.embedding_model:
            memory.embedding = self._generate_embedding(content)
            
        # Store memory
        self.memories[memory_id] = memory
        self._update_indexes(memory)
        self._save_memory(memory)
        
        return memory_id
    
    def semantic_search(
        self, 
        query: str, 
        limit: int = 5,
        memory_type: Optional[MemoryType] = None,
        min_similarity: float = 0.7
    ) -> List[Tuple[EnhancedMemory, float]]:
        """Perform semantic search using embeddings."""
        if not self.embedding_model:
            # Fallback to text search
            return self.text_search(query, limit, memory_type)
            
        query_embedding = self._generate_embedding(query)
        similarities = []
        
        for memory in self.memories.values():
            if memory_type and memory.memory_type != memory_type:
                continue
                
            if self._is_expired(memory):
                continue
                
            if memory.embedding:
                similarity = self._cosine_similarity(query_embedding, memory.embedding)
                if similarity >= min_similarity:
                    similarities.append((memory, similarity))
        
        # Sort by similarity and access patterns
        similarities.sort(key=lambda x: (x[1], x[0].access_count, x[0].priority.value), reverse=True)
        return similarities[:limit]
    
    def smart_categorization(self, content: str) -> MemoryType:
        """Automatically categorize memory content."""
        content_lower = content.lower()
        
        # Code detection
        code_patterns = [
            r'def\s+\w+\(',
            r'class\s+\w+',
            r'function\s+\w+',
            r'import\s+\w+',
            r'<html|<div|<script',
            r'\{\s*[\"\'][^\"\']+[\"\']:\s*'  # JSON-like
        ]
        
        if any(re.search(pattern, content) for pattern in code_patterns):
            return MemoryType.CODE_SNIPPET
            
        # Task detection
        task_keywords = ['todo', 'task', 'reminder', 'deadline', 'due', 'schedule']
        if any(keyword in content_lower for keyword in task_keywords):
            return MemoryType.TASK
            
        # Reference detection
        if any(pattern in content_lower for pattern in ['reference', 'documentation', 'manual', 'guide']):
            return MemoryType.REFERENCE
            
        # Learning detection
        learning_keywords = ['learned', 'discovered', 'insight', 'understanding', 'concept']
        if any(keyword in content_lower for keyword in learning_keywords):
            return MemoryType.LEARNING
            
        return MemoryType.NOTE
    
    def auto_tag_generation(self, content: str) -> List[str]:
        """Generate tags automatically from content."""
        # Extract key terms (simple implementation)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
        
        # Common words to exclude
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 
            'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 
            'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy',
            'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'
        }
        
        # Count word frequency
        word_freq = defaultdict(int)
        for word in words:
            if word not in stop_words and len(word) > 3:
                word_freq[word] += 1
        
        # Get top words as tags
        tags = [word for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]]
        return tags
    
    def memory_lifecycle_management(self):
        """Manage memory lifecycle - archive, expire, prioritize."""
        now = datetime.now()
        archived_count = 0
        expired_count = 0
        
        for memory_id, memory in list(self.memories.items()):
            # Handle expired memories
            if self._is_expired(memory):
                self.delete_memory(memory_id)
                expired_count += 1
                continue
            
            # Archive rarely accessed old memories
            days_since_access = (now - memory.last_accessed).days
            if days_since_access > 90 and memory.access_count < 3:
                memory.priority = MemoryPriority.LOW
                archived_count += 1
            
            # Boost frequently accessed memories
            elif memory.access_count > 10:
                if memory.priority == MemoryPriority.NORMAL:
                    memory.priority = MemoryPriority.HIGH
                    
        return {"archived": archived_count, "expired": expired_count}
    
    def find_related_memories(self, memory_id: str, limit: int = 5) -> List[EnhancedMemory]:
        """Find memories related to the given memory."""
        if memory_id not in self.memories:
            return []
            
        source_memory = self.memories[memory_id]
        
        # Use semantic search if available
        if self.embedding_model and source_memory.embedding:
            similarities = []
            for other_id, other_memory in self.memories.items():
                if other_id == memory_id or not other_memory.embedding:
                    continue
                    
                similarity = self._cosine_similarity(source_memory.embedding, other_memory.embedding)
                if similarity > 0.6:  # Threshold for relatedness
                    similarities.append((other_memory, similarity))
            
            similarities.sort(key=lambda x: x[1], reverse=True)
            return [mem for mem, _ in similarities[:limit]]
        
        # Fallback to tag-based similarity
        related = []
        source_tags = set(source_memory.tags)
        
        for other_id, other_memory in self.memories.items():
            if other_id == memory_id:
                continue
                
            other_tags = set(other_memory.tags)
            overlap = len(source_tags.intersection(other_tags))
            
            if overlap > 0:
                related.append((other_memory, overlap))
        
        related.sort(key=lambda x: x[1], reverse=True)
        return [mem for mem, _ in related[:limit]]
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        stats = {
            "total_memories": len(self.memories),
            "by_type": defaultdict(int),
            "by_priority": defaultdict(int),
            "access_patterns": [],
            "expired_count": 0,
            "average_age_days": 0
        }
        
        total_age = 0
        now = datetime.now()
        
        for memory in self.memories.values():
            stats["by_type"][memory.memory_type.value] += 1
            stats["by_priority"][memory.priority.value] += 1
            
            if self._is_expired(memory):
                stats["expired_count"] += 1
                
            age_days = (now - memory.created_at).days
            total_age += age_days
        
        if self.memories:
            stats["average_age_days"] = total_age / len(self.memories)
            
        return dict(stats)
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text (placeholder - integrate with actual embedding model)."""
        # This would integrate with sentence transformers or similar
        # For now, return a dummy embedding
        return [0.0] * 384
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norms = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        
        if norms == 0:
            return 0.0
            
        return dot_product / norms
    
    def _generate_memory_id(self, content: str) -> str:
        """Generate unique memory ID."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        timestamp = str(int(time.time()))
        return f"mem_{timestamp}_{content_hash[:8]}"
    
    def _is_expired(self, memory: EnhancedMemory) -> bool:
        """Check if memory has expired."""
        if not memory.expires_at:
            return False
        return datetime.now() > memory.expires_at
    
    def _update_indexes(self, memory: EnhancedMemory):
        """Update search indexes."""
        self.category_index[memory.memory_type].append(memory.id)
        for tag in memory.tags:
            self.tag_index[tag].append(memory.id)
    
    def _save_memory(self, memory: EnhancedMemory):
        """Save memory to disk."""
        # Implementation for persistence
        pass
    
    def load_memories(self):
        """Load memories from disk."""
        # Implementation for loading
        pass


class EnhancedMCPUI:
    """Enhanced UI for the improved MCP system."""
    
    def __init__(self, parent, enhanced_mcp_manager, colors):
        """Initialize enhanced MCP UI."""
        self.parent = parent
        self.mcp_manager = enhanced_mcp_manager
        self.colors = colors
        
        # Create enhanced UI components
        self.create_enhanced_ui()
    
    def create_enhanced_ui(self):
        """Create the enhanced UI with filtering, categorization, and analytics."""
        # Main container
        self.main_frame = ttk.Frame(self.parent)
        
        # Create tabbed interface
        self.notebook = ttk.Notebook(self.main_frame)
        
        # Memory browser tab
        self.create_memory_browser_tab()
        
        # Analytics tab
        self.create_analytics_tab()
        
        # Settings tab
        self.create_settings_tab()
        
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
    def create_memory_browser_tab(self):
        """Create enhanced memory browser with filtering and categorization."""
        # This would contain:
        # - Category filters (dropdown)
        # - Priority filters
        # - Date range selectors
        # - Advanced search with semantic similarity
        # - Memory relationship visualization
        # - Bulk operations (tag, delete, export)
        pass
    
    def create_analytics_tab(self):
        """Create analytics dashboard for memory insights."""
        # This would show:
        # - Memory usage over time
        # - Most accessed memories
        # - Category distribution
        # - Tag clouds
        # - Access patterns
        # - Memory lifecycle status
        pass
    
    def create_settings_tab(self):
        """Create settings for memory management."""
        # This would include:
        # - Auto-categorization settings
        # - Memory expiration rules
        # - Embedding model selection
        # - Export/import options
        # - Cleanup policies
        pass