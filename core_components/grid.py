from core_components.grid_availability import GridAvailability
from typing import Tuple

#TODO: Work on proper error handling for out of bounds and invalid coordinates

Vertex = Tuple[int, int]

class Grid:
    def __init__(self, width, height, obstacles : list[Vertex]):
        self.width = width
        self.height = height
        self.obstacles = obstacles
        self.grid = [[GridAvailability.PASSABLE for _ in range(width)] for _ in range(height)]
        self.mark_obstacles()

    def mark_obstacles(self):
        """
        Marks the obstacles on the grid based on the provided list of coordinates.
        """
        for x, y in self.obstacles:
            if 0 <= x < self.width and 0 <= y < self.height:
                self.grid[y][x] = GridAvailability.OBSTACLE

    def mark_taken(self, position : Vertex):
        """
        Marks a cell as taken (occupied) on the grid.
        """
        x, y = position
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y][x] = GridAvailability.TAKEN

    def is_passable(self, position : Vertex) -> bool:
        """
        Returns True if a cell is empty and within the grid boundaries, otherwise returns False
        """
        x, y = position
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x] == GridAvailability.PASSABLE
        return False

    def get_neighbors(self, position : Vertex) -> list[Vertex]:
        """
        Returns valid adjacent cells (up/down/left/right)
        """
        x, y = position
        neighbors = []
        for dx, dy in [(-1, 0), (0, 1), (0, -1), (1, 0)]:
            new_x, new_y = x + dx, y + dy
            if 0 <= new_x < self.width and 0 <= new_y < self.height:
                neighbors.append((new_x, new_y))
        return neighbors
    
    def get_grid_state(self):
        """
        Returns the current state of the grid as a 2D list of GridAvailability values.
        """
        return self.grid
