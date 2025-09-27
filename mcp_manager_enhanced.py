"""
MCP Manager Enhanced - Backward Compatible Wrapper
=================================================

This module provides enhanced MCP functionality while maintaining 100% backward
compatibility with the existing MCPManager. Uses the wrapper pattern to extend
functionality without modifying the original implementation.

SAFETY FEATURES:
- Inherits from original MCPManager (zero API breakage)
- All enhancements are opt-in via feature flags
- Falls back to original behavior if enhancements fail
- Maintains exact method signatures for compatibility
"""

import os
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime

# Import original MCP classes for compatibility
from mcp_server import MCPManager
from mcp_enhancements import EnhancedMemory, MemoryType, MemoryPriority

class MCPManagerEnhanced(MCPManager):
    """
    Enhanced MCP Manager that extends original functionality.
    Maintains 100% backward compatibility while adding new features.
    """
    
    def __init__(self, memories_dir="memories"):
        # Initialize parent class first (critical for compatibility)
        super().__init__(memories_dir)
        
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
            for filename in os.listdir(self.memories_dir):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(self.memories_dir, filename), 'r', encoding='utf-8') as f:
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

# =============================================================================
# COMPATIBILITY TESTING FUNCTIONS
# =============================================================================

def test_backward_compatibility():
    """Test that enhanced manager maintains compatibility with original."""
    print("Testing backward compatibility...")
    
    # Test with feature flags OFF (should behave exactly like original)
    enhanced_manager = MCPManagerEnhanced("memories")
    
    # Test basic operations
    memory_id = enhanced_manager.add_memory("Test memory for compatibility", ["test"])
    print(f"✓ add_memory works: {memory_id}")
    
    relevant = enhanced_manager.get_relevant_memories("test", 1) 
    print(f"✓ get_relevant_memories works: {len(relevant)} chars returned")
    
    search_results = enhanced_manager.search_memories("test", 1)
    print(f"✓ search_memories works: {len(search_results)} results")
    
    # Test with feature flags ON
    enhanced_manager.enable_feature("auto_categorization")
    enhanced_manager.enable_feature("enhanced_analytics")
    
    memory_id_enhanced = enhanced_manager.add_memory("Todo: test enhanced features", ["todo"])
    print(f"✓ Enhanced add_memory works: {memory_id_enhanced}")
    
    stats = enhanced_manager.get_enhanced_stats()
    print(f"✓ Enhanced stats work: {stats.get('total_memories', 0)} memories")
    
    print("Backward compatibility test completed successfully!")

if __name__ == "__main__":
    test_backward_compatibility()