import tkinter as tk
from typing import Optional
from core_components.grid import Grid, Vertex
from simulation_engine.step_snapshot import StepSnapshot

class GridCanvas(tk.Canvas):
    """
    Custom Canvas widget for rendering grid state.

    Color coding:
    - Black:     obstacles
    - Red:       attackers (A)
    - Blue:      defenders (D)
    - Light gray: empty targets (o)
    - Dark red:  captured targets (!)
    - Green:     protected targets (*)
    - Orange outline: bottleneck vertices
    """

    CELL_SIZE = 48

    COLOR_PASSABLE        = "#FFFFFF"
    COLOR_OBSTACLE        = "#1A1A1A"
    COLOR_ATTACKER        = "#E03A3A"
    COLOR_DEFENDER        = "#3A6BE0"
    COLOR_TARGET_EMPTY    = "#C8C8C8"
    COLOR_TARGET_CAPTURED = "#7A0000"
    COLOR_TARGET_PROTECTED= "#1A8A1A"
    COLOR_BORDER          = "#555555"
    COLOR_BOTTLENECK      = "#FFAA00"

    def __init__(self, parent, grid: Grid, **kwargs):
        super().__init__(parent, bg="#F0F0F0", **kwargs)
        self.set_grid(grid)

    def set_grid(self, grid: Grid):
        """Replace the grid (called when a new scenario is loaded)."""
        self.grid = grid
        self.width_cells, self.height_cells = grid.get_dimensions()
        canvas_w = self.width_cells  * self.CELL_SIZE + 2
        canvas_h = self.height_cells * self.CELL_SIZE + 2
        self.config(width=canvas_w, height=canvas_h)
        self.current_snapshot: Optional[StepSnapshot] = None
        self.delete("all")

    def update_snapshot(self, snapshot: StepSnapshot):
        self.current_snapshot = snapshot
        self.delete("all")
        self._draw_grid()

    # -------------------- DRAWING METHODS --------------------

    def _draw_grid(self):
        if not self.current_snapshot:
            return
        for y in range(self.height_cells):
            for x in range(self.width_cells):
                self._draw_cell(x, y)

        for t in self.current_snapshot.captured_targets:
            self._draw_target(t, self.COLOR_TARGET_CAPTURED, "!")
        for t in self.current_snapshot.protected_targets:
            self._draw_target(t, self.COLOR_TARGET_PROTECTED, "★")
        for t in self.current_snapshot.empty_targets:
            self._draw_target(t, self.COLOR_TARGET_EMPTY, "o")

        for b in self.current_snapshot.bottleneck_vertices:
            self._draw_bottleneck_marker(b)

        for s in self.current_snapshot.defenders:
            self._draw_agent(s.position, self.COLOR_DEFENDER, "D")
        for s in self.current_snapshot.attackers:
            self._draw_agent(s.position, self.COLOR_ATTACKER, "A")

    def _cell_rect(self, x, y):
        x0 = x * self.CELL_SIZE + 1
        y0 = y * self.CELL_SIZE + 1
        return x0, y0, x0 + self.CELL_SIZE, y0 + self.CELL_SIZE

    def _draw_cell(self, x, y):
        x0, y0, x1, y1 = self._cell_rect(x, y)
        fill = self.COLOR_OBSTACLE if self.grid.is_obstacle((x, y)) else self.COLOR_PASSABLE
        self.create_rectangle(x0, y0, x1, y1, fill=fill, outline=self.COLOR_BORDER, width=1)

    def _draw_target(self, pos: Vertex, color: str, label: str):
        x0, y0, x1, y1 = self._cell_rect(*pos)
        self.create_rectangle(x0, y0, x1, y1, fill=color, outline=self.COLOR_BORDER, width=1)
        if label:
            self.create_text(
                (x0+x1)/2, (y0+y1)/2,
                text=label, font=("Helvetica", 13, "bold"), fill="white"
            )

    def _draw_agent(self, pos: Vertex, color: str, label: str):
        x0, y0, x1, y1 = self._cell_rect(*pos)
        r = self.CELL_SIZE / 2 - 5
        cx, cy = (x0+x1)/2, (y0+y1)/2
        self.create_oval(cx-r, cy-r, cx+r, cy+r, fill=color, outline="#000000", width=2)
        self.create_text(cx, cy, text=label, font=("Helvetica", 11, "bold"), fill="white")

    def _draw_bottleneck_marker(self, pos: Vertex):
        x0, y0, x1, y1 = self._cell_rect(*pos)
        self.create_rectangle(x0+2, y0+2, x1-2, y1-2,
                               fill="", outline=self.COLOR_BOTTLENECK, width=3)