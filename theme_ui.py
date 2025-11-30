"""
Theme Customization UI
Provides a user interface for customizing application themes.
"""

import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox
from theme_manager import ThemeManager, ColorScheme


class ThemeCustomizerDialog:
    """Dialog for customizing application theme."""
    
    def __init__(self, parent, theme_manager: ThemeManager):
        """Initialize the theme customizer dialog."""
        self.parent = parent
        self.theme_manager = theme_manager
        self.dialog = None
        self.preview_labels = {}
        self.color_buttons = {}
        self.modified = False
        
        # Store original scheme for cancel
        self.original_scheme = ColorScheme.from_dict(
            theme_manager.get_current_scheme().to_dict()
        )
        
        # Working copy for preview
        self.working_scheme = ColorScheme.from_dict(
            theme_manager.get_current_scheme().to_dict()
        )
    
    def show(self):
        """Show the theme customizer dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Theme Customizer")
        self.dialog.geometry("900x700")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center window
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (900 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (700 // 2)
        self.dialog.geometry(f"900x700+{x}+{y}")
        
        # Get current colors for dialog styling
        scheme = self.theme_manager.get_current_scheme()
        self.dialog.configure(background=scheme.bg_color)
        
        # Create UI
        self._create_header()
        self._create_theme_selector()
        self._create_color_editor()
        self._create_preview_area()
        self._create_buttons()
        
        # Protocol for window close
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
    
    def _create_header(self):
        """Create header section."""
        scheme = self.working_scheme
        
        header_frame = tk.Frame(self.dialog, bg=scheme.secondary_bg)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        title_label = tk.Label(
            header_frame,
            text="🎨 Theme Customizer",
            font=("Segoe UI", 16, "bold"),
            bg=scheme.secondary_bg,
            fg=scheme.accent_color
        )
        title_label.pack(pady=5)
        
        subtitle_label = tk.Label(
            header_frame,
            text="Customize the appearance of your chat interface",
            font=("Segoe UI", 10),
            bg=scheme.secondary_bg,
            fg=scheme.fg_color
        )
        subtitle_label.pack()
    
    def _create_theme_selector(self):
        """Create theme selection dropdown."""
        scheme = self.working_scheme
        
        selector_frame = tk.Frame(self.dialog, bg=scheme.bg_color)
        selector_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            selector_frame,
            text="Preset Theme:",
            font=("Segoe UI", 11, "bold"),
            bg=scheme.bg_color,
            fg=scheme.fg_color
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.theme_var = tk.StringVar(value=self.theme_manager.get_current_theme_name())
        theme_dropdown = ttk.Combobox(
            selector_frame,
            textvariable=self.theme_var,
            values=self.theme_manager.get_theme_names(),
            state="readonly",
            width=30
        )
        theme_dropdown.pack(side=tk.LEFT, padx=5)
        theme_dropdown.bind("<<ComboboxSelected>>", self._on_theme_selected)
        
        # Import/Export buttons
        ttk.Button(
            selector_frame,
            text="Import",
            command=self._import_theme
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            selector_frame,
            text="Export",
            command=self._export_theme
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            selector_frame,
            text="Save As...",
            command=self._save_as_custom
        ).pack(side=tk.LEFT, padx=5)
    
    def _create_color_editor(self):
        """Create color editing section."""
        scheme = self.working_scheme
        
        # Create scrollable canvas
        canvas_frame = tk.Frame(self.dialog, bg=scheme.bg_color)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        canvas = tk.Canvas(canvas_frame, bg=scheme.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        
        scrollable_frame = tk.Frame(canvas, bg=scheme.bg_color)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Color categories
        color_categories = {
            "Main Interface": [
                ("bg_color", "Background"),
                ("fg_color", "Text Color"),
                ("accent_color", "Accent Color"),
                ("secondary_bg", "Secondary Background"),
                ("tertiary_bg", "Tertiary Background"),
                ("subtle_accent", "Subtle Accent"),
                ("border_color", "Border Color"),
                ("highlight_color", "Highlight"),
                ("cursor_color", "Cursor"),
                ("muted_text", "Muted Text"),
            ],
            "Status Colors": [
                ("success_color", "Success"),
                ("error_color", "Error"),
                ("warning_color", "Warning"),
            ],
            "Code & Markdown": [
                ("code_bg", "Code Background"),
                ("code_fg", "Code Text"),
                ("link_color", "Links"),
                ("quote_border", "Quote Border"),
                ("hr_color", "Horizontal Rule"),
                ("header_bg", "Header Background"),
            ],
            "Markdown Headings": [
                ("markdown_h1", "Heading 1"),
                ("markdown_h2", "Heading 2"),
                ("markdown_h3", "Heading 3"),
                ("markdown_h4", "Heading 4"),
            ]
        }
        
        for category, colors in color_categories.items():
            # Category label
            category_label = tk.Label(
                scrollable_frame,
                text=category,
                font=("Segoe UI", 12, "bold"),
                bg=scheme.bg_color,
                fg=scheme.accent_color,
                anchor="w"
            )
            category_label.pack(fill=tk.X, pady=(10, 5))
            
            # Separator
            separator = tk.Frame(scrollable_frame, height=1, bg=scheme.border_color)
            separator.pack(fill=tk.X, pady=(0, 10))
            
            # Color items
            for attr_name, display_name in colors:
                self._create_color_item(scrollable_frame, attr_name, display_name)
    
    def _create_color_item(self, parent, attr_name, display_name):
        """Create a single color editing item."""
        scheme = self.working_scheme
        color_value = getattr(scheme, attr_name)
        
        if color_value is None:
            color_value = scheme.fg_color  # Default fallback
        
        item_frame = tk.Frame(parent, bg=scheme.bg_color)
        item_frame.pack(fill=tk.X, pady=2)
        
        # Label
        label = tk.Label(
            item_frame,
            text=display_name,
            font=("Segoe UI", 10),
            bg=scheme.bg_color,
            fg=scheme.fg_color,
            width=25,
            anchor="w"
        )
        label.pack(side=tk.LEFT, padx=5)
        
        # Color preview button
        color_btn = tk.Button(
            item_frame,
            text="    ",
            bg=color_value,
            width=10,
            relief="solid",
            borderwidth=1,
            command=lambda: self._choose_color(attr_name)
        )
        color_btn.pack(side=tk.LEFT, padx=5)
        self.color_buttons[attr_name] = color_btn
        
        # Hex value label
        hex_label = tk.Label(
            item_frame,
            text=color_value,
            font=("Consolas", 9),
            bg=scheme.bg_color,
            fg=scheme.muted_text,
            width=10,
            anchor="w"
        )
        hex_label.pack(side=tk.LEFT, padx=5)
        self.preview_labels[attr_name] = hex_label
    
    def _create_preview_area(self):
        """Create preview area showing theme in action."""
        scheme = self.working_scheme
        
        preview_frame = tk.LabelFrame(
            self.dialog,
            text="Preview",
            font=("Segoe UI", 11, "bold"),
            bg=scheme.bg_color,
            fg=scheme.accent_color,
            borderwidth=2,
            relief="groove"
        )
        preview_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Sample chat message
        sample_frame = tk.Frame(preview_frame, bg=scheme.secondary_bg)
        sample_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # User message
        user_label = tk.Label(
            sample_frame,
            text="👤 You",
            font=("Segoe UI", 10, "bold"),
            bg=scheme.secondary_bg,
            fg=scheme.highlight_color,
            anchor="w"
        )
        user_label.pack(fill=tk.X)
        
        user_msg = tk.Label(
            sample_frame,
            text="This is a preview of your theme!",
            font=("Segoe UI", 10),
            bg=scheme.secondary_bg,
            fg=scheme.fg_color,
            anchor="w"
        )
        user_msg.pack(fill=tk.X, pady=(0, 10))
        
        # Assistant message
        assistant_label = tk.Label(
            sample_frame,
            text="🤖 Assistant",
            font=("Segoe UI", 10, "bold"),
            bg=scheme.secondary_bg,
            fg=scheme.accent_color,
            anchor="w"
        )
        assistant_label.pack(fill=tk.X)
        
        assistant_msg = tk.Label(
            sample_frame,
            text="Your customized colors look great! ✨",
            font=("Segoe UI", 10),
            bg=scheme.secondary_bg,
            fg=scheme.fg_color,
            anchor="w"
        )
        assistant_msg.pack(fill=tk.X)
    
    def _create_buttons(self):
        """Create action buttons."""
        scheme = self.working_scheme
        
        button_frame = tk.Frame(self.dialog, bg=scheme.bg_color)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(
            button_frame,
            text="Apply",
            command=self._on_apply,
            style="Primary.TButton"
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="OK",
            command=self._on_ok,
            style="Primary.TButton"
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Reset to Default",
            command=self._on_reset
        ).pack(side=tk.RIGHT, padx=5)
    
    def _choose_color(self, attr_name):
        """Open color chooser for specific attribute."""
        current_color = getattr(self.working_scheme, attr_name)
        if current_color is None:
            current_color = self.working_scheme.fg_color
        
        color = colorchooser.askcolor(
            color=current_color,
            title=f"Choose {attr_name.replace('_', ' ').title()}"
        )
        
        if color[1]:  # color[1] is the hex value
            setattr(self.working_scheme, attr_name, color[1])
            self.color_buttons[attr_name].configure(bg=color[1])
            self.preview_labels[attr_name].configure(text=color[1])
            self.modified = True
            self._update_dialog_colors()
    
    def _on_theme_selected(self, event=None):
        """Handle theme selection from dropdown."""
        theme_name = self.theme_var.get()
        if self.theme_manager.set_theme(theme_name):
            # Update working scheme
            self.working_scheme = ColorScheme.from_dict(
                self.theme_manager.get_current_scheme().to_dict()
            )
            self._refresh_ui()
            self.modified = False
    
    def _refresh_ui(self):
        """Refresh all UI elements with current scheme."""
        # Update color buttons and labels
        for attr_name, button in self.color_buttons.items():
            color_value = getattr(self.working_scheme, attr_name)
            if color_value is None:
                color_value = self.working_scheme.fg_color
            button.configure(bg=color_value)
            self.preview_labels[attr_name].configure(text=color_value)
        
        self._update_dialog_colors()
        
        # Update dialog background
        try:
            self.dialog.configure(background=self.working_scheme.bg_color)
            self.dialog.update_idletasks()
        except:
            pass
    
    def _update_dialog_colors(self):
        """Update dialog colors based on working scheme."""
        # This is a simplified update - full update would require recreating widgets
        self.dialog.configure(background=self.working_scheme.bg_color)
    
    def _import_theme(self):
        """Import a theme from file."""
        filepath = filedialog.askopenfilename(
            title="Import Theme",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filepath:
            theme_name = self.theme_manager.import_theme(filepath)
            if theme_name:
                messagebox.showinfo("Success", f"Theme '{theme_name}' imported successfully!")
                self.theme_var.set(theme_name)
                self._on_theme_selected()
            else:
                messagebox.showerror("Error", "Failed to import theme. Check file format.")
    
    def _export_theme(self):
        """Export current theme to file."""
        theme_name = self.theme_var.get()
        filepath = filedialog.asksaveasfilename(
            title="Export Theme",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"{theme_name.replace(' ', '_')}.json"
        )
        
        if filepath:
            if self.theme_manager.export_theme(theme_name, filepath):
                messagebox.showinfo("Success", "Theme exported successfully!")
            else:
                messagebox.showerror("Error", "Failed to export theme.")
    
    def _save_as_custom(self):
        """Save current colors as a custom theme."""
        from tkinter import simpledialog
        
        name = simpledialog.askstring(
            "Save Custom Theme",
            "Enter a name for this theme:",
            parent=self.dialog
        )
        
        if name:
            if self.theme_manager.create_custom_theme(name, self.working_scheme):
                self.theme_manager.set_theme(name)
                self.theme_var.set(name)
                messagebox.showinfo("Success", f"Custom theme '{name}' saved!")
            else:
                messagebox.showerror("Error", "Cannot override built-in themes. Choose a different name.")
    
    def _on_apply(self):
        """Apply changes without closing."""
        # Update theme manager with working scheme
        for attr_name in vars(self.working_scheme):
            value = getattr(self.working_scheme, attr_name)
            setattr(self.theme_manager.current_scheme, attr_name, value)
        
        self.theme_manager.notify_theme_changed()
        self.theme_manager.save_theme_settings()
        self.modified = False
        
        # Update the dialog's own colors
        try:
            self.dialog.configure(background=self.working_scheme.bg_color)
            # Force a refresh of the dialog
            self.dialog.update_idletasks()
        except:
            pass
        
        messagebox.showinfo("Applied", "Theme changes applied!")
    
    def _on_ok(self):
        """Apply changes and close."""
        self._on_apply()
        self.dialog.destroy()
    
    def _on_cancel(self):
        """Cancel changes and close."""
        if self.modified:
            result = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to apply them?",
                parent=self.dialog
            )
            
            if result is None:  # Cancel
                return
            elif result:  # Yes
                self._on_apply()
        
        # Restore original scheme
        for attr_name in vars(self.original_scheme):
            value = getattr(self.original_scheme, attr_name)
            setattr(self.theme_manager.current_scheme, attr_name, value)
        
        self.theme_manager.notify_theme_changed()
        self.dialog.destroy()
    
    def _on_reset(self):
        """Reset to default theme."""
        if messagebox.askyesno("Reset Theme", "Reset to default theme?", parent=self.dialog):
            self.theme_manager.set_theme("Default (Cyberpunk)")
            self.theme_var.set("Default (Cyberpunk)")
            self.working_scheme = ColorScheme.from_dict(
                self.theme_manager.get_current_scheme().to_dict()
            )
            self._refresh_ui()
            self.modified = False
