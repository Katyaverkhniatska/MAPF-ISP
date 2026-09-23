import unittest
from tests_unit.util_tests import make_attacker, make_defender
from unittest.mock import patch
from allocation_strategies.greedy_strategy import GreedyStrategy
from allocation_strategies.random_strategy import RandomStrategy
from allocation_strategies.bottleneck_strategy import BottleneckStrategy
from core_components.agent import Agent
from core_components.agent_type import AgentType
from core_components.grid import Grid
from pathfinding.path_finder import PathFinder


class TestPathFinder(unittest.TestCase):
    """Test suite for PathFinder A* algorithm"""

    def test_straight_path(self):
        """Simple path with no obstacles.
        The starting vertex must be the head of the path.
        The goal should be the tail of the path."""
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


class TestRandomStrategy(unittest.TestCase):
    
    def test_all_defenders_assigned(self):
        """Every defender gets a target"""
        grid = Grid(10, 10, obstacles=[])
        defenders = [make_defender(0, 0, grid=grid), make_defender(1, 0, grid=grid)]
        targets = [(5, 5), (6, 6), (7, 7)]
        attackers = []

        strategy = RandomStrategy()
        result = strategy.allocate(grid, defenders, targets, attackers)

        self.assertEqual(len(result), len(defenders))
        for defender in defenders:
            self.assertIn(defender, result)
            self.assertIn(result[defender], targets)

    def test_more_defenders_than_targets(self):
        """Defenders share targets when outnumbered"""
        grid = Grid(10, 10, obstacles=[])
        defenders = [make_defender(i, 0, grid=grid) for i in range(5)]
        targets = [(5, 5), (6, 6)]
        attackers = []

        strategy = RandomStrategy()
        result = strategy.allocate(grid, defenders, targets, attackers)

        self.assertEqual(len(result), 5)
        for defender in defenders:
            self.assertIn(result[defender], targets)

    def test_empty_defenders(self):
        """Returns empty dict when no defenders"""
        grid = Grid(10, 10, obstacles=[])
        strategy = RandomStrategy()
        result = strategy.allocate(grid, [], [(5, 5)], [])
        self.assertEqual(result, {})

    def test_empty_targets(self):
        """Raises an error when no targets"""
        grid = Grid(10, 10, obstacles=[])
        defenders = [make_defender(0, 0, grid=grid)]
        strategy = RandomStrategy()
        with self.assertRaises(ValueError):
            strategy.allocate(grid, defenders, [], [])


class TestGreedyStrategy(unittest.TestCase):

    def test_closest_target_assigned(self):
        """Each defender gets the nearest target"""
        grid = Grid(10, 10, obstacles=[])
        defender = make_defender(0, 0, grid=grid)
        targets = [(1, 0), (8, 8)]  # (1,0) is clearly closer
        
        strategy = GreedyStrategy()
        result = strategy.allocate(grid, [defender], targets, [])
        
        self.assertEqual(result[defender], (1, 0))

    def test_no_duplicate_assignments(self):
        """Two defenders don't get the same target when enough targets exist"""
        grid = Grid(10, 10, obstacles=[])
        defenders = [make_defender(0, 0, grid=grid), make_defender(9, 9, grid=grid)]
        targets = [(1, 0), (8, 9)]

        strategy = GreedyStrategy()
        result = strategy.allocate(grid, defenders, targets, [])

        assigned_targets = list(result.values())
        self.assertEqual(len(set(assigned_targets)), 2)  # Both targets unique

    def test_more_defenders_than_targets(self):
        """Extra defenders share the closest target"""
        grid = Grid(10, 10, obstacles=[])
        defenders = [make_defender(0, 0, grid=grid) for _ in range(3)]
        targets = [(1, 0)]

        strategy = GreedyStrategy()
        result = strategy.allocate(grid, defenders, targets, [])

        self.assertEqual(len(result), 3)
        for defender in defenders:
            self.assertEqual(result[defender], (1, 0))

    def test_empty_defenders(self):
        """Returns empty dict when no defenders"""
        grid = Grid(10, 10, obstacles=[])
        strategy = GreedyStrategy()
        result = strategy.allocate(grid, [], [(5, 5)], [])
        self.assertEqual(result, {})

    def test_empty_targets(self):
        """Raises an error when no targets"""
        grid = Grid(10, 10, obstacles=[])
        defenders = [make_defender(0, 0, grid=grid)]
        strategy = GreedyStrategy()
        with self.assertRaises(ValueError):
            strategy.allocate(grid, defenders, [], [])


