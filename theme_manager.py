"""
Theme Manager for Chat Application
Centralized theme management with customizable color schemes.
"""

import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ColorScheme:
    """Represents a complete color scheme for the application."""
    # Main UI colors
    bg_color: str = "#0F0115"           # Rich dark background
    fg_color: str = "#CBABE2"           # Soft purple-white text
    accent_color: str = "#266A02"       # Vibrant accent
    secondary_bg: str = "#200202"       # Slightly lighter background
    tertiary_bg: str = "#1B0202"        # Darker background for depth
    subtle_accent: str = "#336648"      # Dark green accent
    success_color: str = "#00FD04"      # Vibrant green for success
    error_color: str = "#E5002A"        # Bright red for errors
    warning_color: str = "#EE940D"      # Rich amber for warnings
    border_color: str = "#250606"       # Subtle border color
    highlight_color: str = "#98A1C3"    # Light highlight
    cursor_color: str = "#FFD8D7"       # Light cursor
    muted_text: str = "#825F5F"         # Muted text
    
    # Code/Markdown specific colors
    code_bg: str = "#0D0E14"            # Dark code background
    code_fg: str = "#E0E0E0"            # Light text for code
    link_color: str = "#7AA2F7"         # Blue links
    quote_border: str = "#414868"       # Subtle border
    hr_color: str = "#414868"           # Horizontal rule
    header_bg: str = "#24283B"          # Header background
    
    # Markdown syntax highlighting
    markdown_h1: str = "#BB9AF7"        # Purple for H1
    markdown_h2: str = "#2AC3DE"        # Cyan for H2
    markdown_h3: str = "#7AA2F7"        # Blue for H3
    markdown_h4: str = "#9ECE6A"        # Green for H4
    markdown_bold: str = None           # Use fg_color if None
    markdown_italic: str = None         # Use fg_color if None
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'ColorScheme':
        """Create ColorScheme from dictionary."""
        return cls(**data)


