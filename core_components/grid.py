from core_components.grid_availability import GridAvailability
from typing import Tuple

#TODO: Work on proper error handling for out of bounds and invalid coordinates

Vertex = Tuple[int, int]

class Grid:
    __width: int
    __height: int
    __obstacles: list[Vertex]
    
    def __init__(self, width, height, obstacles : list[Vertex]):
        self.__width = width
        self.__height = height
        self.__obstacles = obstacles
        self.__grid = [[GridAvailability.PASSABLE for _ in range(width)] for _ in range(height)]
        self._mark_obstacles()

    def get_dimensions(self) -> Tuple[int, int]:
        return self.__width, self.__height

    def _validate_position(self, position: Vertex) -> bool:
        x, y = position
        return 0 <= x < self.__width and 0 <= y < self.__height

    def _mark_obstacles(self):
        """
        Marks the obstacles on the grid based on the provided list of coordinates.
        """
        for x, y in self.__obstacles:
            if self._validate_position((x, y)):
                self.__grid[y][x] = GridAvailability.OBSTACLE

    def mark_taken(self, position : Vertex):
        """
        Marks a cell as taken (occupied) on the grid.
        """
        if self._validate_position(position) and not self.is_obstacle(position):
            x, y = position
            self.__grid[y][x] = GridAvailability.TAKEN

    def unmark_taken(self, position : Vertex):
        """
        Unmarks a cell as taken (occupied) on the grid, making it passable again.
        """
        if self._validate_position(position) and self.is_taken(position):
            x, y = position
            self.__grid[y][x] = GridAvailability.PASSABLE

    def is_passable(self, position : Vertex) -> bool:
        """
        Returns True if a cell is empty and within the grid boundaries, otherwise returns False
        """
        if self._validate_position(position):
            x, y = position
            return self.__grid[y][x] == GridAvailability.PASSABLE
        return False

    def is_taken(self, position : Vertex) -> bool:
        """
        Returns True if a cell is taken (occupied) and within the grid boundaries, otherwise returns False
        """
        if self._validate_position(position):
            x, y = position
            return self.__grid[y][x] == GridAvailability.TAKEN
        return False

    def is_obstacle(self, position : Vertex) -> bool:
        """
        Returns True if a cell is an obstacle and within the grid boundaries, otherwise returns False
        """
        if self._validate_position(position):
            x, y = position
            return self.__grid[y][x] == GridAvailability.OBSTACLE
        return False

    def get_neighbors(self, position : Vertex) -> list[Vertex]:
        """
        Returns valid adjacent cells (up/down/left/right)
        """
        x, y = position
        neighbors = []
        for dx, dy in [(-1, 0), (0, 1), (0, -1), (1, 0)]:
            new_x, new_y = x + dx, y + dy
            if self._validate_position((new_x, new_y)):
                neighbors.append((new_x, new_y))
        return neighbors
    
    def get_grid_state(self):
        """
        Returns the current state of the grid as a 2D list of GridAvailability values.
        """
        return self.__grid

    def print_grid(self):
        """
        Prints the grid to the console for visualization.
        """
        for row in self.__grid:
            print(' '.join(cell.name[0] for cell in row))
