#!/usr/bin/env python3
"""
Mitsubishi .100 Pattern Viewer GUI

A simplified GUI application for viewing .100 format sewing patterns
using the correct format interpretation.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import tkinter.font as tkFont
from mitsubishi_100_parser import Mitsubishi100Parser, CommandType, PatternCommand
import os
import math
from typing import Optional, List, Tuple


class PatternCanvas(tk.Canvas):
    """Custom canvas for displaying .100 format sewing patterns."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.parent = parent

        # Canvas state
        self.scale = 1.0  # pixels per unit
        self.offset_x = 0
        self.offset_y = 0
        self.pattern_commands = []
        self.pattern_bounds = (0, 0, 0, 0)  # min_x, min_y, max_x, max_y

        # Interaction state
        self.dragging = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.selected_point = None
        self.highlighted_command = None

        # Bind events
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<MouseWheel>", self.on_zoom)
        self.bind("<Button-4>", self.on_zoom)  # Linux scroll up
        self.bind("<Button-5>", self.on_zoom)  # Linux scroll down

        # Colors for different command types
        self.colors = {
            CommandType.STITCH: "#FF0000",      # Red for stitches
            CommandType.MOVE: "#0000FF",        # Blue for moves
            CommandType.COLOR_CHANGE: "#00FF00", # Green for color changes
            CommandType.BACKTACK: "#FF8000",    # Orange for backtack
            CommandType.PATTERN_END: "#800080", # Purple for pattern end
            CommandType.END: "#000000",         # Black for internal end
        }

    def load_pattern(self, commands: List[PatternCommand]):
        """Load pattern commands into the canvas."""
        self.pattern_commands = commands
        self.calculate_bounds()
        self.fit_to_window()
        self.draw_pattern()

    def calculate_bounds(self):
        """Calculate the bounding box of the pattern."""
        if not self.pattern_commands:
            self.pattern_bounds = (0, 0, 100, 100)
            return

        coords = []
        for cmd in self.pattern_commands:
            if cmd.command_type in [CommandType.STITCH, CommandType.MOVE]:
                coords.append((cmd.x, cmd.y))

        if coords:
            x_coords = [x for x, y in coords]
            y_coords = [y for x, y in coords]
            self.pattern_bounds = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
        else:
            self.pattern_bounds = (0, 0, 100, 100)

    def fit_to_window(self):
        """Adjust scale and offset to fit pattern in window."""
        canvas_width = self.winfo_width() or 800
        canvas_height = self.winfo_height() or 600

        if not self.pattern_commands:
            # For empty patterns, center on origin with reasonable scale
            self.scale = 2.0  # 2 pixels per unit
            self.offset_x = canvas_width / 2
            self.offset_y = canvas_height / 2
            return

        min_x, min_y, max_x, max_y = self.pattern_bounds
        pattern_width = max_x - min_x
        pattern_height = max_y - min_y

        if pattern_width == 0 or pattern_height == 0:
            # Single point or line, center with reasonable scale
            self.scale = 2.0
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2
            self.offset_x = canvas_width / 2 - center_x * self.scale
            self.offset_y = canvas_height / 2 - center_y * self.scale
            return

        # Calculate scale to fit with some margin
        margin = 0.9  # 90% of canvas size
        scale_x = (canvas_width * margin) / pattern_width
        scale_y = (canvas_height * margin) / pattern_height
        self.scale = min(scale_x, scale_y)

        # Center the pattern
        pattern_center_x = (min_x + max_x) / 2
        pattern_center_y = (min_y + max_y) / 2
        self.offset_x = canvas_width / 2 - pattern_center_x * self.scale
        self.offset_y = canvas_height / 2 - pattern_center_y * self.scale

    def world_to_canvas(self, x: float, y: float) -> Tuple[float, float]:
        """Convert world coordinates to canvas coordinates."""
        canvas_x = x * self.scale + self.offset_x
        canvas_y = y * self.scale + self.offset_y
        return canvas_x, canvas_y

    def canvas_to_world(self, canvas_x: float, canvas_y: float) -> Tuple[float, float]:
        """Convert canvas coordinates to world coordinates."""
        world_x = (canvas_x - self.offset_x) / self.scale
        world_y = (canvas_y - self.offset_y) / self.scale
        return world_x, world_y

    def draw_pattern(self):
        """Draw the entire pattern on the canvas."""
        self.delete("all")

        # Always draw grid (even for empty patterns)
        self.draw_grid()

        # Draw stitch area boundary
        self.draw_stitch_area()

        if not self.pattern_commands:
            return

        # Draw pattern commands
        last_x, last_y = 0, 0
        path_points = []

        for i, cmd in enumerate(self.pattern_commands):
            if cmd.command_type in [CommandType.STITCH, CommandType.MOVE, CommandType.BACKTACK]:
                canvas_x, canvas_y = self.world_to_canvas(cmd.x, cmd.y)

                # Draw line from last position
                if len(path_points) > 0:
                    last_canvas_x, last_canvas_y = self.world_to_canvas(last_x, last_y)

                    # Use different line styles for different command types
                    if cmd.command_type == CommandType.STITCH:
                        # Solid line for stitches
                        self.create_line(last_canvas_x, last_canvas_y, canvas_x, canvas_y,
                                       fill=self.colors[cmd.command_type], width=2, tags="pattern")
                    elif cmd.command_type == CommandType.MOVE:
                        # Dashed line for moves
                        self.create_line(last_canvas_x, last_canvas_y, canvas_x, canvas_y,
                                       fill=self.colors[cmd.command_type], width=1,
                                       dash=(3, 3), tags="pattern")
                    elif cmd.command_type == CommandType.BACKTACK:
                        # Dotted line for backtack
                        self.create_line(last_canvas_x, last_canvas_y, canvas_x, canvas_y,
                                       fill=self.colors[cmd.command_type], width=2,
                                       dash=(1, 2), tags="pattern")

                # Draw point
                if cmd.command_type == CommandType.STITCH:
                    size = 3
                    self.create_oval(canvas_x - size, canvas_y - size,
                                   canvas_x + size, canvas_y + size,
                                   fill=self.colors[cmd.command_type],
                                   outline=self.colors[cmd.command_type],
                                   tags=f"point_{i}")
                elif cmd.command_type == CommandType.MOVE:
                    size = 2
                    self.create_oval(canvas_x - size, canvas_y - size,
                                   canvas_x + size, canvas_y + size,
                                   fill="white", outline=self.colors[cmd.command_type],
                                   width=2, tags=f"point_{i}")
                elif cmd.command_type == CommandType.BACKTACK:
                    size = 2
                    self.create_oval(canvas_x - size, canvas_y - size,
                                   canvas_x + size, canvas_y + size,
                                   fill=self.colors[cmd.command_type],
                                   outline=self.colors[cmd.command_type],
                                   tags=f"point_{i}")

                path_points.append((cmd.x, cmd.y))
                last_x, last_y = cmd.x, cmd.y

                # Add highlight if this command is selected
                if i == self.highlighted_command:
                    highlight_size = 8
                    self.create_oval(canvas_x - highlight_size, canvas_y - highlight_size,
                                   canvas_x + highlight_size, canvas_y + highlight_size,
                                   fill="", outline="yellow", width=3, tags="highlight")

            elif cmd.command_type == CommandType.COLOR_CHANGE:
                # Draw color change marker at last position
                if path_points:
                    canvas_x, canvas_y = self.world_to_canvas(last_x, last_y)
                    size = 5
                    self.create_rectangle(canvas_x - size, canvas_y - size,
                                        canvas_x + size, canvas_y + size,
                                        fill=self.colors[cmd.command_type],
                                        outline="black", width=2, tags=f"color_{i}")

                    # Add highlight if this command is selected
                    if i == self.highlighted_command:
                        highlight_size = 8
                        self.create_rectangle(canvas_x - highlight_size, canvas_y - highlight_size,
                                            canvas_x + highlight_size, canvas_y + highlight_size,
                                            fill="", outline="yellow", width=3, tags="highlight")

            elif cmd.command_type == CommandType.PATTERN_END:
                # Draw pattern end marker at position
                if cmd.x is not None and cmd.y is not None:
                    canvas_x, canvas_y = self.world_to_canvas(cmd.x, cmd.y)
                    size = 6
                    # Draw diamond shape for pattern end
                    self.create_polygon(canvas_x, canvas_y - size,
                                       canvas_x + size, canvas_y,
                                       canvas_x, canvas_y + size,
                                       canvas_x - size, canvas_y,
                                       fill=self.colors[cmd.command_type],
                                       outline="black", width=2, tags=f"end_{i}")

                    # Add highlight if this command is selected
                    if i == self.highlighted_command:
                        highlight_size = 10
                        self.create_polygon(canvas_x, canvas_y - highlight_size,
                                          canvas_x + highlight_size, canvas_y,
                                          canvas_x, canvas_y + highlight_size,
                                          canvas_x - highlight_size, canvas_y,
                                          fill="", outline="yellow", width=3, tags="highlight")

    def draw_grid(self):
        """Draw a background grid."""
        canvas_width = self.winfo_width() or 800
        canvas_height = self.winfo_height() or 600

        # Calculate grid spacing in world units
        grid_spacing_world = 10  # Base grid spacing
        while grid_spacing_world * self.scale < 20:  # Minimum 20 pixels
            grid_spacing_world *= 2
        while grid_spacing_world * self.scale > 100:  # Maximum 100 pixels
            grid_spacing_world /= 2

        # Draw vertical lines
        min_x = (0 - self.offset_x) / self.scale
        max_x = (canvas_width - self.offset_x) / self.scale

        start_x = int(min_x / grid_spacing_world) * grid_spacing_world
        x = start_x
        while x <= max_x:
            canvas_x, _ = self.world_to_canvas(x, 0)
            self.create_line(canvas_x, 0, canvas_x, canvas_height,
                           fill="#E0E0E0", width=1, tags="grid")
            x += grid_spacing_world

        # Draw horizontal lines
        min_y = (0 - self.offset_y) / self.scale
        max_y = (canvas_height - self.offset_y) / self.scale

        start_y = int(min_y / grid_spacing_world) * grid_spacing_world
        y = start_y
        while y <= max_y:
            _, canvas_y = self.world_to_canvas(0, y)
            self.create_line(0, canvas_y, canvas_width, canvas_y,
                           fill="#E0E0E0", width=1, tags="grid")
            y += grid_spacing_world

    def draw_stitch_area(self):
        """Draw the machine's stitching area boundary."""
        if not self.parent.machine_settings['show_stitch_area']:
            return

        width = self.parent.machine_settings['stitch_area_width']
        height = self.parent.machine_settings['stitch_area_height']

        # Calculate stitch area bounds (centered on origin)
        min_x = -width // 2
        max_x = width // 2
        min_y = -height // 2
        max_y = height // 2

        # Convert to canvas coordinates
        canvas_x1, canvas_y1 = self.world_to_canvas(min_x, min_y)
        canvas_x2, canvas_y2 = self.world_to_canvas(max_x, max_y)

        # Draw boundary rectangle
        self.create_rectangle(canvas_x1, canvas_y1, canvas_x2, canvas_y2,
                            outline="#FF0000", width=2, dash=(5, 5), tags="stitch_area")

        # Add labels
        label_x, label_y = self.world_to_canvas(min_x + 5, max_y - 5)
        model = self.parent.machine_settings['machine_model']
        size_mm = f"{width//10}×{height//10}mm"
        self.create_text(label_x, label_y, text=f"{model}\n{size_mm}",
                        fill="#FF0000", font=("Arial", 8), anchor="nw", tags="stitch_area")

    def on_click(self, event):
        """Handle mouse click events."""
        self.focus_set()
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y

        # Check if clicking on a point
        closest_items = self.find_closest(event.x, event.y)
        if closest_items:
            item = closest_items[0]
            tags = self.gettags(item)

            if tags and tags[0].startswith("point_"):
                point_index = int(tags[0].split("_")[1])
                self.selected_point = point_index
                self.parent.on_point_selected(point_index)
                return

        # If we get here, either no items found or not clicking on a point
        self.selected_point = None

        # In edit mode, add command where clicked
        if hasattr(self.parent, 'editing_mode') and self.parent.editing_mode:
            world_x, world_y = self.canvas_to_world(event.x, event.y)
            # Check if coordinates are within stitch area
            if self.parent.is_within_stitch_area(int(world_x), int(world_y)):
                self.parent.add_command_at_position(int(world_x), int(world_y))
            else:
                self.parent.show_area_warning(int(world_x), int(world_y))
        else:
            # Otherwise start dragging for pan
            self.dragging = True

    def on_drag(self, event):
        """Handle mouse drag events."""
        if self.dragging:
            # Pan the view
            dx = event.x - self.last_mouse_x
            dy = event.y - self.last_mouse_y
            self.offset_x += dx
            self.offset_y += dy
            self.last_mouse_x = event.x
            self.last_mouse_y = event.y
            self.draw_pattern()

    def on_release(self, event):
        """Handle mouse release events."""
        self.dragging = False

    def on_zoom(self, event):
        """Handle zoom events."""
        # Get mouse position in world coordinates before zoom
        mouse_world_x, mouse_world_y = self.canvas_to_world(event.x, event.y)

        # Determine zoom direction
        if hasattr(event, 'delta'):  # Windows
            zoom_factor = 1.1 if event.delta > 0 else 0.9
        else:  # Linux
            zoom_factor = 1.1 if event.num == 4 else 0.9

        # Apply zoom
        self.scale *= zoom_factor

        # Adjust offset to keep mouse position fixed
        new_mouse_canvas_x, new_mouse_canvas_y = self.world_to_canvas(mouse_world_x, mouse_world_y)
        self.offset_x += event.x - new_mouse_canvas_x
        self.offset_y += event.y - new_mouse_canvas_y

        self.draw_pattern()


