import unittest
from tests.util_tests import make_attacker, make_defender
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


class TestRandomStrategy(unittest.TestCase):
    
    def test_all_defenders_assigned(self):
        """Every defender gets a target"""
        grid = Grid(10, 10, obstacles=[])
        defenders = [make_defender(0, 0), make_defender(1, 0)]
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
        defenders = [make_defender(i, 0) for i in range(5)]
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
        """Returns empty dict when no targets"""
        grid = Grid(10, 10, obstacles=[])
        defenders = [make_defender(0, 0)]
        strategy = RandomStrategy()
        result = strategy.allocate(grid, defenders, [], [])
        self.assertEqual(result, {})


class TestGreedyStrategy(unittest.TestCase):

    def test_closest_target_assigned(self):
        """Each defender gets the nearest target"""
        grid = Grid(10, 10, obstacles=[])
        defender = make_defender(0, 0)
        targets = [(1, 0), (8, 8)]  # (1,0) is clearly closer
        
        strategy = GreedyStrategy()
        result = strategy.allocate(grid, [defender], targets, [])
        
        self.assertEqual(result[defender], (1, 0))

    def test_no_duplicate_assignments(self):
        """Two defenders don't get the same target when enough targets exist"""
        grid = Grid(10, 10, obstacles=[])
        defenders = [make_defender(0, 0), make_defender(9, 9)]
        targets = [(1, 0), (8, 9)]

        strategy = GreedyStrategy()
        result = strategy.allocate(grid, defenders, targets, [])

        assigned_targets = list(result.values())
        self.assertEqual(len(set(assigned_targets)), 2)  # Both targets unique

    def test_more_defenders_than_targets(self):
        """Extra defenders share the closest target"""
        grid = Grid(10, 10, obstacles=[])
        defenders = [make_defender(0, 0) for _ in range(3)]
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
        """Returns empty dict when no targets"""
        grid = Grid(10, 10, obstacles=[])
        defenders = [make_defender(0, 0)]
        strategy = GreedyStrategy()
        result = strategy.allocate(grid, defenders, [], [])
        self.assertEqual(result, {})



