from pathfinding.a_star import AStar
from typing import Optional, List, Tuple

class PathFinder:
    def __init__(self, grid):
        self.grid = grid

    def find_path(self, start: Tuple[int, int], goal: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        """
        Find a path from start to goal using A* algorithm.
        
        Returns:
            List of (x, y) coordinates representing the path, or None if no path exists.
            
        Raises:
            ValueError: If start or goal is invalid (out of bounds or blocked).
        """
        pathfinder = AStar(start, goal, self.grid)
        return pathfinder.find_path()