class ThemeManager:
    """Manages application themes and color schemes."""
    
    # Built-in themes
    BUILTIN_THEMES = {
        "Default (Cyberpunk)": ColorScheme(),
        
        "Tokyo Night": ColorScheme(
            bg_color="#1A1B26",
            fg_color="#C0CAF5",
            accent_color="#7AA2F7",
            secondary_bg="#24283B",
            tertiary_bg="#1F2335",
            subtle_accent="#BB9AF7",
            success_color="#9ECE6A",
            error_color="#F7768E",
            warning_color="#E0AF68",
            border_color="#414868",
            highlight_color="#2AC3DE",
            cursor_color="#C0CAF5",
            muted_text="#565F89",
            code_bg="#0D0E14",
            code_fg="#E0E0E0",
            link_color="#7AA2F7",
            quote_border="#414868",
            hr_color="#414868",
            header_bg="#24283B",
            markdown_h1="#BB9AF7",
            markdown_h2="#2AC3DE",
            markdown_h3="#7AA2F7",
            markdown_h4="#9ECE6A"
        ),
        
        "Dracula": ColorScheme(
            bg_color="#282A36",
            fg_color="#F8F8F2",
            accent_color="#BD93F9",
            secondary_bg="#343746",
            tertiary_bg="#21222C",
            subtle_accent="#6272A4",
            success_color="#50FA7B",
            error_color="#FF5555",
            warning_color="#FFB86C",
            border_color="#44475A",
            highlight_color="#8BE9FD",
            cursor_color="#F8F8F2",
            muted_text="#6272A4",
            code_bg="#1E1F29",
            code_fg="#F8F8F2",
            link_color="#8BE9FD",
            quote_border="#44475A",
            hr_color="#44475A",
            header_bg="#343746",
            markdown_h1="#FF79C6",
            markdown_h2="#8BE9FD",
            markdown_h3="#BD93F9",
            markdown_h4="#50FA7B"
        ),
        
        "Monokai": ColorScheme(
            bg_color="#272822",
            fg_color="#F8F8F2",
            accent_color="#66D9EF",
            secondary_bg="#3E3D32",
            tertiary_bg="#1E1F1C",
            subtle_accent="#75715E",
            success_color="#A6E22E",
            error_color="#F92672",
            warning_color="#FD971F",
            border_color="#49483E",
            highlight_color="#66D9EF",
            cursor_color="#F8F8F2",
            muted_text="#75715E",
            code_bg="#1E1F1C",
            code_fg="#F8F8F2",
            link_color="#66D9EF",
            quote_border="#49483E",
            hr_color="#49483E",
            header_bg="#3E3D32",
            markdown_h1="#F92672",
            markdown_h2="#66D9EF",
            markdown_h3="#AE81FF",
            markdown_h4="#A6E22E"
        ),
        
        "Solarized Dark": ColorScheme(
            bg_color="#002B36",
            fg_color="#839496",
            accent_color="#268BD2",
            secondary_bg="#073642",
            tertiary_bg="#001F28",
            subtle_accent="#586E75",
            success_color="#859900",
            error_color="#DC322F",
            warning_color="#B58900",
            border_color="#073642",
            highlight_color="#2AA198",
            cursor_color="#839496",
            muted_text="#586E75",
            code_bg="#001F28",
            code_fg="#93A1A1",
            link_color="#268BD2",
            quote_border="#073642",
            hr_color="#073642",
            header_bg="#073642",
            markdown_h1="#CB4B16",
            markdown_h2="#2AA198",
            markdown_h3="#268BD2",
            markdown_h4="#859900"
        ),
        
        "Nord": ColorScheme(
            bg_color="#2E3440",
            fg_color="#ECEFF4",
            accent_color="#88C0D0",
            secondary_bg="#3B4252",
            tertiary_bg="#2E3440",
            subtle_accent="#4C566A",
            success_color="#A3BE8C",
            error_color="#BF616A",
            warning_color="#EBCB8B",
            border_color="#434C5E",
            highlight_color="#8FBCBB",
            cursor_color="#ECEFF4",
            muted_text="#616E88",
            code_bg="#1E2128",
            code_fg="#D8DEE9",
            link_color="#88C0D0",
            quote_border="#434C5E",
            hr_color="#434C5E",
            header_bg="#3B4252",
            markdown_h1="#B48EAD",
            markdown_h2="#8FBCBB",
            markdown_h3="#88C0D0",
            markdown_h4="#A3BE8C"
        ),
        
        "Gruvbox Dark": ColorScheme(
            bg_color="#282828",
            fg_color="#EBDBB2",
            accent_color="#83A598",
            secondary_bg="#3C3836",
            tertiary_bg="#1D2021",
            subtle_accent="#504945",
            success_color="#B8BB26",
            error_color="#FB4934",
            warning_color="#FABD2F",
            border_color="#504945",
            highlight_color="#8EC07C",
            cursor_color="#EBDBB2",
            muted_text="#7C6F64",
            code_bg="#1D2021",
            code_fg="#FBF1C7",
            link_color="#83A598",
            quote_border="#504945",
            hr_color="#504945",
            header_bg="#3C3836",
            markdown_h1="#D3869B",
            markdown_h2="#8EC07C",
            markdown_h3="#83A598",
            markdown_h4="#B8BB26"
        )
    }
    
    def __init__(self, settings_file: str = "theme_settings.json"):
        """Initialize theme manager."""
        self.settings_file = settings_file
        self.current_theme_name = "Default (Cyberpunk)"
        self.current_scheme = ColorScheme()
        self.custom_themes: Dict[str, ColorScheme] = {}
        self.callbacks = []
        
        # Load saved theme
        self.load_theme_settings()
    
    def register_callback(self, callback):
        """Register a callback to be called when theme changes."""
        self.callbacks.append(callback)
    
    def notify_theme_changed(self):
        """Notify all callbacks that theme has changed."""
        for callback in self.callbacks:
            try:
                callback(self.current_scheme)
            except Exception as e:
                print(f"Error in theme callback: {e}")
    
    def get_theme_names(self) -> list:
        """Get list of all available theme names."""
        return list(self.BUILTIN_THEMES.keys()) + list(self.custom_themes.keys())
    
    def get_current_scheme(self) -> ColorScheme:
        """Get current color scheme."""
        return self.current_scheme
    
    def get_current_theme_name(self) -> str:
        """Get current theme name."""
        return self.current_theme_name
    
    def set_theme(self, theme_name: str) -> bool:
        """Set active theme by name."""
        if theme_name in self.BUILTIN_THEMES:
            self.current_scheme = ColorScheme.from_dict(
                self.BUILTIN_THEMES[theme_name].to_dict()
            )
            self.current_theme_name = theme_name
            self.save_theme_settings()
            self.notify_theme_changed()
            return True
        elif theme_name in self.custom_themes:
            self.current_scheme = ColorScheme.from_dict(
                self.custom_themes[theme_name].to_dict()
            )
            self.current_theme_name = theme_name
            self.save_theme_settings()
            self.notify_theme_changed()
            return True
        return False
    
    def create_custom_theme(self, name: str, scheme: ColorScheme) -> bool:
        """Create a new custom theme."""
        if name in self.BUILTIN_THEMES:
            return False  # Can't override built-in themes
        
        self.custom_themes[name] = scheme
        self.save_theme_settings()
        return True
    
    def delete_custom_theme(self, name: str) -> bool:
        """Delete a custom theme."""
        if name in self.custom_themes:
            del self.custom_themes[name]
            self.save_theme_settings()
            return True
        return False
    
    def update_current_scheme(self, **kwargs):
        """Update specific colors in current scheme."""
        for key, value in kwargs.items():
            if hasattr(self.current_scheme, key):
                setattr(self.current_scheme, key, value)
        self.notify_theme_changed()
    
    def save_theme_settings(self):
        """Save theme settings to file."""
        try:
            data = {
                "current_theme": self.current_theme_name,
                "current_scheme": self.current_scheme.to_dict(),
                "custom_themes": {
                    name: scheme.to_dict() 
                    for name, scheme in self.custom_themes.items()
                }
            }
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving theme settings: {e}")
    
    def load_theme_settings(self):
        """Load theme settings from file."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Load custom themes
                if "custom_themes" in data:
                    self.custom_themes = {
                        name: ColorScheme.from_dict(scheme_dict)
                        for name, scheme_dict in data["custom_themes"].items()
                    }
                
                # Load current theme
                if "current_theme" in data:
                    self.set_theme(data["current_theme"])
                elif "current_scheme" in data:
                    # Legacy support - load scheme directly
                    self.current_scheme = ColorScheme.from_dict(data["current_scheme"])
        except Exception as e:
            print(f"Error loading theme settings: {e}")
            # Use default theme on error
            self.current_scheme = ColorScheme()
    
    def export_theme(self, theme_name: str, filepath: str) -> bool:
        """Export a theme to a JSON file."""
        try:
            scheme = None
            if theme_name in self.BUILTIN_THEMES:
                scheme = self.BUILTIN_THEMES[theme_name]
            elif theme_name in self.custom_themes:
                scheme = self.custom_themes[theme_name]
            
            if scheme:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump({
                        "name": theme_name,
                        "scheme": scheme.to_dict()
                    }, f, indent=2)
                return True
        except Exception as e:
            print(f"Error exporting theme: {e}")
        return False
    
    def import_theme(self, filepath: str) -> Optional[str]:
        """Import a theme from a JSON file. Returns theme name if successful."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if "name" in data and "scheme" in data:
                name = data["name"]
                scheme = ColorScheme.from_dict(data["scheme"])
                
                # Ensure unique name for custom themes
                if name in self.BUILTIN_THEMES:
                    name = f"{name} (Custom)"
                
                self.custom_themes[name] = scheme
                self.save_theme_settings()
                return name
        except Exception as e:
            print(f"Error importing theme: {e}")
        return None