class TestBottleneckStrategy(unittest.TestCase):
 
    # ------------------------------------------------------------------
    # Baseline cases (mirroring TestGreedyStrategy)
    # ------------------------------------------------------------------
    def test_empty_defenders(self):
        """Returns empty dict when no defenders"""
        grid = Grid(10, 10, obstacles=[])
        strategy = BottleneckStrategy()
        result = strategy.allocate(grid, [], [(5, 5)], [])
        self.assertEqual(result, {})
 
    def test_empty_targets(self):
        """Returns empty dict when no targets and no attackers"""
        grid = Grid(10, 10, obstacles=[])
        defenders = [make_defender(0, 0)]
        strategy = BottleneckStrategy()
        result = strategy.allocate(grid, defenders, [], [])
        self.assertEqual(result, {})
 
    def test_no_attackers_falls_back_to_random_assignment(self):
        """With no attackers there are no paths to simulate, so the loop
        breaks immediately and defenders fall back to random targets."""
        grid = Grid(10, 10, obstacles=[])
        defenders = [make_defender(0, 0), make_defender(9, 9)]
        targets = [(1, 0), (8, 9)]
 
        strategy = BottleneckStrategy()
        result = strategy.allocate(grid, defenders, targets, [])
 
        self.assertEqual(len(result), 2)
        self.assertEqual(set(result.values()), set(targets))
 
    def test_leftover_random_assignment_has_no_duplicates_when_enough_targets(self):
        """Fallback random assignment should spread defenders across
        distinct targets rather than sampling the same one twice."""
        grid = Grid(10, 10, obstacles=[])
        defenders = [make_defender(0, 0) for _ in range(3)]
        targets = [(1, 0), (2, 0), (3, 0)]
 
        strategy = BottleneckStrategy()
        result = strategy.allocate(grid, defenders, targets, [])
 
        assigned_targets = list(result.values())
        self.assertEqual(len(set(assigned_targets)), 3)
 
    # ------------------------------------------------------------------
    # Bottleneck-specific cases
    # ------------------------------------------------------------------
    def test_search_vicinity_finds_gap_between_isolated_obstacles(self):
        """Direct unit test of _search_vicinity/_shortest_gap_between_components:
        two single-cell obstacles flanking a passable vertex, with nothing
        else nearby, should be recognized as two components with the gap
        vertex itself as the shortest connecting path. Using a minimal,
        unambiguous obstacle layout avoids the false-bottleneck / component-
        ordering pitfalls a larger wall layout can trigger (see below)."""
        obstacles = [(4, 4), (6, 4)]
        grid = Grid(10, 10, obstacles=obstacles)
        strategy = BottleneckStrategy()
 
        gap = strategy._search_vicinity(grid, (5, 4), forbidden=set())
 
        self.assertEqual(gap, [(5, 4)])
 
    def test_forbidden_accumulates_across_iterations(self):
        """Once a bottleneck is blocked, its vertices must be added to the
        forbidden set passed into the next vicinity search, and a second
        defender should be assigned to whatever bottleneck is found next.
 
        We mock _simulate_attacker_paths/_search_vicinity to control the
        sequence deterministically, rather than relying on real pathfinding
        geometry (which is sensitive to the false-bottleneck / component-
        ordering behavior demonstrated above).
        """
        grid = Grid(10, 10, obstacles=[])
        defenders = [make_defender(0, 0), make_defender(1, 1)]
        attacker = make_attacker(0, 0, target=(9, 9))
        strategy = BottleneckStrategy()
 
        bottleneck_sequence = [[(5, 5)], [(6, 6)]]
        captured_forbidden = []
 
        def fake_search_vicinity(grid_arg, w, forbidden):
            captured_forbidden.append(set(forbidden))
            return bottleneck_sequence.pop(0) if bottleneck_sequence else []
 
        with patch.object(strategy, "_simulate_attacker_paths", return_value=[[(5, 5)]]), \
                patch.object(strategy, "_search_vicinity", side_effect=fake_search_vicinity):
            result = strategy.allocate(grid, defenders, [(9, 9)], [attacker])
 
        self.assertEqual(set(result.values()), {(5, 5), (6, 6)})
        self.assertEqual(captured_forbidden[0], set())
        self.assertEqual(captured_forbidden[1], {(5, 5)})
 
    def test_tie_broken_by_distance_to_defenders(self):
        """When two vertices tie for max frequency, the one closer to the
        (approximate) defender location should be selected."""
        strategy = BottleneckStrategy()
        frequency = {(0, 0): 3, (9, 9): 3, (4, 4): 1}
        defenders = [Agent(1, 1, AgentType.DEFENDER)]
 
        selected = strategy._select_frequent_vertex(frequency, defenders)
 
        self.assertEqual(selected, (0, 0))
 
    def test_single_max_frequency_vertex_selected_without_tie(self):
        """When there's a unique max-frequency vertex, distance to
        defenders should not matter."""
        strategy = BottleneckStrategy()
        frequency = {(0, 0): 1, (9, 9): 5}
        defenders = [Agent(0, 0, AgentType.DEFENDER)]  # closer to (0,0), but (9,9) still wins
 
        selected = strategy._select_frequent_vertex(frequency, defenders)
 
        self.assertEqual(selected, (9, 9))
 
    def test_partial_block_when_fewer_defenders_than_bottleneck_size(self):
        """If fewer defenders remain than the bottleneck needs, only a
        matching-length prefix of the bottleneck's vertices should be
        claimed. Mocked for determinism, same reasoning as above."""
        grid = Grid(10, 10, obstacles=[])
        defender = make_defender(0, 0)  # only one defender available
        attacker = make_attacker(0, 0, target=(9, 9))
        strategy = BottleneckStrategy()
 
        with patch.object(strategy, "_simulate_attacker_paths", return_value=[[(5, 5)]]), \
                patch.object(strategy, "_search_vicinity", return_value=[(5, 5), (6, 5)]):
            result = strategy.allocate(grid, [defender], [(9, 9)], [attacker])
 
        # Only the first vertex of the 2-vertex bottleneck gets claimed.
        self.assertEqual(result, {defender: (5, 5)})

    # ------------------------------------------------------------------
    # Attacker-target guessing (delta^0_A)
    # ------------------------------------------------------------------
    def test_simulate_attacker_paths_uses_guessed_target_not_real_one(self):
        """Regression test: path simulation must route toward the provided
        guess, not the attacker's real known target -- this is precisely
        the bug that made Bottleneck degenerate into Random before
        Agent.get_target() and the guessing step existed."""
        grid = Grid(10, 10, obstacles=[])
        attacker = make_attacker(0, 0, target=(9, 9))
        strategy = BottleneckStrategy()
        path_finder = PathFinder(grid)

        guessed_targets = {attacker: (3, 3)}  # deliberately not (9, 9)
        paths = strategy._simulate_attacker_paths(
            grid, [attacker], guessed_targets, forbidden=set(), path_finder=path_finder
        )

        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0][-1], (3, 3))
        self.assertNotEqual(paths[0][-1], (9, 9))

    def test_guess_attacker_targets_draws_from_target_list(self):
        """Every guessed target must be one of the actual targets given,
        for every attacker -- sampling is with replacement, so repeats
        across attackers are fine."""
        strategy = BottleneckStrategy()
        targets = [(1, 1), (2, 2), (3, 3)]
        attackers = [make_attacker(0, 0, target=(9, 9)) for _ in range(20)]

        guesses = strategy._guess_attacker_targets(attackers, targets)

        self.assertEqual(set(guesses.keys()), set(attackers))
        for guessed in guesses.values():
            self.assertIn(guessed, targets)

    def test_guess_attacker_targets_with_no_targets_returns_empty(self):
        """No targets to guess from -> no crash, just an empty mapping."""
        strategy = BottleneckStrategy()
        attacker = make_attacker(0, 0, target=(9, 9))

        self.assertEqual(strategy._guess_attacker_targets([attacker], []), {})

    def test_guess_computed_once_across_iterations(self):
        """delta^0_A must be fixed for the whole allocate() call -- only
        the *paths* toward it should change as bottlenecks accumulate in
        `forbidden`, per Algorithm 1. If this guess were re-rolled every
        iteration, blocking one bottleneck could make a previously-found
        one vanish for no structural reason."""
        grid = Grid(10, 10, obstacles=[])
        defenders = [make_defender(0, 0), make_defender(1, 1)]
        attacker = make_attacker(0, 0, target=(9, 9))
        strategy = BottleneckStrategy()

        bottleneck_sequence = [[(5, 5)], [(6, 6)]]

        def fake_search_vicinity(grid_arg, w, forbidden):
            return bottleneck_sequence.pop(0) if bottleneck_sequence else []

        with patch.object(
            strategy, "_guess_attacker_targets", return_value={attacker: (9, 9)}
        ) as mock_guess, patch.object(
            strategy, "_search_vicinity", side_effect=fake_search_vicinity
        ):
            strategy.allocate(grid, defenders, [(9, 9)], [attacker])

        mock_guess.assert_called_once()

    def test_use_true_targets_flag_bypasses_guessing(self):
        """use_true_targets=True is the idealized-baseline mode: it should
        use Agent.get_target() directly, ignoring the target list entirely
        -- proven here by giving a target list that doesn't even contain
        the attacker's real target."""
        attacker = make_attacker(0, 0, target=(9, 9))
        strategy = BottleneckStrategy(use_true_targets=True)

        determined = strategy._determine_attacker_targets([attacker], targets=[(1, 1)])

        self.assertEqual(determined, {attacker: (9, 9)})

    def test_use_true_targets_skips_attackers_without_target(self):
        """An attacker with no target set (get_target() is None) should be
        excluded, matching the old goal-is-None skip behavior."""
        attacker = make_attacker(0, 0, target=None)  # target never set
        strategy = BottleneckStrategy(use_true_targets=True)

        determined = strategy._determine_attacker_targets([attacker], targets=[(1, 1)])

        self.assertEqual(determined, {})

if __name__ == "__main__":
    unittest.main()