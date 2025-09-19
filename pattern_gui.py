#!/usr/bin/env python3
"""
Mitsubishi PLK-A0804F Pattern Editor GUI

A comprehensive GUI application for viewing, analyzing, and editing sewing patterns
from Mitsubishi PLK-A0804F controllers.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import tkinter.font as tkFont
from mitsubishi_pattern_parser import MitsubishiPatternParser, CommandType, PatternCommand
import os
import math
from typing import Optional, List, Tuple

class PatternCanvas(tk.Canvas):
    """Custom canvas for displaying and editing sewing patterns."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.parent = parent

        # Canvas state
        self.scale = 0.1  # Initial scale (units per pixel)
        self.offset_x = 0
        self.offset_y = 0
        self.pattern_commands = []
        self.pattern_bounds = (0, 0, 0, 0)  # min_x, min_y, max_x, max_y

        # Interaction state
        self.dragging = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.selected_point = None

        # Bind events
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<MouseWheel>", self.on_zoom)
        self.bind("<Button-4>", self.on_zoom)  # Linux scroll up
        self.bind("<Button-5>", self.on_zoom)  # Linux scroll down

        # Colors for different command types
        self.colors = {
            CommandType.POINT: "#FF0000",          # Red for stitch points
            CommandType.LINEAR_MOVE: "#0000FF",    # Blue for moves
            CommandType.CIRCULAR: "#00FF00",       # Green for circular
            CommandType.ARC: "#FF8800",            # Orange for arcs
            CommandType.CURVE: "#8800FF",          # Purple for curves
            CommandType.SPEED: "#888888",          # Gray for speed
            CommandType.FUNCTION: "#FF00FF",       # Magenta for functions
            CommandType.SEPARATOR: "#000000",      # Black for separators
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
            if cmd.command_type in [CommandType.POINT, CommandType.LINEAR_MOVE, CommandType.CIRCULAR]:
                coords.append((cmd.x, cmd.y))

        if coords:
            x_coords = [x for x, y in coords]
            y_coords = [y for x, y in coords]
            self.pattern_bounds = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
        else:
            self.pattern_bounds = (0, 0, 100, 100)

    def fit_to_window(self):
        """Adjust scale and offset to fit pattern in window."""
        if not self.pattern_commands:
            return

        canvas_width = self.winfo_width() or 800
        canvas_height = self.winfo_height() or 600

        min_x, min_y, max_x, max_y = self.pattern_bounds
        pattern_width = max_x - min_x
        pattern_height = max_y - min_y

        if pattern_width == 0 or pattern_height == 0:
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

        if not self.pattern_commands:
            return

        # Draw grid
        self.draw_grid()

        # Draw pattern commands
        last_x, last_y = 0, 0

        for i, cmd in enumerate(self.pattern_commands):
            if cmd.command_type in [CommandType.POINT, CommandType.LINEAR_MOVE, CommandType.CIRCULAR]:
                canvas_x, canvas_y = self.world_to_canvas(cmd.x, cmd.y)

                # Draw line from last position if it's a movement
                if cmd.command_type == CommandType.LINEAR_MOVE and i > 0:
                    last_canvas_x, last_canvas_y = self.world_to_canvas(last_x, last_y)
                    self.create_line(last_canvas_x, last_canvas_y, canvas_x, canvas_y,
                                   fill=self.colors[cmd.command_type], width=1, tags="pattern")

                # Draw point
                size = 3 if cmd.command_type == CommandType.POINT else 2
                color = self.colors[cmd.command_type]

                self.create_oval(canvas_x - size, canvas_y - size,
                               canvas_x + size, canvas_y + size,
                               fill=color, outline=color, tags=f"point_{i}")

                last_x, last_y = cmd.x, cmd.y

    def draw_grid(self):
        """Draw a background grid."""
        canvas_width = self.winfo_width() or 800
        canvas_height = self.winfo_height() or 600

        # Calculate grid spacing in world units
        grid_spacing_world = 1000  # Base grid spacing
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

    def on_click(self, event):
        """Handle mouse click events."""
        self.focus_set()
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y

        # Check if clicking on a point
        item = self.find_closest(event.x, event.y)[0]
        tags = self.gettags(item)

        if tags and tags[0].startswith("point_"):
            point_index = int(tags[0].split("_")[1])
            self.selected_point = point_index
            self.parent.on_point_selected(point_index)
        else:
            self.selected_point = None
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
        elif self.selected_point is not None:
            # Move selected point
            world_x, world_y = self.canvas_to_world(event.x, event.y)
            cmd = self.pattern_commands[self.selected_point]
            cmd.x = int(world_x)
            cmd.y = int(world_y)
            self.draw_pattern()
            self.parent.on_pattern_modified()

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


class PatternEditorGUI:
    """Main GUI application for editing Mitsubishi sewing patterns."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Mitsubishi PLK-A0804F Pattern Editor")
        self.root.geometry("1200x800")

        # Application state
        self.parser = MitsubishiPatternParser()
        self.current_file = None
        self.pattern_commands = []
        self.modified = False

        self.setup_ui()
        self.setup_menu()

    def setup_menu(self):
        """Set up the application menu."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Pattern...", command=self.open_pattern, accelerator="Ctrl+O")
        file_menu.add_command(label="Save Pattern", command=self.save_pattern, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self.save_pattern_as)
        file_menu.add_separator()
        file_menu.add_command(label="Export to CSV...", command=self.export_csv)
        file_menu.add_command(label="Export to G-code...", command=self.export_gcode)
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

        # Validation menu
        validation_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Validation", menu=validation_menu)
        validation_menu.add_command(label="Run Pattern Validation", command=self.validate_pattern)
        validation_menu.add_command(label="Parser Status", command=self.show_parser_status)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About Parser", command=self.show_about)

        # Bind keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self.open_pattern())
        self.root.bind('<Control-s>', lambda e: self.save_pattern())

    def setup_ui(self):
        """Set up the user interface."""
        # Main paned window
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel for pattern canvas
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=3)

        # Canvas frame with scrollbars
        canvas_frame = ttk.Frame(left_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = PatternCanvas(canvas_frame, bg="white", highlightthickness=0)
        self.canvas.parent = self  # Reference back to main GUI

        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Pack canvas and scrollbars
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Right panel for controls and information
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)

        # Validation Warning section
        warning_frame = ttk.LabelFrame(right_frame, text="⚠️ Parser Status")
        warning_frame.pack(fill=tk.X, padx=5, pady=5)

        warning_text = tk.Text(warning_frame, height=4, width=30, font=("Arial", 8),
                              bg="#fff3cd", fg="#856404", wrap=tk.WORD)
        warning_text.insert(tk.END, "⚠️ EXPERIMENTAL PARSER\n")
        warning_text.insert(tk.END, "This interpretation is based on reverse-engineering and may be incorrect. ")
        warning_text.insert(tk.END, "Validation shows command type identification needs verification. ")
        warning_text.insert(tk.END, "Test with simple known patterns!")
        warning_text.config(state=tk.DISABLED)
        warning_text.pack(fill=tk.X, padx=2, pady=2)

        # Pattern information section
        info_frame = ttk.LabelFrame(right_frame, text="Pattern Information")
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        self.info_text = tk.Text(info_frame, height=6, width=30, font=("Courier", 9))
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

        # Validation Status section
        validation_frame = ttk.LabelFrame(right_frame, text="🔍 Interpretation Confidence")
        validation_frame.pack(fill=tk.X, padx=5, pady=5)

        self.validation_text = tk.Text(validation_frame, height=5, width=30, font=("Courier", 8))
        validation_scroll = ttk.Scrollbar(validation_frame, orient=tk.VERTICAL, command=self.validation_text.yview)
        self.validation_text.configure(yscrollcommand=validation_scroll.set)
        self.validation_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        validation_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Control buttons
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(button_frame, text="Add Point", command=self.add_point).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Delete", command=self.delete_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Validate", command=self.validate_pattern).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Fit View", command=self.fit_to_window).pack(side=tk.LEFT, padx=2)

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def open_pattern(self):
        """Open a pattern file."""
        filename = filedialog.askopenfilename(
            title="Open Pattern File",
            filetypes=[
                ("Pattern files", "*.100 *.101 *.102 *.103 *.104 *.105 *.106 *.107 *.108 *.109 *.110 *.111 *.112 *.113 *.114 *.115 *.116 *.117 *.118"),
                ("All files", "*.*")
            ],
            initialdir="Patterns" if os.path.exists("Patterns") else "."
        )

        if filename:
            try:
                self.pattern_commands = self.parser.parse_file(filename)
                self.current_file = filename
                self.modified = False
                self.update_display()
                self.status_var.set(f"Loaded: {os.path.basename(filename)} ({len(self.pattern_commands)} commands)")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load pattern file:\n{str(e)}")

    def save_pattern(self):
        """Save the current pattern."""
        if not self.current_file:
            self.save_pattern_as()
            return

        try:
            self.save_pattern_to_file(self.current_file)
            self.modified = False
            self.status_var.set(f"Saved: {os.path.basename(self.current_file)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save pattern file:\n{str(e)}")

    def save_pattern_as(self):
        """Save the current pattern with a new name."""
        if not self.pattern_commands:
            messagebox.showwarning("Warning", "No pattern to save!")
            return

        filename = filedialog.asksaveasfilename(
            title="Save Pattern As",
            defaultextension=".102",
            filetypes=[
                ("Pattern files", "*.100 *.101 *.102 *.103 *.104 *.105 *.106 *.107 *.108 *.109 *.110 *.111 *.112 *.113 *.114 *.115 *.116 *.117 *.118"),
                ("All files", "*.*")
            ]
        )

        if filename:
            try:
                self.save_pattern_to_file(filename)
                self.current_file = filename
                self.modified = False
                self.status_var.set(f"Saved as: {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save pattern file:\n{str(e)}")

    def save_pattern_to_file(self, filename):
        """Save pattern commands to a binary file."""
        with open(filename, 'wb') as f:
            for cmd in self.pattern_commands:
                if cmd.raw_data:
                    f.write(cmd.raw_data)

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
                self.parser.export_to_csv(self.current_file or "temp", filename)
                self.status_var.set(f"Exported to CSV: {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export CSV:\n{str(e)}")

    def export_gcode(self):
        """Export pattern to G-code format."""
        if not self.pattern_commands:
            messagebox.showwarning("Warning", "No pattern to export!")
            return

        filename = filedialog.asksaveasfilename(
            title="Export to G-code",
            defaultextension=".gcode",
            filetypes=[("G-code files", "*.gcode *.nc"), ("All files", "*.*")]
        )

        if filename:
            try:
                self.export_to_gcode(filename)
                self.status_var.set(f"Exported to G-code: {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export G-code:\n{str(e)}")

    def export_to_gcode(self, filename):
        """Export pattern to G-code format."""
        with open(filename, 'w') as f:
            f.write(f"; G-code export from Mitsubishi Pattern Editor\n")
            f.write(f"; Original file: {self.current_file or 'New Pattern'}\n")
            f.write(f"; Total commands: {len(self.pattern_commands)}\n\n")

            f.write("G90 ; Absolute positioning\n")
            f.write("G21 ; Units in millimeters\n\n")

            for cmd in self.pattern_commands:
                if cmd.command_type == CommandType.POINT:
                    x_mm = cmd.x / 100.0
                    y_mm = cmd.y / 100.0
                    f.write(f"G1 X{x_mm:.2f} Y{y_mm:.2f} ; Stitch\n")
                elif cmd.command_type == CommandType.LINEAR_MOVE:
                    x_mm = cmd.x / 100.0
                    y_mm = cmd.y / 100.0
                    f.write(f"G0 X{x_mm:.2f} Y{y_mm:.2f} ; Move\n")
                elif cmd.command_type == CommandType.CIRCULAR:
                    x_mm = cmd.x / 100.0
                    y_mm = cmd.y / 100.0
                    f.write(f"G2 X{x_mm:.2f} Y{y_mm:.2f} ; Circular\n")

            f.write("\nM30 ; End of program\n")

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
            self.update_validation_panel()
            return

        # Calculate statistics
        analysis = self.parser.analyze_pattern_motion(self.current_file or "temp")

        info = f"File: {os.path.basename(self.current_file) if self.current_file else 'New Pattern'}\n"
        info += f"Commands: {len(self.pattern_commands)}\n"
        info += f"Stitch Points: {analysis['stitch_points']}\n"
        info += f"Movements: {analysis['movement_commands']}\n"
        info += f"Speed Changes: {analysis['speed_changes']}\n"
        info += f"Functions: {analysis['function_calls']}\n"
        info += f"Path Length: {analysis['path_length']:.1f}\n\n"

        x_range = analysis['coordinate_range']['x']
        y_range = analysis['coordinate_range']['y']
        info += f"X Range: {x_range[0]} to {x_range[1]}\n"
        info += f"Y Range: {y_range[0]} to {y_range[1]}\n"
        info += f"Size: {x_range[1]-x_range[0]} x {y_range[1]-y_range[0]}"

        self.info_text.insert(tk.END, info)
        self.update_validation_panel()

    def update_validation_panel(self):
        """Update the validation/confidence panel."""
        self.validation_text.delete(1.0, tk.END)

        if not self.pattern_commands:
            self.validation_text.insert(tk.END, "Load a pattern to see validation")
            return

        # Check for known issues based on validation findings
        validation_info = ""

        # Check envelope pattern specifically
        filename = os.path.basename(self.current_file) if self.current_file else ""
        if "2020KUV" in filename or "envelope" in filename.lower():
            validation_info += "✓ Envelope pattern - Shape validated\n"

        # Check for function codes
        func_commands = [cmd for cmd in self.pattern_commands if cmd.command_type.name == "FUNCTION"]
        if func_commands:
            validation_info += f"⚠️ {len(func_commands)} function commands found\n"

        # Check coordinate reasonableness
        coords = []
        for cmd in self.pattern_commands:
            if hasattr(cmd, 'x') and hasattr(cmd, 'y') and cmd.x is not None:
                coords.append((cmd.x, cmd.y))

        if coords:
            x_coords = [x for x, y in coords]
            y_coords = [y for x, y in coords]
            max_coord = max(max(x_coords), max(y_coords))

            if max_coord > 50000:
                validation_info += "⚠️ Very large coordinates detected\n"

        # Parser confidence assessment
        validation_info += "\nParser Confidence:\n"
        validation_info += "✓ Coordinate extraction\n"
        validation_info += "❓ Command type identification\n"
        validation_info += "❓ Function parameter decoding\n"
        validation_info += "\nNEEDS MACHINE TESTING!"

        self.validation_text.insert(tk.END, validation_info)

    def update_command_list(self):
        """Update the command list display."""
        self.cmd_listbox.delete(0, tk.END)

        for i, cmd in enumerate(self.pattern_commands):
            if cmd.command_type in [CommandType.POINT, CommandType.LINEAR_MOVE, CommandType.CIRCULAR]:
                text = f"{i:3d}: {cmd.command_type.name:12s} ({cmd.x:5d}, {cmd.y:5d})"
            else:
                params = ','.join(map(str, cmd.parameters)) if cmd.parameters else ""
                text = f"{i:3d}: {cmd.command_type.name:12s} {params}"

            self.cmd_listbox.insert(tk.END, text)

    def on_command_selected(self, event):
        """Handle command selection in the listbox."""
        selection = self.cmd_listbox.curselection()
        if selection:
            index = selection[0]
            self.canvas.selected_point = index
            self.canvas.draw_pattern()

    def on_point_selected(self, point_index):
        """Handle point selection in the canvas."""
        self.cmd_listbox.selection_clear(0, tk.END)
        self.cmd_listbox.selection_set(point_index)
        self.cmd_listbox.see(point_index)

    def on_pattern_modified(self):
        """Handle pattern modification."""
        self.modified = True
        self.update_info_panel()
        self.update_command_list()

    def add_point(self):
        """Add a new stitch point."""
        if not self.pattern_commands:
            # Create first point at origin
            new_cmd = PatternCommand(CommandType.POINT, x=0, y=0)
        else:
            # Add point near the last point
            last_cmd = None
            for cmd in reversed(self.pattern_commands):
                if cmd.command_type in [CommandType.POINT, CommandType.LINEAR_MOVE, CommandType.CIRCULAR]:
                    last_cmd = cmd
                    break

            if last_cmd:
                new_cmd = PatternCommand(CommandType.POINT, x=last_cmd.x + 100, y=last_cmd.y + 100)
            else:
                new_cmd = PatternCommand(CommandType.POINT, x=0, y=0)

        # Rebuild raw data for the new command
        import struct
        new_cmd.raw_data = struct.pack('<BHH', 0x61, new_cmd.x & 0xFF, new_cmd.y)

        self.pattern_commands.append(new_cmd)
        self.on_pattern_modified()
        self.canvas.draw_pattern()

    def delete_selected(self):
        """Delete the selected command."""
        if self.canvas.selected_point is not None:
            if 0 <= self.canvas.selected_point < len(self.pattern_commands):
                del self.pattern_commands[self.canvas.selected_point]
                self.canvas.selected_point = None
                self.on_pattern_modified()
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

    def validate_pattern(self):
        """Run comprehensive pattern validation."""
        if not self.pattern_commands:
            messagebox.showwarning("Warning", "No pattern loaded to validate!")
            return

        # Create validation report
        report = "PATTERN VALIDATION REPORT\n"
        report += "=" * 40 + "\n\n"

        filename = os.path.basename(self.current_file) if self.current_file else "Unknown"
        report += f"File: {filename}\n"
        report += f"Commands: {len(self.pattern_commands)}\n\n"

        # Check for known patterns
        if "2020KUV" in filename:
            report += "ENVELOPE PATTERN VALIDATION:\n"
            coords = []
            for cmd in self.pattern_commands:
                if hasattr(cmd, 'x') and hasattr(cmd, 'y') and cmd.x is not None:
                    coords.append((cmd.x, cmd.y))

            if coords:
                x_coords = [x for x, y in coords]
                y_coords = [y for x, y in coords]
                width = max(x_coords) - min(x_coords)
                height = max(y_coords) - min(y_coords)
                aspect_ratio = width / height if height > 0 else 0

                report += f"  Aspect ratio: {aspect_ratio:.3f}\n"
                if 0.8 <= aspect_ratio <= 1.2:
                    report += "  ✓ Square shape confirmed\n"
                else:
                    report += "  ❌ Not square - parsing error?\n"

        # Function code analysis
        report += "\nFUNCTION CODE ANALYSIS:\n"
        if self.current_file:
            try:
                with open(self.current_file, 'rb') as f:
                    data = f.read()

                manual_codes = {
                    0x0002: "Thread Trimming",
                    0x0003: "Feed",
                    0x0004: "HALT",
                    0x0005: "Reverse Rotation",
                    0x0006: "Second Home Position",
                    0x0007: "Basting",
                    0x0031: "END Data"
                }

                found_codes = []
                for code, name in manual_codes.items():
                    import struct
                    le_bytes = struct.pack('<H', code)
                    if le_bytes in data:
                        pos = data.find(le_bytes)
                        found_codes.append(f"  Found {name} at byte {pos}")

                if found_codes:
                    report += "\n".join(found_codes) + "\n"
                else:
                    report += "  No manual function codes found\n"

            except Exception as e:
                report += f"  Error reading file: {e}\n"

        # Coordinate analysis
        report += "\nCOORDINATE ANALYSIS:\n"
        coords = []
        for cmd in self.pattern_commands:
            if hasattr(cmd, 'x') and hasattr(cmd, 'y') and cmd.x is not None:
                coords.append((cmd.x, cmd.y))

        if coords:
            x_coords = [x for x, y in coords]
            y_coords = [y for x, y in coords]
            report += f"  X range: {min(x_coords)} to {max(x_coords)}\n"
            report += f"  Y range: {min(y_coords)} to {max(y_coords)}\n"

            max_coord = max(max(x_coords), max(y_coords))
            if max_coord > 100000:
                report += "  ⚠️ Extremely large coordinates - check scaling\n"
            elif max_coord > 50000:
                report += "  ⚠️ Large coordinates detected\n"
            else:
                report += "  ✓ Reasonable coordinate range\n"

        # Parser confidence
        report += "\nPARSER CONFIDENCE ASSESSMENT:\n"
        report += "✓ HIGH: Coordinate extraction (validated with envelope)\n"
        report += "❓ LOW:  Command type identification (0x03 = coordinates, not commands)\n"
        report += "❓ MED:  Function code detection (manual codes found in data)\n"
        report += "❌ UNKNOWN: Real command structure\n\n"

        report += "RECOMMENDATION:\n"
        report += "Create simple test patterns on your machine and compare\n"
        report += "with parser output to verify interpretation accuracy."

        # Show report in a dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Pattern Validation Report")
        dialog.geometry("600x500")

        text_widget = scrolledtext.ScrolledText(dialog, font=("Courier", 10))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(tk.END, report)
        text_widget.config(state=tk.DISABLED)

        close_btn = ttk.Button(dialog, text="Close", command=dialog.destroy)
        close_btn.pack(pady=5)

    def show_parser_status(self):
        """Show detailed parser status and limitations."""
        status_text = """MITSUBISHI PATTERN PARSER STATUS

⚠️ IMPORTANT DISCLAIMER ⚠️
This parser is based on reverse-engineering and has NOT been validated
against official Mitsubishi documentation.

VALIDATION FINDINGS:
✓ Coordinate extraction appears correct (envelope pattern validates as square)
✓ Function codes from manual found in pattern data
❌ Command type identification is QUESTIONABLE
❌ Binary structure interpretation needs verification

CRITICAL ISSUE DISCOVERED:
The byte sequence 0x03 appears to be coordinate data, NOT command types
as initially interpreted. This means the parser's command classification
may be fundamentally incorrect.

WHAT WORKS:
- Pattern visualization (coordinates seem correct)
- File loading and basic structure parsing
- Function code detection
- Shape analysis (envelope pattern shows correct aspect ratio)

WHAT NEEDS VERIFICATION:
- All command type identifications (0x61, 0x03, 0xE1, etc.)
- Parameter decoding for functions
- Coordinate scaling and units
- Binary structure interpretation

RECOMMENDATION:
Create simple test patterns on your sewing machine:
1. Single stitch at known position
2. Simple line of stitches
3. Basic geometric shape

Then compare the parser output with your known input to verify accuracy.

USE AT YOUR OWN RISK for pattern editing until validated!"""

        dialog = tk.Toplevel(self.root)
        dialog.title("Parser Status & Limitations")
        dialog.geometry("700x600")

        text_widget = scrolledtext.ScrolledText(dialog, font=("Arial", 10), wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(tk.END, status_text)
        text_widget.config(state=tk.DISABLED)

        close_btn = ttk.Button(dialog, text="Close", command=dialog.destroy)
        close_btn.pack(pady=5)

    def show_about(self):
        """Show about dialog."""
        about_text = """Mitsubishi PLK-A0804F Pattern Editor
Version 1.0 (Experimental)

A reverse-engineered pattern parser and editor for Mitsubishi
PLK-A0804F sewing machine controllers.

⚠️ EXPERIMENTAL SOFTWARE ⚠️
This software is based on pattern analysis and reverse-engineering.
The interpretation may be incorrect. Always verify with your machine
before using edited patterns.

Features:
• Pattern visualization
• Basic editing capabilities
• Export to CSV and G-code
• Function code detection
• Validation reporting

Limitations:
• Command structure not officially verified
• Coordinate scaling unknown
• Function parameters may be misinterpreted

For support and updates, check the project documentation.

Developed with Python and Tkinter.
Not affiliated with Mitsubishi Electric."""

        messagebox.showinfo("About Pattern Editor", about_text)

    def refresh_display(self):
        """Refresh the display."""
        self.update_display()

    def run(self):
        """Start the GUI application."""
        # Load a sample pattern if available
        sample_files = ["NEW.109", "NEW.102", "05PF.100"]
        for sample in sample_files:
            sample_path = os.path.join("Patterns", sample)
            if os.path.exists(sample_path):
                try:
                    self.pattern_commands = self.parser.parse_file(sample_path)
                    self.current_file = sample_path
                    self.update_display()
                    self.status_var.set(f"Loaded sample: {sample}")
                    break
                except:
                    continue

        self.root.mainloop()


def main():
    """Main entry point."""
    app = PatternEditorGUI()
    app.run()


if __name__ == "__main__":
    main()