class Pattern100ViewerGUI:
    """Main GUI application for viewing Mitsubishi .100 format patterns."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Mitsubishi .100 Pattern Viewer")
        self.root.geometry("1200x800")

        # Application state
        self.parser = Mitsubishi100Parser()
        self.current_file = None
        self.pattern_commands = []
        self.modified = False
        self.editing_mode = False
        self.current_command_type = CommandType.STITCH  # Default command type for clicking

        # Machine settings
        self.machine_settings = {
            'stitch_area_width': 200,   # Default 20mm = 200 units (0.1mm per unit)
            'stitch_area_height': 200,  # Default 20mm = 200 units
            'show_stitch_area': True,
            'restrict_to_area': True,
            'machine_model': 'PLK-A0804',
            'units_per_mm': 10  # 10 units = 1mm
        }

        self.setup_ui()
        self.setup_menu()

    def setup_menu(self):
        """Set up the application menu."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Pattern", command=self.new_pattern, accelerator="Ctrl+N")
        file_menu.add_command(label="Open Pattern...", command=self.open_pattern, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Save Pattern", command=self.save_pattern, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self.save_pattern_as, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Export to CSV...", command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Fit to Window", command=self.fit_to_window)
        view_menu.add_command(label="Zoom In", command=self.zoom_in)
        view_menu.add_command(label="Zoom Out", command=self.zoom_out)
        view_menu.add_separator()
        view_menu.add_command(label="Refresh", command=self.refresh_display)

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Toggle Edit Mode", command=self.toggle_edit_mode)
        edit_menu.add_separator()
        edit_menu.add_command(label="Add Stitch", command=self.add_stitch_dialog)
        edit_menu.add_command(label="Add Move", command=self.add_move_dialog)
        edit_menu.add_command(label="Add Color Change", command=self.add_color_change)
        edit_menu.add_command(label="Add Backtack", command=self.add_backtack)
        edit_menu.add_separator()
        edit_menu.add_command(label="Add Stitch Line", command=self.add_stitch_line_dialog)
        edit_menu.add_command(label="Generate QR Pattern", command=self.add_qr_pattern_dialog)
        edit_menu.add_separator()
        edit_menu.add_command(label="Add Pattern End", command=self.add_pattern_end)
        edit_menu.add_command(label="Add Full Ending", command=self.add_full_ending)
        edit_menu.add_separator()
        edit_menu.add_command(label="Delete Selected", command=self.delete_selected)

        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Machine Settings...", command=self.show_machine_settings)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

        # Bind keyboard shortcuts
        self.root.bind('<Control-n>', lambda e: self.new_pattern())
        self.root.bind('<Control-o>', lambda e: self.open_pattern())
        self.root.bind('<Control-s>', lambda e: self.save_pattern())
        self.root.bind('<Control-Shift-S>', lambda e: self.save_pattern_as())

    def setup_ui(self):
        """Set up the user interface."""
        # Main paned window
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel for pattern canvas
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=3)

        # Canvas frame
        canvas_frame = ttk.Frame(left_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = PatternCanvas(canvas_frame, bg="white", highlightthickness=0)
        self.canvas.parent = self  # Reference back to main GUI
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Right panel for information
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)

        # Pattern information section
        info_frame = ttk.LabelFrame(right_frame, text="Pattern Information")
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        self.info_text = tk.Text(info_frame, height=8, width=30, font=("Courier", 9))
        info_scroll = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=info_scroll.set)
        self.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        info_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Command list section
        cmd_frame = ttk.LabelFrame(right_frame, text="Commands")
        cmd_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Command listbox with scrollbar
        cmd_list_frame = ttk.Frame(cmd_frame)
        cmd_list_frame.pack(fill=tk.BOTH, expand=True)

        self.cmd_listbox = tk.Listbox(cmd_list_frame, font=("Courier", 8))
        cmd_list_scroll = ttk.Scrollbar(cmd_list_frame, orient=tk.VERTICAL, command=self.cmd_listbox.yview)
        self.cmd_listbox.configure(yscrollcommand=cmd_list_scroll.set)
        self.cmd_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cmd_list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.cmd_listbox.bind('<<ListboxSelect>>', self.on_command_selected)

        # Edit tool selector
        edit_tool_frame = ttk.LabelFrame(right_frame, text="Edit Tool (Click Mode)")
        edit_tool_frame.pack(fill=tk.X, padx=5, pady=5)

        self.command_type_var = tk.StringVar(value="STITCH")

        # Radio buttons for command types
        ttk.Radiobutton(edit_tool_frame, text="Stitch", variable=self.command_type_var,
                       value="STITCH", command=self.on_command_type_changed).pack(anchor='w', padx=5)
        ttk.Radiobutton(edit_tool_frame, text="Move", variable=self.command_type_var,
                       value="MOVE", command=self.on_command_type_changed).pack(anchor='w', padx=5)
        ttk.Radiobutton(edit_tool_frame, text="Color Change", variable=self.command_type_var,
                       value="COLOR_CHANGE", command=self.on_command_type_changed).pack(anchor='w', padx=5)
        ttk.Radiobutton(edit_tool_frame, text="Backtack", variable=self.command_type_var,
                       value="BACKTACK", command=self.on_command_type_changed).pack(anchor='w', padx=5)

        # Control buttons
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(button_frame, text="Fit View", command=self.fit_to_window).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Export CSV", command=self.export_csv).pack(side=tk.LEFT, padx=2)

        # Legend
        legend_frame = ttk.LabelFrame(right_frame, text="Legend")
        legend_frame.pack(fill=tk.X, padx=5, pady=5)

        legend_text = tk.Text(legend_frame, height=6, width=30, font=("Arial", 8))
        legend_text.insert(tk.END, "● Red solid lines: Stitches\n")
        legend_text.insert(tk.END, "○ Blue dashed lines: Moves\n")
        legend_text.insert(tk.END, "■ Green squares: Color changes\n")
        legend_text.insert(tk.END, "● Orange dotted: Backtack\n")
        legend_text.insert(tk.END, "◆ Purple diamond: Pattern end\n")
        legend_text.insert(tk.END, "Grid: Reference coordinates")
        legend_text.config(state=tk.DISABLED)
        legend_text.pack(fill=tk.X, padx=2, pady=2)

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready - Create new pattern or open existing file")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Update window title
        self.update_window_title()

    def open_pattern(self):
        """Open a .100 pattern file."""
        # Create file types for .001-.300 extensions
        pattern_extensions = [f"*.{i:03d}" for i in range(1, 301)] + ["*.100"]
        pattern_filter = " ".join(pattern_extensions)

        filename = filedialog.askopenfilename(
            title="Open Pattern File",
            filetypes=[
                ("Pattern files (.001-.300, .100)", pattern_filter),
                ("All files", "*.*")
            ],
            initialdir="." if not os.path.exists("Patterns") else "Patterns"
        )

        if filename:
            try:
                self.pattern_commands = self.parser.parse_file(filename)
                self.current_file = filename
                self.modified = False
                self.update_display()
                self.update_window_title()
                self.status_var.set(f"Loaded: {os.path.basename(filename)} ({len(self.pattern_commands)} commands)")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load pattern file:\n{str(e)}")

    def export_csv(self):
        """Export pattern to CSV format."""
        if not self.pattern_commands:
            messagebox.showwarning("Warning", "No pattern to export!")
            return

        filename = filedialog.asksaveasfilename(
            title="Export to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if filename:
            try:
                self.parser.export_to_csv(filename)
                self.status_var.set(f"Exported to CSV: {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export CSV:\n{str(e)}")

    def update_display(self):
        """Update all display elements."""
        # Update canvas
        self.canvas.load_pattern(self.pattern_commands)

        # Update information panel
        self.update_info_panel()

        # Update command list
        self.update_command_list()

    def update_info_panel(self):
        """Update the pattern information panel."""
        self.info_text.delete(1.0, tk.END)

        if not self.pattern_commands:
            self.info_text.insert(tk.END, "No pattern loaded")
            return

        # Get statistics
        stats = self.parser.get_pattern_stats()
        bounds = self.parser.get_pattern_bounds()

        info = f"File: {os.path.basename(self.current_file) if self.current_file else 'Unknown'}\n"
        info += f"Total Commands: {stats['total_commands']}\n"
        info += f"Stitches: {stats['stitch_count']}\n"
        info += f"Moves: {stats['move_count']}\n"
        info += f"Color Changes: {stats['color_changes']}\n"
        info += f"Path Length: {stats['path_length']:.1f}\n\n"
        info += f"Bounds:\n"
        info += f"X: {bounds[0]} to {bounds[2]}\n"
        info += f"Y: {bounds[1]} to {bounds[3]}\n"
        info += f"Size: {bounds[2]-bounds[0]} x {bounds[3]-bounds[1]}"

        self.info_text.insert(tk.END, info)

    def update_command_list(self):
        """Update the command list display."""
        self.cmd_listbox.delete(0, tk.END)

        for i, cmd in enumerate(self.pattern_commands):
            if cmd.command_type in [CommandType.STITCH, CommandType.MOVE, CommandType.BACKTACK]:
                text = f"{i:3d}: {cmd.command_type.value:12s} ({cmd.x:5d}, {cmd.y:5d})"
            elif cmd.command_type == CommandType.PATTERN_END:
                x_pos = f"({cmd.x:5d}, {cmd.y:5d})" if cmd.x is not None else ""
                text = f"{i:3d}: {cmd.command_type.value:12s} {x_pos}"
            else:
                text = f"{i:3d}: {cmd.command_type.value:12s}"

            self.cmd_listbox.insert(tk.END, text)

    def on_command_selected(self, event):
        """Handle command selection in the listbox."""
        selection = self.cmd_listbox.curselection()
        if selection:
            index = selection[0]
            self.canvas.selected_point = index
            self.canvas.highlighted_command = index
            self.canvas.draw_pattern()

            # Scroll the canvas to show the selected command if it has coordinates
            if index < len(self.pattern_commands):
                cmd = self.pattern_commands[index]
                if cmd.command_type in [CommandType.STITCH, CommandType.MOVE]:
                    self.scroll_to_command(cmd)

    def on_point_selected(self, point_index):
        """Handle point selection in the canvas."""
        self.cmd_listbox.selection_clear(0, tk.END)
        self.cmd_listbox.selection_set(point_index)
        self.cmd_listbox.see(point_index)
        self.canvas.highlighted_command = point_index
        self.canvas.draw_pattern()

    def fit_to_window(self):
        """Fit the pattern to the window."""
        self.canvas.fit_to_window()
        self.canvas.draw_pattern()

    def zoom_in(self):
        """Zoom in on the pattern."""
        self.canvas.scale *= 1.2
        self.canvas.draw_pattern()

    def zoom_out(self):
        """Zoom out from the pattern."""
        self.canvas.scale /= 1.2
        self.canvas.draw_pattern()

    def scroll_to_command(self, cmd):
        """Scroll the canvas to center on a specific command."""
        if cmd.command_type in [CommandType.STITCH, CommandType.MOVE]:
            # Convert command coordinates to canvas coordinates
            canvas_x, canvas_y = self.canvas.world_to_canvas(cmd.x, cmd.y)

            # Get canvas dimensions
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            # Calculate offset to center the point
            center_x = canvas_width / 2
            center_y = canvas_height / 2

            # Adjust canvas offset to center the selected point
            self.canvas.offset_x += center_x - canvas_x
            self.canvas.offset_y += center_y - canvas_y

            # Redraw the pattern
            self.canvas.draw_pattern()

    def refresh_display(self):
        """Refresh the display."""
        self.update_display()

    def new_pattern(self):
        """Create a new pattern."""
        if self.modified:
            response = messagebox.askyesnocancel("Unsaved Changes",
                                               "Save changes to current pattern before creating new one?")
            if response is True:  # Yes - save first
                if not self.save_pattern():
                    return  # Save cancelled or failed
            elif response is None:  # Cancel
                return

        # Create new pattern
        self.parser.create_new_pattern()
        self.pattern_commands = self.parser.commands
        self.current_file = None
        self.modified = False
        self.update_display()
        self.update_window_title()
        self.status_var.set("New pattern created")

    def save_pattern(self) -> bool:
        """Save the current pattern. Returns True if saved successfully."""
        if not self.pattern_commands:
            messagebox.showwarning("Warning", "No pattern to save!")
            return False

        if not self.current_file:
            return self.save_pattern_as()

        try:
            # Reset save position for delta calculation
            self.parser._last_save_x = 0
            self.parser._last_save_y = 0
            self.parser.commands = self.pattern_commands
            self.parser.save_to_file(self.current_file)
            self.modified = False
            self.update_window_title()
            self.status_var.set(f"Saved: {os.path.basename(self.current_file)}")
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save pattern:\n{str(e)}")
            return False

    def save_pattern_as(self) -> bool:
        """Save the current pattern with a new name. Returns True if saved successfully."""
        if not self.pattern_commands:
            messagebox.showwarning("Warning", "No pattern to save!")
            return False

        # Create file types for .001-.300 extensions
        pattern_extensions = [f"*.{i:03d}" for i in range(1, 301)] + ["*.100"]
        pattern_filter = " ".join(pattern_extensions)

        filename = filedialog.asksaveasfilename(
            title="Save Pattern As",
            defaultextension=".001",
            filetypes=[
                ("Pattern files (.001-.300, .100)", pattern_filter),
                ("All files", "*.*")
            ],
            initialdir="." if not os.path.exists("Patterns") else "Patterns"
        )

        if filename:
            try:
                # Reset save position for delta calculation
                self.parser._last_save_x = 0
                self.parser._last_save_y = 0
                self.parser.commands = self.pattern_commands
                self.parser.save_to_file(filename)
                self.current_file = filename
                self.modified = False
                self.update_window_title()
                self.status_var.set(f"Saved as: {os.path.basename(filename)}")
                return True
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save pattern:\n{str(e)}")
                return False
        return False

    def toggle_edit_mode(self):
        """Toggle between view and edit modes."""
        self.editing_mode = not self.editing_mode
        self.update_window_title()
        if self.editing_mode:
            command_name = self.command_type_var.get().lower().replace('_', ' ')
            self.status_var.set(f"Edit Mode - Click to add {command_name}")
        else:
            self.status_var.set("View Mode")

    def add_stitch_dialog(self):
        """Show dialog to add a stitch at specific coordinates."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Stitch")
        dialog.geometry("250x150")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Stitch Coordinates:").pack(pady=5)

        coord_frame = ttk.Frame(dialog)
        coord_frame.pack(pady=5)

        ttk.Label(coord_frame, text="X:").grid(row=0, column=0, padx=5)
        x_var = tk.StringVar(value="0")
        x_entry = ttk.Entry(coord_frame, textvariable=x_var, width=10)
        x_entry.grid(row=0, column=1, padx=5)

        ttk.Label(coord_frame, text="Y:").grid(row=0, column=2, padx=5)
        y_var = tk.StringVar(value="0")
        y_entry = ttk.Entry(coord_frame, textvariable=y_var, width=10)
        y_entry.grid(row=0, column=3, padx=5)

        def add_stitch():
            try:
                x = int(x_var.get())
                y = int(y_var.get())

                if self.is_within_stitch_area(x, y):
                    self.parser.add_stitch(x, y)
                    self.pattern_commands = self.parser.commands
                    self.modified = True
                    self.update_display()
                    self.update_window_title()
                    dialog.destroy()
                else:
                    self.show_area_warning(x, y)
            except ValueError:
                messagebox.showerror("Error", "Please enter valid integer coordinates")

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Add Stitch", command=add_stitch).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        x_entry.focus()

    def add_move_dialog(self):
        """Show dialog to add a move to specific coordinates."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Move")
        dialog.geometry("250x150")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Move Coordinates:").pack(pady=5)

        coord_frame = ttk.Frame(dialog)
        coord_frame.pack(pady=5)

        ttk.Label(coord_frame, text="X:").grid(row=0, column=0, padx=5)
        x_var = tk.StringVar(value="0")
        x_entry = ttk.Entry(coord_frame, textvariable=x_var, width=10)
        x_entry.grid(row=0, column=1, padx=5)

        ttk.Label(coord_frame, text="Y:").grid(row=0, column=2, padx=5)
        y_var = tk.StringVar(value="0")
        y_entry = ttk.Entry(coord_frame, textvariable=y_var, width=10)
        y_entry.grid(row=0, column=3, padx=5)

        def add_move():
            try:
                x = int(x_var.get())
                y = int(y_var.get())

                if self.is_within_stitch_area(x, y):
                    self.parser.add_move(x, y)
                    self.pattern_commands = self.parser.commands
                    self.modified = True
                    self.update_display()
                    self.update_window_title()
                    dialog.destroy()
                else:
                    self.show_area_warning(x, y)
            except ValueError:
                messagebox.showerror("Error", "Please enter valid integer coordinates")

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Add Move", command=add_move).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        x_entry.focus()

    def add_color_change(self):
        """Add a color change command."""
        self.parser.add_color_change()
        self.pattern_commands = self.parser.commands
        self.modified = True
        self.update_display()
        self.update_window_title()
        self.status_var.set("Color change added")

    def add_backtack(self):
        """Add a backtack sequence."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Backtack")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Backtack Settings:").pack(pady=5)

        settings_frame = ttk.Frame(dialog)
        settings_frame.pack(pady=5)

        ttk.Label(settings_frame, text="Length:").grid(row=0, column=0, padx=5, pady=5)
        length_var = tk.StringVar(value="6")
        length_entry = ttk.Entry(settings_frame, textvariable=length_var, width=10)
        length_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(settings_frame, text="Steps:").grid(row=1, column=0, padx=5, pady=5)
        steps_var = tk.StringVar(value="3")
        steps_entry = ttk.Entry(settings_frame, textvariable=steps_var, width=10)
        steps_entry.grid(row=1, column=1, padx=5, pady=5)

        info_text = tk.Text(dialog, height=3, width=35, font=("Arial", 8))
        info_text.insert(tk.END, "Backtack creates a series of rapid moves\nto secure the thread at the end of seams.\nBased on recent stitch direction.")
        info_text.config(state=tk.DISABLED)
        info_text.pack(pady=5)

        def add_backtack():
            try:
                length = int(length_var.get())
                steps = int(steps_var.get())
                length = max(1, min(20, length))  # Limit range
                steps = max(1, min(10, steps))

                self.parser.add_backtack(length, steps)
                self.pattern_commands = self.parser.commands
                self.modified = True
                self.update_display()
                self.update_window_title()
                self.status_var.set(f"Backtack sequence added ({length} moves)")
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers")

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Add Backtack", command=add_backtack).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        length_entry.focus()

    def add_pattern_end(self):
        """Add pattern end terminator."""
        self.parser.add_pattern_end()
        self.pattern_commands = self.parser.commands
        self.modified = True
        self.update_display()
        self.update_window_title()
        self.status_var.set("Pattern end terminator added")

    def add_full_ending(self):
        """Add complete ending sequence with options."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Full Ending Sequence")
        dialog.geometry("350x250")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Complete Pattern Ending:").pack(pady=5)

        settings_frame = ttk.Frame(dialog)
        settings_frame.pack(pady=5)

        ttk.Label(settings_frame, text="Backtack Length:").grid(row=0, column=0, padx=5, pady=5)
        length_var = tk.StringVar(value="8")
        length_entry = ttk.Entry(settings_frame, textvariable=length_var, width=10)
        length_entry.grid(row=0, column=1, padx=5, pady=5)

        info_text = tk.Text(dialog, height=6, width=40, font=("Arial", 9))
        info_text.insert(tk.END, "Full ending sequence includes:\n")
        info_text.insert(tk.END, "1. Color Change (0x02) - stops machine\n")
        info_text.insert(tk.END, "2. Backtack moves (0x03) - secures thread\n")
        info_text.insert(tk.END, "3. Pattern End (0x1F) - terminates pattern\n\n")
        info_text.insert(tk.END, "This matches the ending found in\noriginal Mitsubishi patterns.")
        info_text.config(state=tk.DISABLED)
        info_text.pack(pady=5)

        def add_full_ending():
            try:
                length = int(length_var.get())
                length = max(1, min(20, length))

                self.parser.add_full_ending_sequence(length)
                self.pattern_commands = self.parser.commands
                self.modified = True
                self.update_display()
                self.update_window_title()
                self.status_var.set("Complete ending sequence added")
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers")

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Add Full Ending", command=add_full_ending).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        length_entry.focus()

    def is_within_stitch_area(self, x: int, y: int) -> bool:
        """Check if coordinates are within the machine's stitch area."""
        if not self.machine_settings['restrict_to_area']:
            return True

        width = self.machine_settings['stitch_area_width']
        height = self.machine_settings['stitch_area_height']

        min_x = -width // 2
        max_x = width // 2
        min_y = -height // 2
        max_y = height // 2

        return min_x <= x <= max_x and min_y <= y <= max_y

    def show_area_warning(self, x: int, y: int):
        """Show warning when trying to stitch outside the area."""
        width_mm = self.machine_settings['stitch_area_width'] // self.machine_settings['units_per_mm']
        height_mm = self.machine_settings['stitch_area_height'] // self.machine_settings['units_per_mm']
        model = self.machine_settings['machine_model']

        messagebox.showwarning("Outside Stitch Area",
                             f"Position ({x}, {y}) is outside the {model} stitch area.\n\n"
                             f"Maximum area: {width_mm}×{height_mm}mm\n"
                             f"Centered on origin (0, 0)\n\n"
                             f"Use Settings → Machine Settings to adjust.")

    def show_machine_settings(self):
        """Show machine settings dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Machine Settings")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        # Main frame
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Machine model
        ttk.Label(main_frame, text="Machine Model:").grid(row=0, column=0, sticky='w', pady=5)
        model_var = tk.StringVar(value=self.machine_settings['machine_model'])
        model_combo = ttk.Combobox(main_frame, textvariable=model_var, width=15,
                                  values=['PLK-A0804', 'PLK-A0408', 'PLK-A0204', 'Custom'])
        model_combo.grid(row=0, column=1, padx=5, pady=5, sticky='w')

        # Stitch area settings
        ttk.Label(main_frame, text="Stitch Area (mm):").grid(row=1, column=0, sticky='w', pady=5)

        area_frame = ttk.Frame(main_frame)
        area_frame.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        width_var = tk.StringVar(value=str(self.machine_settings['stitch_area_width'] // self.machine_settings['units_per_mm']))
        height_var = tk.StringVar(value=str(self.machine_settings['stitch_area_height'] // self.machine_settings['units_per_mm']))

        ttk.Label(area_frame, text="Width:").grid(row=0, column=0, padx=(0,5))
        width_entry = ttk.Entry(area_frame, textvariable=width_var, width=8)
        width_entry.grid(row=0, column=1, padx=2)

        ttk.Label(area_frame, text="Height:").grid(row=0, column=2, padx=(10,5))
        height_entry = ttk.Entry(area_frame, textvariable=height_var, width=8)
        height_entry.grid(row=0, column=3, padx=2)

        # Preset button
        def set_preset():
            model = model_var.get()
            if model == 'PLK-A0804':
                width_var.set('20')
                height_var.set('20')
            elif model == 'PLK-A0408':
                width_var.set('40')
                height_var.set('8')
            elif model == 'PLK-A0204':
                width_var.set('20')
                height_var.set('4')

        ttk.Button(area_frame, text="Preset", command=set_preset).grid(row=0, column=4, padx=(10,0))

        # Options
        show_area_var = tk.BooleanVar(value=self.machine_settings['show_stitch_area'])
        restrict_var = tk.BooleanVar(value=self.machine_settings['restrict_to_area'])

        ttk.Checkbutton(main_frame, text="Show stitch area boundary", variable=show_area_var).grid(row=2, column=0, columnspan=2, sticky='w', pady=5)
        ttk.Checkbutton(main_frame, text="Restrict stitching to area", variable=restrict_var).grid(row=3, column=0, columnspan=2, sticky='w', pady=5)

        # Info
        info_text = tk.Text(main_frame, height=4, width=45, font=("Arial", 8))
        info_text.grid(row=4, column=0, columnspan=2, pady=(10,5), sticky='ew')
        info_text.insert(tk.END, "The stitch area represents the maximum movement\n")
        info_text.insert(tk.END, "range of your machine's needle and fabric holder.\n")
        info_text.insert(tk.END, "Patterns are centered on origin (0,0).\n")
        info_text.insert(tk.END, "Enable restrictions to prevent invalid coordinates.")
        info_text.config(state=tk.DISABLED)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)

        def apply_settings():
            try:
                width_mm = int(width_var.get())
                height_mm = int(height_var.get())

                # Validate ranges
                width_mm = max(1, min(200, width_mm))  # 1-200mm
                height_mm = max(1, min(200, height_mm))

                # Update settings
                units_per_mm = self.machine_settings['units_per_mm']
                self.machine_settings.update({
                    'machine_model': model_var.get(),
                    'stitch_area_width': width_mm * units_per_mm,
                    'stitch_area_height': height_mm * units_per_mm,
                    'show_stitch_area': show_area_var.get(),
                    'restrict_to_area': restrict_var.get()
                })

                # Refresh display
                self.canvas.draw_pattern()
                self.status_var.set(f"Settings updated: {model_var.get()} {width_mm}×{height_mm}mm")
                dialog.destroy()

            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers for area dimensions")

        def center_pattern():
            """Center current pattern on origin."""
            if self.pattern_commands:
                # Calculate current pattern center
                coords = [(cmd.x, cmd.y) for cmd in self.pattern_commands
                         if cmd.command_type in [CommandType.STITCH, CommandType.MOVE, CommandType.BACKTACK]]
                if coords:
                    x_coords = [x for x, y in coords]
                    y_coords = [y for x, y in coords]
                    center_x = (min(x_coords) + max(x_coords)) / 2
                    center_y = (min(y_coords) + max(y_coords)) / 2

                    # Shift all commands to center on origin
                    for cmd in self.pattern_commands:
                        if cmd.command_type in [CommandType.STITCH, CommandType.MOVE, CommandType.BACKTACK]:
                            cmd.x = int(cmd.x - center_x)
                            cmd.y = int(cmd.y - center_y)

                    self.modified = True
                    self.update_display()
                    self.update_window_title()
                    self.status_var.set("Pattern centered on origin")

        ttk.Button(button_frame, text="Center Pattern", command=center_pattern).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Apply", command=apply_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        # Auto-set preset when model changes
        model_combo.bind('<<ComboboxSelected>>', lambda e: set_preset())

        width_entry.focus()

    def add_stitch_line_dialog(self):
        """Show dialog to add a line of evenly distributed stitches."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Stitch Line")
        dialog.geometry("350x250")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Stitch Line Parameters:").pack(pady=5)

        # Start point
        start_frame = ttk.LabelFrame(dialog, text="Start Point")
        start_frame.pack(fill=tk.X, padx=10, pady=5)

        start_coord_frame = ttk.Frame(start_frame)
        start_coord_frame.pack(pady=5)

        ttk.Label(start_coord_frame, text="X:").grid(row=0, column=0, padx=5)
        start_x_var = tk.StringVar(value="0")
        start_x_entry = ttk.Entry(start_coord_frame, textvariable=start_x_var, width=10)
        start_x_entry.grid(row=0, column=1, padx=5)

        ttk.Label(start_coord_frame, text="Y:").grid(row=0, column=2, padx=5)
        start_y_var = tk.StringVar(value="0")
        start_y_entry = ttk.Entry(start_coord_frame, textvariable=start_y_var, width=10)
        start_y_entry.grid(row=0, column=3, padx=5)

        # End point
        end_frame = ttk.LabelFrame(dialog, text="End Point")
        end_frame.pack(fill=tk.X, padx=10, pady=5)

        end_coord_frame = ttk.Frame(end_frame)
        end_coord_frame.pack(pady=5)

        ttk.Label(end_coord_frame, text="X:").grid(row=0, column=0, padx=5)
        end_x_var = tk.StringVar(value="50")
        end_x_entry = ttk.Entry(end_coord_frame, textvariable=end_x_var, width=10)
        end_x_entry.grid(row=0, column=1, padx=5)

        ttk.Label(end_coord_frame, text="Y:").grid(row=0, column=2, padx=5)
        end_y_var = tk.StringVar(value="0")
        end_y_entry = ttk.Entry(end_coord_frame, textvariable=end_y_var, width=10)
        end_y_entry.grid(row=0, column=3, padx=5)

        # Stitch spacing
        spacing_frame = ttk.Frame(dialog)
        spacing_frame.pack(pady=5)

        ttk.Label(spacing_frame, text="Stitch Spacing (units):").grid(row=0, column=0, padx=5)
        spacing_var = tk.StringVar(value="20")  # 2mm default (20 units)
        spacing_entry = ttk.Entry(spacing_frame, textvariable=spacing_var, width=10)
        spacing_entry.grid(row=0, column=1, padx=5)

        ttk.Label(spacing_frame, text="≈2mm").grid(row=0, column=2, padx=5)

        def add_stitch_line():
            try:
                start_x = int(start_x_var.get())
                start_y = int(start_y_var.get())
                end_x = int(end_x_var.get())
                end_y = int(end_y_var.get())
                spacing = float(spacing_var.get())

                # Validate all coordinates are within stitch area
                if (self.is_within_stitch_area(start_x, start_y) and
                    self.is_within_stitch_area(end_x, end_y)):

                    self.parser.add_stitch_line(start_x, start_y, end_x, end_y, spacing)
                    self.pattern_commands = self.parser.commands
                    self.modified = True
                    self.update_display()
                    self.update_window_title()

                    # Calculate line info
                    import math
                    length = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
                    num_stitches = max(2, int(length / spacing) + 1)
                    self.status_var.set(f"Added stitch line: {num_stitches} stitches, {length:.1f} units")
                    dialog.destroy()
                else:
                    outside_coords = []
                    if not self.is_within_stitch_area(start_x, start_y):
                        outside_coords.append(f"Start ({start_x}, {start_y})")
                    if not self.is_within_stitch_area(end_x, end_y):
                        outside_coords.append(f"End ({end_x}, {end_y})")

                    messagebox.showwarning("Outside Stitch Area",
                                         f"{' and '.join(outside_coords)} outside stitch area.\n\n"
                                         f"Use Settings → Machine Settings to adjust area or coordinates.")

            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers")

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Add Stitch Line", command=add_stitch_line).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        start_x_entry.focus()

    def add_qr_pattern_dialog(self):
        """Show dialog to generate a simple QR-like pattern."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Generate QR Pattern")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="QR Pattern Generator:").pack(pady=5)

        # Text input
        text_frame = ttk.LabelFrame(dialog, text="Text to Encode")
        text_frame.pack(fill=tk.X, padx=10, pady=5)

        text_var = tk.StringVar(value="Hello")
        text_entry = ttk.Entry(text_frame, textvariable=text_var, width=30)
        text_entry.pack(pady=5)

        # Position
        pos_frame = ttk.LabelFrame(dialog, text="Center Position")
        pos_frame.pack(fill=tk.X, padx=10, pady=5)

        pos_coord_frame = ttk.Frame(pos_frame)
        pos_coord_frame.pack(pady=5)

        ttk.Label(pos_coord_frame, text="X:").grid(row=0, column=0, padx=5)
        pos_x_var = tk.StringVar(value="0")
        pos_x_entry = ttk.Entry(pos_coord_frame, textvariable=pos_x_var, width=10)
        pos_x_entry.grid(row=0, column=1, padx=5)

        ttk.Label(pos_coord_frame, text="Y:").grid(row=0, column=2, padx=5)
        pos_y_var = tk.StringVar(value="0")
        pos_y_entry = ttk.Entry(pos_coord_frame, textvariable=pos_y_var, width=10)
        pos_y_entry.grid(row=0, column=3, padx=5)

        # Size settings
        size_frame = ttk.LabelFrame(dialog, text="Pattern Size")
        size_frame.pack(fill=tk.X, padx=10, pady=5)

        size_coord_frame = ttk.Frame(size_frame)
        size_coord_frame.pack(pady=5)

        ttk.Label(size_coord_frame, text="Module Size:").grid(row=0, column=0, padx=5)
        module_var = tk.StringVar(value="12")
        module_entry = ttk.Entry(size_coord_frame, textvariable=module_var, width=8)
        module_entry.grid(row=0, column=1, padx=5)

        ttk.Label(size_coord_frame, text="Stitch Spacing:").grid(row=0, column=2, padx=5)
        stitch_var = tk.StringVar(value="8")
        stitch_entry = ttk.Entry(size_coord_frame, textvariable=stitch_var, width=8)
        stitch_entry.grid(row=0, column=3, padx=5)

        # Info
        info_text = tk.Text(dialog, height=3, width=45, font=("Arial", 8))
        info_text.pack(pady=5)
        info_text.insert(tk.END, "Creates a simple hash-based pattern (not a real QR code).\n")
        info_text.insert(tk.END, "Pattern will be 10×10 modules with border.\n")
        info_text.insert(tk.END, "Each filled module becomes a small rectangle of stitches.")
        info_text.config(state=tk.DISABLED)

        def generate_qr():
            try:
                text = text_var.get().strip()
                if not text:
                    messagebox.showwarning("Warning", "Please enter text to encode")
                    return

                center_x = int(pos_x_var.get())
                center_y = int(pos_y_var.get())
                module_size = int(module_var.get())
                stitch_spacing = float(stitch_var.get())

                # Calculate approximate pattern size
                total_size = 10 * module_size  # 10x10 modules
                min_x = center_x - total_size // 2
                max_x = center_x + total_size // 2
                min_y = center_y - total_size // 2
                max_y = center_y + total_size // 2

                # Check if pattern fits in stitch area
                if (self.is_within_stitch_area(min_x, min_y) and
                    self.is_within_stitch_area(max_x, max_y)):

                    actual_size = self.parser.generate_simple_qr_pattern(
                        text, center_x, center_y, module_size, stitch_spacing)

                    self.pattern_commands = self.parser.commands
                    self.modified = True
                    self.update_display()
                    self.update_window_title()
                    self.status_var.set(f"Generated QR pattern: '{text}' ({actual_size}×{actual_size} units)")
                    dialog.destroy()
                else:
                    messagebox.showwarning("Outside Stitch Area",
                                         f"QR pattern ({total_size}×{total_size} units) at ({center_x}, {center_y}) "
                                         f"would exceed stitch area.\n\n"
                                         f"Try smaller module size or different center position.")

            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers")

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Generate QR", command=generate_qr).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        text_entry.focus()

    def on_command_type_changed(self):
        """Handle command type selection change."""
        command_name = self.command_type_var.get()
        self.current_command_type = CommandType[command_name]
        if self.editing_mode:
            self.status_var.set(f"Edit Mode - Click to add {command_name.lower().replace('_', ' ')}")

    def add_command_at_position(self, x: int, y: int):
        """Add a command at the specified position (called from canvas click)."""
        if self.current_command_type == CommandType.STITCH:
            self.parser.add_stitch(x, y)
            self.status_var.set(f"Stitch added at ({x}, {y})")
        elif self.current_command_type == CommandType.MOVE:
            self.parser.add_move(x, y)
            self.status_var.set(f"Move added at ({x}, {y})")
        elif self.current_command_type == CommandType.COLOR_CHANGE:
            self.parser.add_color_change()
            self.status_var.set(f"Color change added")
        elif self.current_command_type == CommandType.BACKTACK:
            # For backtack, we'll add a single backtack move at this position
            from mitsubishi_100_parser import PatternCommand
            cmd = PatternCommand(
                command_type=CommandType.BACKTACK,
                x=x,
                y=y
            )
            self.parser.commands.append(cmd)
            self.status_var.set(f"Backtack added at ({x}, {y})")

        self.pattern_commands = self.parser.commands
        self.modified = True
        self.update_display()
        self.update_window_title()

    def delete_selected(self):
        """Delete the selected command."""
        if self.canvas.highlighted_command is not None:
            index = self.canvas.highlighted_command
            if 0 <= index < len(self.pattern_commands):
                del self.pattern_commands[index]
                self.parser.commands = self.pattern_commands
                self.canvas.highlighted_command = None
                self.modified = True
                self.update_display()
                self.update_window_title()
                self.status_var.set("Command deleted")

    def update_window_title(self):
        """Update the window title to show current file and modified status."""
        title = "Mitsubishi Pattern Editor"
        if self.current_file:
            title += f" - {os.path.basename(self.current_file)}"
        else:
            title += " - New Pattern"
        if self.modified:
            title += " *"
        if self.editing_mode:
            title += " [EDIT MODE]"
        self.root.title(title)

    def show_about(self):
        """Show about dialog."""
        about_text = """Mitsubishi Pattern Editor
Version 2.0

A pattern editor for Mitsubishi .100 format files
based on the correct format interpretation.

Features:
• Create, edit, and save patterns (.001-.300, .100)
• Accurate .100 format parsing
• Pattern visualization with highlighting
• Add/remove stitches, moves, and color changes
• Export to CSV format
• Zoom and pan controls

Command Types:
• Red solid lines: Stitch commands (0x61)
• Blue dashed lines: Move commands (odd bytes)
• Green squares: Color change commands (even bytes)
• Yellow highlights: Selected commands

This editor uses the correct .100 format structure with
4-byte commands and simple coordinate encoding."""

        messagebox.showinfo("About Pattern Editor", about_text)

    def run(self):
        """Start the GUI application."""
        self.root.mainloop()


def main():
    """Main entry point."""
    app = Pattern100ViewerGUI()
    app.run()


if __name__ == "__main__":
    main()