import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import tkinter as tk

class Message:
    """Represents a single message in a conversation."""

    def __init__(self, role: str, content: str, timestamp: Optional[str] = None):
        self.role = role  # 'user', 'assistant', 'system', etc.
        self.content = content
        self.timestamp = timestamp or datetime.now().isoformat()

    def to_dict(self) -> Dict[str, str]:
        """Convert message to dictionary for serialization."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'Message':
        """Create a Message instance from a dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp")
        )


class Conversation:
    """Represents a full conversation with metadata."""

    def __init__(self, title: Optional[str] = None, model: Optional[str] = None):
        self.title = title or f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        self.model = model
        self.messages: List[Message] = []
        self.created_at = datetime.now().isoformat()
        self.last_updated = self.created_at

    def add_message(self, role: str, content: str) -> Message:
        """Add a new message to the conversation."""
        message = Message(role=role, content=content)
        self.messages.append(message)
        self.last_updated = datetime.now().isoformat()
        return message

    def to_dict(self) -> Dict[str, Any]:
        """Convert conversation to dictionary for serialization."""
        return {
            "title": self.title,
            "model": self.model,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "messages": [msg.to_dict() for msg in self.messages]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        """Create a Conversation instance from a dictionary."""
        conversation = cls(title=data["title"], model=data.get("model"))
        conversation.created_at = data.get("created_at", conversation.created_at)
        conversation.last_updated = data.get("last_updated", conversation.last_updated)
        conversation.messages = [Message.from_dict(msg) for msg in data.get("messages", [])]
        return conversation


class ConversationManager:
    """Manages saving, loading, and listing conversations."""

    def __init__(self, conversations_dir: str = "conversations"):
        self.conversations_dir = conversations_dir
        self.active_conversation = Conversation()

        # Create conversations directory if it doesn't exist
        if not os.path.exists(self.conversations_dir):
            os.makedirs(self.conversations_dir)

    def new_conversation(self, title: Optional[str] = None, model: Optional[str] = None) -> Conversation:
        """Create and set a new active conversation."""
        self.active_conversation = Conversation(title=title, model=model)
        return self.active_conversation

    def save_conversation(self) -> str:
        """Save the active conversation to a file."""
        try:
            if not self.active_conversation.messages:
                return "No messages to save"

            # Sanitize title for filename
            safe_title = "".join(c if c.isalnum() else "_" for c in self.active_conversation.title)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_title}_{timestamp}.json"
            filepath = os.path.join(self.conversations_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.active_conversation.to_dict(), f, indent=4, ensure_ascii=False)

            return f"Conversation saved as '{filename}'"
        except Exception as e:
            return f"Error saving conversation: {str(e)}"

    def load_conversation(self, filepath: str) -> Optional[Conversation]:
        """Load a conversation from a file and set it as active."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.active_conversation = Conversation.from_dict(data)
            return self.active_conversation
        except Exception as e:
            print(f"Error loading conversation: {str(e)}")
            return None

    def list_conversations(self) -> List[str]:
        """List all saved conversation files."""
        try:
            return [f for f in os.listdir(self.conversations_dir) if f.endswith('.json')]
        except Exception as e:
            print(f"Error listing conversations: {str(e)}")
            return []

    def add_message_to_active(self, role: str, content: str) -> None:
        """Add a message to the active conversation."""
        self.active_conversation.add_message(role=role, content=content)

    def render_conversation(self, text_widget: tk.Text, tag_config: Dict[str, Dict]) -> None:
        """Render the active conversation in a text widget with markdown support."""
        text_widget["state"] = "normal"
        text_widget.delete("1.0", tk.END)

        for message in self.active_conversation.messages:
            role_tag = message.role
            if role_tag not in ['user', 'assistant', 'system', 'error', 'status']:
                role_tag = 'status'  # Default tag

            # Add role label
            label_tag = f"{role_tag}_label" if hasattr(text_widget, 'tag_names') and f"{role_tag}_label" in text_widget.tag_names() else role_tag

            if role_tag == 'user':
                text_widget.insert(tk.END, "\n🧑 You: ", label_tag)
            elif role_tag == 'assistant':
                text_widget.insert(tk.END, "\n🤖 Assistant: ", label_tag)
            elif role_tag == 'system':
                text_widget.insert(tk.END, "\n⚙️ System: ", label_tag)
            elif role_tag == 'error':
                text_widget.insert(tk.END, "\n⚠️ Error: ", label_tag)
            elif role_tag == 'status':
                text_widget.insert(tk.END, "\n💬 Status: ", label_tag)

            # Check if we can use markdown rendering
            if role_tag == 'assistant' and hasattr(text_widget, 'display_markdown'):
                try:
                    # Use markdown rendering for assistant messages
                    text_widget.display_markdown(message.content)
                except Exception as e:
                    # Fallback to original method
                    self._render_with_code_blocks(text_widget, message.content, role_tag)
            elif role_tag == 'assistant':
                # Fallback for regular Text widget
                self._render_with_code_blocks(text_widget, message.content, role_tag)
            else:
                # For other message types, just insert with the tag
                text_widget.insert(tk.END, message.content, role_tag)

            # Add a newline after each message if it doesn't end with one
            if not message.content.endswith('\n'):
                text_widget.insert(tk.END, '\n', role_tag)

        text_widget["state"] = "disabled"
        text_widget.see(tk.END)

    def _render_with_code_blocks(self, text_widget: tk.Text, content: str, role_tag: str) -> None:
        """Helper method to render text with code blocks."""
        parts = content.split('```')
        for i, part in enumerate(parts):
            if i % 2 == 0:  # Regular text
                text_widget.insert(tk.END, part, role_tag)
            else:  # Code block
                text_widget.insert(tk.END, '\n', role_tag)  # Newline before code
                text_widget.insert(tk.END, part.strip(), 'code')  # Code with code tag
                text_widget.insert(tk.END, '\n', role_tag)  # Newline after code
