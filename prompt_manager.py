import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional


class Prompt:
    """Represents a saved prompt with title and content."""

    def __init__(self, title: str, content: str):
        self.title = title
        self.content = content
        self.created_at = datetime.now().isoformat()
        self.last_updated = self.created_at

    def update_content(self, content: str) -> None:
        """Update the prompt content."""
        self.content = content
        self.last_updated = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert prompt to dictionary for serialization."""
        return {
            "title": self.title,
            "content": self.content,
            "created_at": self.created_at,
            "last_updated": self.last_updated
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Prompt':
        """Create a Prompt instance from a dictionary."""
        prompt = cls(title=data["title"], content=data["content"])
        prompt.created_at = data.get("created_at", prompt.created_at)
        prompt.last_updated = data.get("last_updated", prompt.last_updated)
        return prompt


class PromptManager:
    """Manages saving, loading, and listing prompts."""

    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = prompts_dir
        self.prompts: Dict[str, Prompt] = {}  # Dictionary of title -> Prompt

        # Create prompts directory if it doesn't exist
        if not os.path.exists(self.prompts_dir):
            os.makedirs(self.prompts_dir)
            
        # Load existing prompts
        self.load_all_prompts()

    def load_all_prompts(self) -> None:
        """Load all saved prompts from the prompts directory."""
        try:
            prompt_files = [f for f in os.listdir(self.prompts_dir) if f.endswith('.json')]
            for filename in prompt_files:
                filepath = os.path.join(self.prompts_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    prompt = Prompt.from_dict(data)
                    self.prompts[prompt.title] = prompt
        except Exception as e:
            print(f"Error loading prompts: {str(e)}")

    def add_prompt(self, title: str, content: str) -> bool:
        """Add a new prompt or update an existing one."""
        try:
            # Create new prompt
            prompt = Prompt(title=title, content=content)
            
            # Add to dictionary
            self.prompts[title] = prompt
            
            # Save to file
            self._save_prompt(prompt)
            
            return True
        except Exception as e:
            print(f"Error adding prompt: {str(e)}")
            return False

    def update_prompt(self, title: str, content: str) -> bool:
        """Update an existing prompt."""
        try:
            if title not in self.prompts:
                return False
                
            # Update prompt
            self.prompts[title].update_content(content)
            
            # Save to file
            self._save_prompt(self.prompts[title])
            
            return True
        except Exception as e:
            print(f"Error updating prompt: {str(e)}")
            return False

    def delete_prompt(self, title: str) -> bool:
        """Delete a prompt."""
        try:
            if title not in self.prompts:
                return False
                
            # Remove from dictionary
            del self.prompts[title]
            
            # Remove file
            safe_title = self._sanitize_title(title)
            filepath = os.path.join(self.prompts_dir, f"{safe_title}.json")
            if os.path.exists(filepath):
                os.remove(filepath)
                
            return True
        except Exception as e:
            print(f"Error deleting prompt: {str(e)}")
            return False

    def get_prompt(self, title: str) -> Optional[Prompt]:
        """Get a prompt by title."""
        return self.prompts.get(title)

    def get_all_prompts(self) -> List[Prompt]:
        """Get all prompts."""
        return list(self.prompts.values())

    def get_prompt_titles(self) -> List[str]:
        """Get all prompt titles."""
        return list(self.prompts.keys())

    def _save_prompt(self, prompt: Prompt) -> None:
        """Save a prompt to a file."""
        safe_title = self._sanitize_title(prompt.title)
        filepath = os.path.join(self.prompts_dir, f"{safe_title}.json")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(prompt.to_dict(), f, indent=4, ensure_ascii=False)

    def _sanitize_title(self, title: str) -> str:
        """Sanitize title for filename."""
        return "".join(c if c.isalnum() else "_" for c in title)
