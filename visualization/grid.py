from visualization.grid_availability import GridAvailability

#TODO: Work on proper error handling for out of bounds and invalid coordinates

class Grid:
    def __init__(self, width, height, obstacles : list[tuple[int, int]]):
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

    def mark_taken(self, position : tuple[int, int]):
        """
        Marks a cell as taken (occupied) on the grid.
        """
        x, y = position
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y][x] = GridAvailability.TAKEN

    def is_passable(self, position : tuple[int, int]) -> bool:
        """
        Returns True if a cell is empty and within the grid boundaries, otherwise returns False
        """
        x, y = position
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x] == GridAvailability.PASSABLE
        return False

    def get_neighbors(self, position : tuple[int, int]) -> list[tuple[int, int]]:
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
