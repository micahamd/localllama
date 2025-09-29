"""
Agent Sequence Store Module

Handles persistent storage and retrieval of agent sequences.
Extends the patterns used in PromptManager for consistency.
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple


class AgentSequence:
    """Represents a saved agent sequence with metadata."""
    
    def __init__(self, title: str, agents: List[Dict[str, Any]], loop_limit: int = 0):
        """
        Initialize an agent sequence.
        
        Args:
            title: Sequence title/name
            agents: List of agent definitions
            loop_limit: Maximum allowed loops/branches (default: 0 = no loops)
        """
        self.title = title
        self.agents = agents
        self.loop_limit = loop_limit
        self.created_at = datetime.now().isoformat()
        self.last_updated = self.created_at
        self.version = "1.0"
    
    def update_agents(self, agents: List[Dict[str, Any]]) -> None:
        """Update the agent list and timestamp."""
        self.agents = agents
        self.last_updated = datetime.now().isoformat()
    
    def update_loop_limit(self, loop_limit: int) -> None:
        """Update the loop limit and timestamp."""
        self.loop_limit = loop_limit
        self.last_updated = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert sequence to dictionary for serialization."""
        return {
            "title": self.title,
            "agents": self.agents,
            "loop_limit": self.loop_limit,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "version": self.version,
            "agent_count": len(self.agents)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentSequence':
        """Create an AgentSequence instance from a dictionary."""
        sequence = cls(
            title=data["title"],
            agents=data.get("agents", []),
            loop_limit=data.get("loop_limit", 0)
        )
        sequence.created_at = data.get("created_at", sequence.created_at)
        sequence.last_updated = data.get("last_updated", sequence.last_updated)
        sequence.version = data.get("version", "1.0")
        return sequence


class AgentSequenceStore:
    """Manages saving, loading, and listing agent sequences."""
    
    def __init__(self, agents_dir: str = "agents"):
        """
        Initialize the agent sequence store.
        
        Args:
            agents_dir: Directory to store agent sequence files
        """
        self.agents_dir = agents_dir
        self.file_extension = ".agent.json"
        
        # Create agents directory if it doesn't exist
        if not os.path.exists(self.agents_dir):
            os.makedirs(self.agents_dir)
    
    def _sanitize_filename(self, title: str) -> str:
        """
        Sanitize a title for use as a filename.
        
        Args:
            title: Original title
            
        Returns:
            str: Sanitized filename (without extension)
        """
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', title)
        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip(' .')
        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        # Ensure it's not empty
        if not sanitized:
            sanitized = "untitled_sequence"
        
        return sanitized
    
    def _get_file_path(self, title: str) -> str:
        """Get the full file path for a given title."""
        safe_title = self._sanitize_filename(title)
        return os.path.join(self.agents_dir, f"{safe_title}{self.file_extension}")
    
    def save_agent_sequence(self, sequence: AgentSequence) -> bool:
        """
        Save an agent sequence to disk.
        
        Args:
            sequence: AgentSequence to save
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            file_path = self._get_file_path(sequence.title)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(sequence.to_dict(), f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Error saving agent sequence '{sequence.title}': {e}")
            return False
    
    def load_agent_sequence(self, title: str) -> Optional[AgentSequence]:
        """
        Load an agent sequence from disk.
        
        Args:
            title: Title of the sequence to load
            
        Returns:
            AgentSequence or None if not found or error
        """
        try:
            file_path = self._get_file_path(title)
            
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return AgentSequence.from_dict(data)
            
        except Exception as e:
            print(f"Error loading agent sequence '{title}': {e}")
            return None
    
    def list_agent_sequences(self) -> List[Tuple[str, Dict[str, Any]]]:
        """
        List all available agent sequences with metadata.
        
        Returns:
            List of tuples: (title, metadata_dict)
        """
        sequences = []
        
        try:
            if not os.path.exists(self.agents_dir):
                return sequences
            
            for filename in os.listdir(self.agents_dir):
                if filename.endswith(self.file_extension):
                    file_path = os.path.join(self.agents_dir, filename)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # Extract metadata
                        metadata = {
                            "title": data.get("title", "Unknown"),
                            "agent_count": data.get("agent_count", len(data.get("agents", []))),
                            "loop_limit": data.get("loop_limit", 0),
                            "created_at": data.get("created_at"),
                            "last_updated": data.get("last_updated"),
                            "version": data.get("version", "unknown"),
                            "file_size": os.path.getsize(file_path)
                        }
                        
                        sequences.append((data.get("title", filename), metadata))
                        
                    except Exception as e:
                        print(f"Error reading sequence file '{filename}': {e}")
                        continue
            
            # Sort by last_updated (most recent first)
            sequences.sort(key=lambda x: x[1].get("last_updated", ""), reverse=True)
            
        except Exception as e:
            print(f"Error listing agent sequences: {e}")
        
        return sequences
    
    def delete_agent_sequence(self, title: str) -> bool:
        """
        Delete an agent sequence from disk.
        
        Args:
            title: Title of the sequence to delete
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            file_path = self._get_file_path(title)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Error deleting agent sequence '{title}': {e}")
            return False
    
    def sequence_exists(self, title: str) -> bool:
        """
        Check if a sequence with the given title exists.
        
        Args:
            title: Title to check
            
        Returns:
            bool: True if sequence exists
        """
        file_path = self._get_file_path(title)
        return os.path.exists(file_path)
    
    def get_unique_title(self, base_title: str) -> str:
        """
        Get a unique title by appending numbers if necessary.
        
        Args:
            base_title: Base title to make unique
            
        Returns:
            str: Unique title
        """
        if not self.sequence_exists(base_title):
            return base_title
        
        counter = 1
        while True:
            new_title = f"{base_title} ({counter})"
            if not self.sequence_exists(new_title):
                return new_title
            counter += 1
