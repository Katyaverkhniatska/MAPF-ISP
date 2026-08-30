import unittest
from unittest.mock import patch
from allocation_strategies.greedy_strategy import GreedyStrategy
from allocation_strategies.random_strategy import RandomStrategy
from allocation_strategies.bottleneck_strategy import BottleneckStrategy
from core_components.agent import Agent
from core_components.agent_type import AgentType
from core_components.grid import Grid
from pathfinding.path_finder import PathFinder

def make_attacker(x, y, target):
    """Helper: build an attacker and attach its known target.
 
    The strategy reads `attacker.target` via getattr(), so we just set the
    attribute directly rather than assuming a particular constructor shape.
    """
    attacker = Agent(x, y, AgentType.ATTACKER)
    attacker.set_target(target)
    return attacker

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
        defenders = [Agent(0, 0, AgentType.DEFENDER), Agent(1, 0, AgentType.DEFENDER)]
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
        defenders = [Agent(i, 0, AgentType.DEFENDER) for i in range(5)]
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
        defenders = [Agent(0, 0, AgentType.DEFENDER)]
        strategy = RandomStrategy()
        result = strategy.allocate(grid, defenders, [], [])
        self.assertEqual(result, {})


class TestGreedyStrategy(unittest.TestCase):

    def test_closest_target_assigned(self):
        """Each defender gets the nearest target"""
        grid = Grid(10, 10, obstacles=[])
        defender = Agent(0, 0, AgentType.DEFENDER)
        targets = [(1, 0), (8, 8)]  # (1,0) is clearly closer
        
        strategy = GreedyStrategy()
        result = strategy.allocate(grid, [defender], targets, [])
        
        self.assertEqual(result[defender], (1, 0))

    def test_no_duplicate_assignments(self):
        """Two defenders don't get the same target when enough targets exist"""
        grid = Grid(10, 10, obstacles=[])
        defenders = [Agent(0, 0, AgentType.DEFENDER), Agent(9, 9, AgentType.DEFENDER)]
        targets = [(1, 0), (8, 9)]

        strategy = GreedyStrategy()
        result = strategy.allocate(grid, defenders, targets, [])

        assigned_targets = list(result.values())
        self.assertEqual(len(set(assigned_targets)), 2)  # Both targets unique

    def test_more_defenders_than_targets(self):
        """Extra defenders share the closest target"""
        grid = Grid(10, 10, obstacles=[])
        defenders = [Agent(0, 0, AgentType.DEFENDER) for _ in range(3)]
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
        defenders = [Agent(0, 0, AgentType.DEFENDER)]
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
        defenders = [Agent(0, 0, AgentType.DEFENDER)]
        strategy = BottleneckStrategy()
        result = strategy.allocate(grid, defenders, [], [])
        self.assertEqual(result, {})
 
    def test_no_attackers_falls_back_to_random_assignment(self):
        """With no attackers there are no paths to simulate, so the loop
        breaks immediately and defenders fall back to random targets."""
        grid = Grid(10, 10, obstacles=[])
        defenders = [Agent(0, 0, AgentType.DEFENDER), Agent(9, 9, AgentType.DEFENDER)]
        targets = [(1, 0), (8, 9)]
 
        strategy = BottleneckStrategy()
        result = strategy.allocate(grid, defenders, targets, [])
 
        self.assertEqual(len(result), 2)
        self.assertEqual(set(result.values()), set(targets))
 
    def test_leftover_random_assignment_has_no_duplicates_when_enough_targets(self):
        """Fallback random assignment should spread defenders across
        distinct targets rather than sampling the same one twice."""
        grid = Grid(10, 10, obstacles=[])
        defenders = [Agent(0, 0, AgentType.DEFENDER) for _ in range(3)]
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
        defenders = [Agent(0, 0, AgentType.DEFENDER), Agent(1, 1, AgentType.DEFENDER)]
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
 
    def test_no_bottleneck_in_open_field_uses_random_fallback(self):
        """With no obstacles, searchVicinity never finds more than one
        connected component, so defenders should fall back to random
        target assignment instead of being stuck unassigned."""
        grid = Grid(10, 10, obstacles=[])
        attacker = make_attacker(0, 0, target=(9, 9))
        defender = Agent(0, 9, AgentType.DEFENDER)
 
        strategy = BottleneckStrategy()
        result = strategy.allocate(grid, [defender], [(9, 9)], [attacker])
 
        self.assertEqual(result[defender], (9, 9))
 
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
        defender = Agent(0, 0, AgentType.DEFENDER)  # only one defender available
        attacker = make_attacker(0, 0, target=(9, 9))
        strategy = BottleneckStrategy()
 
        with patch.object(strategy, "_simulate_attacker_paths", return_value=[[(5, 5)]]), \
                patch.object(strategy, "_search_vicinity", return_value=[(5, 5), (6, 5)]):
            result = strategy.allocate(grid, [defender], [(9, 9)], [attacker])
 
        # Only the first vertex of the 2-vertex bottleneck gets claimed.
        self.assertEqual(result, {defender: (5, 5)})

if __name__ == "__main__":
    unittest.main()