class TestBottleneckStrategy(unittest.TestCase):

    # ------------------------------------------------------------------
    # Baseline cases (mirroring Algorithm 1 edge cases)
    # ------------------------------------------------------------------
    def test_empty_defenders(self):
        """Returns empty dict when no defenders are available."""
        grid = Grid(10, 10, obstacles=[])
        strategy = BottleneckStrategy()
        result = strategy.allocate(grid, [], [(5, 5)], [])
        self.assertEqual(result, {})

    def test_empty_targets(self):
        """Raises an error when no targets are given."""
        grid = Grid(10, 10, obstacles=[])
        defenders = [make_defender(0, 0, grid=grid)]
        strategy = BottleneckStrategy()
        with self.assertRaises(ValueError):
            strategy.allocate(grid, defenders, [], [])

    def test_no_attackers_falls_back_to_random_assignment(self):
        """
        With no attackers, no paths are simulated, 
        so defenders are randomly assigned to available targets.
        """
        grid = Grid(10, 10, obstacles=[])
        defenders = [make_defender(0, 0, grid=grid), make_defender(9, 9, grid=grid)]
        targets = [(1, 0), (8, 9)]

        strategy = BottleneckStrategy()
        result = strategy.allocate(grid, defenders, targets, [])

        self.assertEqual(len(result), 2)
        self.assertEqual(set(result.values()), set(targets))

    def test_leftover_random_assignment_has_no_duplicates_when_enough_targets(self):
        """Fallback random assignment spreads defenders across distinct targets."""
        grid = Grid(10, 10, obstacles=[])
        defenders = [make_defender(0, 0, grid=grid) for _ in range(3)]
        targets = [(1, 0), (2, 0), (3, 0)]

        strategy = BottleneckStrategy()
        result = strategy.allocate(grid, defenders, targets, [])

        assigned_targets = list(result.values())
        self.assertEqual(len(set(assigned_targets)), 3)

    # ------------------------------------------------------------------
    # Bottleneck-specific cases
    # ------------------------------------------------------------------
    def test_search_vicinity_finds_gap_between_isolated_obstacles(self):
        """
        Tests _search_vicinity gap detection between obstacles flanking (5, 4).
        Trajectory (5, 0) -> (5, 9) passes through (5, 4), which is recognized 
        as a bottleneck altering the path.
        """
        obstacles = [(4, 4), (6, 4)]
        grid = Grid(10, 10, obstacles=obstacles)
        strategy = BottleneckStrategy()
        path_finder = PathFinder(grid)

        attacker = make_attacker(5, 0, target=(5, 9), grid=grid)
        guessed_targets = {attacker: (5, 9)}
        original_paths = strategy._simulate_attacker_paths(
            grid, [attacker], guessed_targets, set(), path_finder
        )

        gap = strategy._search_vicinity(
            grid,
            w=(5, 4),
            forbidden=set(),
            attackers=[attacker],
            guessed_targets=guessed_targets,
            original_paths=original_paths,
            path_finder=path_finder,
        )

        self.assertEqual(gap, [(5, 4)])

    def test_forbidden_accumulates_across_iterations(self):
        """
        Verifies behavior where occupied bottlenecks are appended 
        to the forbidden set F, changing path calculations in subsequent iterations.
        """
        grid = Grid(10, 10, obstacles=[])
        defenders = [make_defender(0, 0, grid=grid), make_defender(1, 1, grid=grid)]
        attacker = make_attacker(0, 0, target=(9, 9), grid=grid)
        strategy = BottleneckStrategy()

        bottleneck_sequence = [[(5, 5)], [(6, 6)]]
        captured_forbidden = []

        def fake_search_vicinity(grid_arg, w, forbidden, *args, **kwargs):
            captured_forbidden.append(set(forbidden))
            return bottleneck_sequence.pop(0) if bottleneck_sequence else []

        with patch.object(
            strategy, "_simulate_attacker_paths", return_value=[[(5, 5)]]
        ), patch.object(
            strategy, "_search_vicinity", side_effect=fake_search_vicinity
        ):
            result = strategy.allocate(grid, defenders, [(9, 9)], [attacker])

        self.assertEqual(set(result.values()), {(5, 5), (6, 6)})
        self.assertEqual(captured_forbidden[0], set())
        self.assertEqual(captured_forbidden[1], {(5, 5)})

    # ------------------------------------------------------------------
    # Attacker-target guessing (delta_A^0)
    # ------------------------------------------------------------------
    def test_simulate_attacker_paths_uses_guessed_target_not_real_one(self):
        """Path simulation must route toward guessed target delta_A^0, not real target."""
        grid = Grid(10, 10, obstacles=[])
        attacker = make_attacker(0, 0, target=(9, 9), grid=grid)
        strategy = BottleneckStrategy()
        path_finder = PathFinder(grid)

        guessed_targets = {attacker: (3, 3)}  # Deliberately distinct from real target (9, 9)
        paths = strategy._simulate_attacker_paths(
            grid, [attacker], guessed_targets, forbidden=set(), path_finder=path_finder
        )

        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0][-1], (3, 3))
        self.assertNotEqual(paths[0][-1], (9, 9))

    def test_guess_attacker_targets_draws_from_target_list(self):
        """Guessed targets delta_A^0 must be sampled from the provided target set T."""
        grid = Grid(10, 10, obstacles=[])
        strategy = BottleneckStrategy()
        targets = [(1, 1), (2, 2), (3, 3)]
        attackers = [make_attacker(0, 0, target=(9, 9), grid=grid) for _ in range(20)]

        guesses = strategy._determine_attacker_targets(attackers, targets)

        self.assertEqual(set(guesses.keys()), set(attackers))
        for guessed in guesses.values():
            self.assertIn(guessed, targets)

    def test_guess_computed_once_across_iterations(self):
        """
        Algorithm 1 requirement: delta_A^0 is fixed once at initialization 
        and held constant while F accumulates across iterations.
        """
        grid = Grid(10, 10, obstacles=[])
        defenders = [make_defender(0, 0, grid=grid), make_defender(1, 1, grid=grid)]
        attacker = make_attacker(0, 0, target=(9, 9), grid=grid)
        strategy = BottleneckStrategy()

        bottleneck_sequence = [[(5, 5)], [(6, 6)]]

        def fake_search_vicinity(grid_arg, w, forbidden, *args, **kwargs):
            return bottleneck_sequence.pop(0) if bottleneck_sequence else []

        # Fixed patch target: _determine_attacker_targets instead of _guess_attacker_targets
        with patch.object(
            strategy, "_determine_attacker_targets", return_value={attacker: (9, 9)}
        ) as mock_guess, patch.object(
            strategy, "_search_vicinity", side_effect=fake_search_vicinity
        ):
            strategy.allocate(grid, defenders, [(9, 9)], [attacker])

        mock_guess.assert_called_once()

    def test_use_true_targets_flag_bypasses_guessing(self):
        """use_true_targets=True uses Agent.get_target() directly."""
        grid = Grid(10, 10, obstacles=[])
        attacker = make_attacker(0, 0, target=(9, 9), grid=grid)
        strategy = BottleneckStrategy(use_true_targets=True)

        determined = strategy._determine_attacker_targets([attacker], targets=[(1, 1)])

        self.assertEqual(determined, {attacker: (9, 9)})

    def test_use_true_targets_skips_attackers_without_target(self):
        """An attacker without a target set is excluded under use_true_targets=True."""
        grid = Grid(10, 10, obstacles=[])
        attacker = make_attacker(0, 0, target=None, grid=grid)
        strategy = BottleneckStrategy(use_true_targets=True)

        determined = strategy._determine_attacker_targets([attacker], targets=[(1, 1)])

        self.assertEqual(determined, {})

    def test_local_obstacle_components_finds_all_connected_clusters(self):
       """Verify that disconnected obstacle clusters are separate components."""
       grid = Grid(10, 10, obstacles=[
           (2, 2), (2, 3),  # Cluster 1 (8-connected)
           (8, 8), (8, 7)   # Cluster 2 (isolated)
       ])
       strategy = BottleneckStrategy()
       components = strategy._local_obstacle_components(
           grid, {(2,2), (2,3), (8,8), (8,7)}, w=(5,5), radius=10
       )
       self.assertEqual(len(components), 2)

    def test_vertex_frequency_counts_shared_path_vertices(self):
        """Two paths through same corridor should both count the corridor vertices."""
        grid = Grid(10, 10, obstacles=[(5, 0), (5, 9)])  # Walls top/bottom
        # We wanna check the simplest paths for these 2 attackers
        _ = [
            make_attacker(0, 5, target=(9, 5), grid=grid),
            make_attacker(0, 6, target=(9, 6), grid=grid)
        ]
        strategy = BottleneckStrategy()
        paths = [[(x, 5) for x in range(0, 10)], [(x, 6) for x in range(0, 10)]]
        freq = strategy._vertex_frequency(paths)
        self.assertEqual(freq.get((5, 5)), 1)  # First path only
        self.assertEqual(freq.get((5, 6)), 1)  # Second path only

        grid = Grid(10, 10, obstacles=[(5, 0), (5, 9)])
        _ = [
            make_attacker(0, 0, target=(9, 0), grid=grid),
            make_attacker(0, 1, target=(9, 1), grid=grid)
        ]

        pathfinder = PathFinder(grid)
        path_1 = pathfinder.find_path((0, 0), (9, 0))
        path_2 = pathfinder.find_path((0, 1), (9, 1))
        paths = []

        if not path_1:
            paths.append([])
        else:
            paths.append(path_1)
        if not path_2:
            paths.append([])
        else:
            paths.append(path_2)

        # Vertex (5, 1) must be visited twice
        freq = strategy._vertex_frequency(paths)
        self.assertEqual(freq.get((5, 1)), 2)

if __name__ == "__main__":
    unittest.main()