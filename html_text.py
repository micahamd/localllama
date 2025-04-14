import tkinter as tk
from tkinter import Text, font
import re
import markdown
from io import StringIO
from html.parser import HTMLParser

class HTMLTextParser(HTMLParser):
    """HTML Parser for converting HTML to Tkinter Text widget content with tags."""

    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.current_tags = []
        self.skip_data = False
        self.list_index = 0
        self.in_code_block = False
        self.code_language = ""
        self.code_content = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == 'b' or tag == 'strong':
            self.current_tags.append('bold')
        elif tag == 'i' or tag == 'em':
            self.current_tags.append('italic')
        elif tag == 'u':
            self.current_tags.append('underline')
        elif tag == 'a':
            self.current_tags.append('link')
            if 'href' in attrs_dict:
                self.text_widget.tag_config('link', foreground='blue', underline=1)
                self.text_widget.tag_bind('link', '<Button-1>',
                                         lambda e: self.open_link(attrs_dict['href']))
        elif tag == 'h1':
            self.current_tags.append('h1')
        elif tag == 'h2':
            self.current_tags.append('h2')
        elif tag == 'h3':
            self.current_tags.append('h3')
        elif tag == 'h4':
            self.current_tags.append('h4')
        elif tag == 'code':
            if 'class' in attrs_dict and attrs_dict['class'].startswith('language-'):
                self.code_language = attrs_dict['class'][9:]  # Remove 'language-' prefix
            self.in_code_block = True
            self.code_content = ""
            self.skip_data = True
        elif tag == 'pre':
            self.current_tags.append('pre')
        elif tag == 'li':
            self.text_widget.insert(tk.END, "• ", self.current_tags)
        elif tag == 'blockquote':
            self.current_tags.append('blockquote')
            self.text_widget.insert(tk.END, "│ ", 'blockquote_marker')
        elif tag == 'hr':
            self.text_widget.insert(tk.END, "\n" + "─" * 50 + "\n", 'hr')
        elif tag == 'br':
            self.text_widget.insert(tk.END, "\n", self.current_tags)

    def handle_endtag(self, tag):
        if tag == 'b' or tag == 'strong':
            self.current_tags.remove('bold')
        elif tag == 'i' or tag == 'em':
            self.current_tags.remove('italic')
        elif tag == 'u':
            self.current_tags.remove('underline')
        elif tag == 'a':
            self.current_tags.remove('link')
        elif tag == 'h1':
            self.current_tags.remove('h1')
            self.text_widget.insert(tk.END, "\n", self.current_tags)
        elif tag == 'h2':
            self.current_tags.remove('h2')
            self.text_widget.insert(tk.END, "\n", self.current_tags)
        elif tag == 'h3':
            self.current_tags.remove('h3')
            self.text_widget.insert(tk.END, "\n", self.current_tags)
        elif tag == 'h4':
            self.current_tags.remove('h4')
            self.text_widget.insert(tk.END, "\n", self.current_tags)
        elif tag == 'p':
            self.text_widget.insert(tk.END, "\n\n", self.current_tags)
        elif tag == 'li':
            self.text_widget.insert(tk.END, "\n", self.current_tags)
        elif tag == 'blockquote':
            self.current_tags.remove('blockquote')
            self.text_widget.insert(tk.END, "\n", self.current_tags)
        elif tag == 'code' and self.in_code_block:
            self.in_code_block = False
            self.skip_data = False
            self.text_widget.insert(tk.END, self.code_content, 'code')
            self.text_widget.insert(tk.END, "\n", self.current_tags)
        elif tag == 'pre':
            self.current_tags.remove('pre')

    def handle_data(self, data):
        if self.skip_data:
            if self.in_code_block:
                self.code_content += data
            return

        if data.strip():
            self.text_widget.insert(tk.END, data, tuple(self.current_tags))

    def open_link(self, url):
        import webbrowser
        webbrowser.open(url)

class HTMLText(Text):
    """A Text widget that can display HTML/Markdown content."""

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure_tags()

    def configure_tags(self):
        """Configure text tags for styling HTML elements."""
        # Get default font properties
        try:
            # Try to get the font as a named font
            default_font = font.nametofont(self.cget("font"))
            default_family = default_font.actual()["family"]
            default_size = default_font.actual()["size"]
        except Exception:
            # If that fails, parse the font tuple directly
            font_str = self.cget("font")
            if isinstance(font_str, str):
                # It's a named font
                default_family = "TkFixedFont"
                default_size = 10
            else:
                # It's a font tuple like ('Segoe UI', 12)
                default_family = font_str[0] if len(font_str) > 0 else "TkFixedFont"
                default_size = font_str[1] if len(font_str) > 1 else 10

        # Configure tags for HTML elements
        self.tag_configure('bold', font=(default_family, default_size, 'bold'))
        self.tag_configure('italic', font=(default_family, default_size, 'italic'))
        self.tag_configure('underline', underline=1)
        self.tag_configure('h1', font=(default_family, default_size + 8, 'bold'))
        self.tag_configure('h2', font=(default_family, default_size + 6, 'bold'))
        self.tag_configure('h3', font=(default_family, default_size + 4, 'bold'))
        self.tag_configure('h4', font=(default_family, default_size + 2, 'bold'))
        self.tag_configure('pre', background='#f0f0f0', font=('Consolas', default_size))
        self.tag_configure('code', background='#2A2A2A', foreground='#E0E0E0',
                           font=('Consolas', default_size))
        self.tag_configure('blockquote', background='#f0f0f0', lmargin1=20, lmargin2=20)
        self.tag_configure('blockquote_marker', foreground='#888888')
        self.tag_configure('hr', foreground='#888888')

    def display_html(self, html_content, base_tag=None):
        """Display HTML content in the Text widget."""
        parser = HTMLTextParser(self)
        parser.feed(html_content)

    def display_markdown(self, markdown_content, base_tag=None):
        """Convert Markdown to HTML and display it."""
        try:
            # First, ensure we have a clean state for this new content
            self.clear()

            # Convert markdown to HTML
            html = markdown.markdown(
                markdown_content,
                extensions=['extra', 'codehilite', 'nl2br', 'sane_lists']
            )

            # Display the HTML
            self.display_html(html, base_tag)
        except Exception as e:
            print(f"Error rendering markdown: {e}")
            # Fallback to plain text if markdown rendering fails
            self.insert(tk.END, markdown_content)

    def clear(self):
        """Clear all content from the widget."""
        self.delete(1.0, tk.END)
