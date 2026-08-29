import unittest
from core_components.grid import Grid
from pathfinding.path_finder import PathFinder


class TestPathFinder(unittest.TestCase):
    """Test suite for PathFinder A* algorithm"""

    def test_straight_path(self):
        """Simple path with no obstacles"""
        grid = Grid(10, 10, obstacles=[])
        pathfinder = PathFinder(grid)
        path = pathfinder.find_path((0, 0), (3, 0))
        self.assertIsNotNone(path)
        assert path is not None
        self.assertGreater(len(path), 0)
        self.assertEqual(path[0], (0, 0))
        self.assertEqual(path[-1], (3, 0))

    def test_path_with_obstacles(self):
        """Path that must navigate around an obstacle"""
        grid = Grid(5, 5, obstacles=[(1, 1), (1, 2), (1, 3)])
        pathfinder = PathFinder(grid)
        path = pathfinder.find_path((0, 2), (4, 2))
        self.assertIsNotNone(path)
        assert path is not None
        self.assertNotIn((1, 1), path)
        self.assertNotIn((1, 2), path)
        self.assertNotIn((1, 3), path)

    def test_no_path_exists(self):
        """Start and goal separated by obstacles (no solution)"""
        grid = Grid(5, 5, obstacles=[(1, 0), (1, 1), (1, 2), (1, 3), (1, 4)])
        pathfinder = PathFinder(grid)
        path = pathfinder.find_path((0, 2), (4, 2))
        self.assertIsNone(path)

    def test_start_equals_goal(self):
        """Start and goal are the same"""
        grid = Grid(10, 10, obstacles=[])
        pathfinder = PathFinder(grid)
        path = pathfinder.find_path((5, 5), (5, 5))
        self.assertIsNotNone(path)
        assert path is not None
        self.assertEqual(len(path), 1)
        self.assertEqual(path[0], (5, 5))

    def test_adjacent_cells(self):
        """Goal is one step away"""
        grid = Grid(10, 10, obstacles=[])
        pathfinder = PathFinder(grid)
        path = pathfinder.find_path((0, 0), (1, 0))
        self.assertIsNotNone(path)
        assert path is not None
        self.assertEqual(len(path), 2)
        self.assertEqual(path, [(0, 0), (1, 0)])

    def test_diagonal_distance(self):
        """Verify path takes efficient route"""
        grid = Grid(10, 10, obstacles=[])
        pathfinder = PathFinder(grid)
        path = pathfinder.find_path((0, 0), (5, 5))
        self.assertIsNotNone(path)
        assert path is not None
        self.assertLessEqual(len(path), 11)

    def test_goal_is_obstacle(self):
        """Goal position is blocked by obstacle - raises ValueError"""
        grid = Grid(5, 5, obstacles=[(2, 2)])
        pathfinder = PathFinder(grid)
        with self.assertRaises(ValueError):
            pathfinder.find_path((0, 0), (2, 2))

    def test_start_is_obstacle(self):
        """Start position is blocked - raises ValueError"""
        grid = Grid(5, 5, obstacles=[(0, 0)])
        pathfinder = PathFinder(grid)
        with self.assertRaises(ValueError):
            pathfinder.find_path((0, 0), (3, 3))

    def test_start_out_of_bounds(self):
        """Start position is out of bounds - raises ValueError"""
        grid = Grid(5, 5, obstacles=[])
        pathfinder = PathFinder(grid)
        with self.assertRaises(ValueError):
            pathfinder.find_path((10, 10), (2, 2))

    def test_goal_out_of_bounds(self):
        """Goal position is out of bounds - raises ValueError"""
        grid = Grid(5, 5, obstacles=[])
        pathfinder = PathFinder(grid)
        with self.assertRaises(ValueError):
            pathfinder.find_path((2, 2), (10, 10))


if __name__ == "__main__":
    unittest.main()