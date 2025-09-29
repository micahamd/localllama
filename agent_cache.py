"""
Agent Cache Module

Handles temporary caching of agent definitions during staging sessions.
Uses deterministic file paths in system temp directory for persistence
across application restarts within the same session.
"""

import json
import os
import tempfile
from typing import List, Dict, Any, Optional
from datetime import datetime


class AgentCache:
    """Manages temporary caching of agent definitions during staging."""
    
    CACHE_FILENAME = "agent_sequence_cache.json"
    
    def __init__(self):
        """Initialize the agent cache."""
        self.cache_file_path = os.path.join(tempfile.gettempdir(), self.CACHE_FILENAME)
    
    def save_agents_to_cache(self, agents: List[Dict[str, Any]]) -> bool:
        """
        Save agent list to temporary cache.
        
        Args:
            agents: List of agent definition dictionaries
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            cache_data = {
                "agents": agents,
                "cached_at": datetime.now().isoformat(),
                "version": "1.0"
            }
            
            with open(self.cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Error saving agents to cache: {e}")
            return False
    
    def load_cached_agents(self) -> List[Dict[str, Any]]:
        """
        Load agent list from temporary cache.
        
        Returns:
            List[Dict]: List of agent definitions, empty list if no cache or error
        """
        try:
            if not os.path.exists(self.cache_file_path):
                return []
            
            with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Validate cache structure
            if not isinstance(cache_data, dict) or "agents" not in cache_data:
                return []
            
            agents = cache_data.get("agents", [])
            
            # Validate agents structure
            if not isinstance(agents, list):
                return []
            
            return agents
            
        except Exception as e:
            print(f"Error loading cached agents: {e}")
            return []
    
    def clear_agent_cache(self) -> bool:
        """
        Clear the temporary agent cache.
        
        Returns:
            bool: True if cleared successfully, False otherwise
        """
        try:
            if os.path.exists(self.cache_file_path):
                os.remove(self.cache_file_path)
            return True
            
        except Exception as e:
            print(f"Error clearing agent cache: {e}")
            return False
    
    def has_cached_agents(self) -> bool:
        """
        Check if there are cached agents available.
        
        Returns:
            bool: True if cache exists and contains agents
        """
        agents = self.load_cached_agents()
        return len(agents) > 0
    
    def get_cache_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the current cache.
        
        Returns:
            Dict with cache metadata or None if no cache
        """
        try:
            if not os.path.exists(self.cache_file_path):
                return None
            
            with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            return {
                "agent_count": len(cache_data.get("agents", [])),
                "cached_at": cache_data.get("cached_at"),
                "version": cache_data.get("version", "unknown"),
                "file_size": os.path.getsize(self.cache_file_path)
            }
            
        except Exception as e:
            print(f"Error getting cache info: {e}")
            return None


def create_agent_definition(
    title: str,
    model: str,
    developer: str,
    system: str,
    messages: List[Dict[str, str]],
    parameters: Dict[str, Any],
    tools: Dict[str, bool],
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized agent definition dictionary.
    
    Args:
        title: Agent title/name
        model: Model name (e.g., "llama3:70b")
        developer: Provider name (e.g., "ollama", "google", "deepseek", "anthropic")
        system: System prompt text
        messages: List of message dictionaries
        parameters: Model parameters (temperature, top_p, etc.)
        tools: Tool enablement flags
        metadata: Additional metadata
        
    Returns:
        Dict: Standardized agent definition
    """
    if metadata is None:
        metadata = {}
    
    # Ensure required metadata fields
    metadata.update({
        "timestamp": datetime.now().isoformat(),
        "references": metadata.get("references", [])
    })
    
    return {
        "title": title,
        "model": model,
        "developer": developer,
        "system": system,
        "messages": messages,
        "parameters": parameters,
        "tools": tools,
        "metadata": metadata
    }


def validate_agent_definition(agent: Dict[str, Any]) -> bool:
    """
    Validate that an agent definition has all required fields.
    
    Args:
        agent: Agent definition dictionary
        
    Returns:
        bool: True if valid, False otherwise
    """
    required_fields = ["title", "model", "developer", "system", "messages", "parameters", "tools", "metadata"]
    
    if not isinstance(agent, dict):
        return False
    
    for field in required_fields:
        if field not in agent:
            return False
    
    # Validate field types
    if not isinstance(agent["title"], str):
        return False
    if not isinstance(agent["model"], str):
        return False
    if not isinstance(agent["developer"], str):
        return False
    if not isinstance(agent["system"], str):
        return False
    if not isinstance(agent["messages"], list):
        return False
    if not isinstance(agent["parameters"], dict):
        return False
    if not isinstance(agent["tools"], dict):
        return False
    if not isinstance(agent["metadata"], dict):
        return False
    
    return True
