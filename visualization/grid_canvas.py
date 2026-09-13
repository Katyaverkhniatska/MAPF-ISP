import tkinter as tk
from typing import Optional
from core_components.grid import Grid, Vertex
from simulation_engine.step_snapshot import StepSnapshot


class GridCanvas(tk.Canvas):
    """
    Custom Canvas widget for rendering grid state.
    
    Renders obstacles, agents, and targets with color coding:
    - Black: obstacles
    - Red: attackers (A)
    - Blue: defenders (D)
    - White: empty targets
    - Dark red: captured targets (!)
    - Green: protected targets (*)
    """
    
    CELL_SIZE = 40  # pixels per grid cell
    
    COLOR_PASSABLE = "white"
    COLOR_OBSTACLE = "black"
    COLOR_ATTACKER = "#FF4444"          # bright red
    COLOR_DEFENDER = "#4444FF"          # bright blue
    COLOR_TARGET_EMPTY = "#CCCCCC"      # light gray
    COLOR_TARGET_CAPTURED = "#990000"   # dark red
    COLOR_TARGET_PROTECTED = "#00AA00"  # green
    COLOR_BORDER = "#333333"
    COLOR_BOTTLENECK = "#FFAA00"        # orange highlight
    
    def __init__(self, parent, grid: Grid, **kwargs):
        super().__init__(parent, bg="white", **kwargs)
        self.grid = grid
        self.current_snapshot: Optional[StepSnapshot] = None
        self.width_cells, self.height_cells = grid.get_dimensions()
        
        # Configure canvas size based on grid
        canvas_width = self.width_cells * self.CELL_SIZE + 2
        canvas_height = self.height_cells * self.CELL_SIZE + 2
        self.config(width=canvas_width, height=canvas_height)
        self.bind("<Configure>", self._on_resize)
    
    def update_snapshot(self, snapshot: StepSnapshot):
        """Update canvas to render a new snapshot."""
        self.current_snapshot = snapshot
        self.delete("all")
        self._draw_grid()
    
    def _draw_grid(self):
        """Draw the complete grid state."""
        if not self.current_snapshot:
            return
        
        # Draw grid background and cells
        for y in range(self.height_cells):
            for x in range(self.width_cells):
                self._draw_cell(x, y)
        
        # Draw targets (so they appear behind agents)
        for target in self.current_snapshot.captured_targets:
            self._draw_target(target, self.COLOR_TARGET_CAPTURED, "!")
        for target in self.current_snapshot.protected_targets:
            self._draw_target(target, self.COLOR_TARGET_PROTECTED, "*")
        for target in self.current_snapshot.empty_targets:
            self._draw_target(target, self.COLOR_TARGET_EMPTY, "")
        
        # Draw bottleneck vertices (faint highlight)
        for bottleneck in self.current_snapshot.bottleneck_vertices:
            self._draw_bottleneck_marker(bottleneck)
        
        # Draw agents
        for agent_snap in self.current_snapshot.defenders:
            self._draw_agent(agent_snap.position, self.COLOR_DEFENDER, "D")
        for agent_snap in self.current_snapshot.attackers:
            self._draw_agent(agent_snap.position, self.COLOR_ATTACKER, "A")
    
    def _draw_cell(self, x: int, y: int):
        """Draw a single grid cell with border."""
        x0 = x * self.CELL_SIZE + 1
        y0 = y * self.CELL_SIZE + 1
        x1 = x0 + self.CELL_SIZE
        y1 = y0 + self.CELL_SIZE
        
        # Determine cell color based on grid state
        if self.grid.is_obstacle((x, y)):
            fill_color = self.COLOR_OBSTACLE
        else:
            fill_color = self.COLOR_PASSABLE
        
        self.create_rectangle(
            x0, y0, x1, y1,
            fill=fill_color,
            outline=self.COLOR_BORDER,
            width=1
        )
    
    def _draw_target(self, position: Vertex, color: str, label: str):
        """Draw a target with optional label."""
        x, y = position
        x0 = x * self.CELL_SIZE + 1
        y0 = y * self.CELL_SIZE + 1
        x1 = x0 + self.CELL_SIZE
        y1 = y0 + self.CELL_SIZE
        
        self.create_rectangle(
            x0, y0, x1, y1,
            fill=color,
            outline=self.COLOR_BORDER,
            width=1
        )
        
        if label:
            cx = (x0 + x1) / 2
            cy = (y0 + y1) / 2
            self.create_text(
                cx, cy,
                text=label,
                font=("Courier", 10, "bold"),
                fill="white"
            )
    
    def _draw_agent(self, position: Vertex, color: str, label: str):
        """Draw an agent (circle with label)."""
        x, y = position
        x0 = x * self.CELL_SIZE + 1
        y0 = y * self.CELL_SIZE + 1
        x1 = x0 + self.CELL_SIZE
        y1 = y0 + self.CELL_SIZE
        
        # Draw circle (filled oval)
        radius = self.CELL_SIZE / 2 - 4
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        
        self.create_oval(
            cx - radius, cy - radius,
            cx + radius, cy + radius,
            fill=color,
            outline="black",
            width=2
        )
        
        # Draw label
        self.create_text(
            cx, cy,
            text=label,
            font=("Courier", 8, "bold"),
            fill="white"
        )
    
    def _draw_bottleneck_marker(self, position: Vertex):
        """Draw a subtle orange outline around a bottleneck vertex."""
        x, y = position
        x0 = x * self.CELL_SIZE + 1
        y0 = y * self.CELL_SIZE + 1
        x1 = x0 + self.CELL_SIZE
        y1 = y0 + self.CELL_SIZE
        
        self.create_rectangle(
            x0, y0, x1, y1,
            fill="",
            outline=self.COLOR_BOTTLENECK,
            width=3
        )
    
    def _on_resize(self, event):
        """Handle canvas resize (not scaling grid, just space)."""
        pass