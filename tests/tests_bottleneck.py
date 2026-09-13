"""
Deterministic Map Tests for BottleneckStrategy.

These tests use hand-designed grid layouts where the expected bottleneck(s)
can be reasoned about manually, allowing us to verify that allocate() finds
the correct (or at least defensible) defender positions.

Pattern:
  1. Define a grid layout as ASCII art (# = obstacle, space = passable, A/D = agent start, T = target)
  2. Manually identify the bottleneck(s) — the gap(s) between obstacle groups through which attackers must pass
  3. Set up agents and targets matching the diagram
  4. Call strategy.allocate()
  5. Assert that returned defenders are assigned to the identified bottleneck vertex/vertices
"""

import unittest
from core_components.agent import Agent
from core_components.agent_type import AgentType
from core_components.grid import Grid, Vertex
from allocation_strategies.bottleneck_strategy import BottleneckStrategy
from tests.util_tests import make_attacker, make_defender


class TestBottleneckDeterministicMaps(unittest.TestCase):
    """
    Test BottleneckStrategy on hand-designed grids with manually-reasoned
    expected bottleneck positions.
    """

    # =====================================================================
    # Test 1: Simple Gap
    # =====================================================================
    #
    # Layout:
    # # # # # # # #
    # # . . . . . #
    # # . # D # . #
    # # . # # # . #
    # # A . . # . #
    # # # # # # # #
    
    def test_simple_gap(self):
        """
        Grid with two separate obstacle components separated by a clear vertical gap.
        Expected bottleneck: the passable cell(s) between them.
        """
        width, height = 7, 6
        
        obstacles = [
            # borders
            (0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0),
            (0, 1), (0, 2), (0, 3), (0, 4),
            (6, 1), (6, 2), (6, 3), (6, 4),
            (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (5, 5), (6, 5),
            # obstacle components
            (2, 2), (4, 2),
            (2, 3), (3, 3), (4, 3),
            (4, 4)
        ]
        
        grid = Grid(width, height, obstacles)
        
        target = (5, 4)  # Target on the right side of the gap
        
        # Agents: one attacker at (1, 4) heading for target T at (5, 4)
        attacker = make_attacker(1, 4, target=target, grid=grid)
        
        # Defender starts at (3, 2)
        defender = make_defender(3, 2, grid=grid)

        print("\nGrid layout for test_simple_gap:")
        grid.print_grid()  # Optional: visualize the grid for debugging
        
        strategy = BottleneckStrategy(use_true_targets=True)
        assignment = strategy.allocate(grid, [defender], [target], [attacker])
        
        self.assertEqual(len(assignment), 1, "Defenders should be assigned")
        
        # Collect assigned positions
        assigned_position = set(assignment.values()).pop()

        # The gap (path) between obstacle components
        gap_region = {(1, 3), (1, 2), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (5, 2), (5, 3)}
        
        # Defender should be assigned into the gap
        self.assertTrue(
            assigned_position in gap_region,
            f"Expected defender in gap {gap_region}, "
            f"but got assignment {assigned_position}"
        )
        
        print(f"✓ Test passed: defender was assigned to gap")
        print(f"  Assigned positions: {assigned_position}")

    # =====================================================================
    # Test 2: Two Bottlenecks
    # =====================================================================
    #
    # Layout:
    # # # # # # # # # #
    # # . T . . . . T #
    # # . # . # . # # #
    # # . . . # . D . #
    # # # # . # . # # #
    # # A . . D . . A #
    # # # # # # # # # #
    #
    # Attacker at (1, 5) moving right towards (2, 1).
    # Attacker at (7, 5) moving left towards (7, 1).
    # Three obstacle groups create a bottlenecks at (3, 4) or (5, 4) region.
    #
    def test_two_bottlenecks(self):
        """
        Grid where obstacle groups form a T-shape, creating a bottleneck
        at the center where all paths must converge.
        """
        width, height = 9, 7

        obstacles = [
            # Top and Bottom Borders (y=0 and y=6)
            (0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (8, 0),
            (0, 6), (1, 6), (2, 6), (3, 6), (4, 6), (5, 6), (6, 6), (7, 6), (8, 6),
            
            # Left and Right Borders (x=0 and x=8)
            (0, 1), (0, 2), (0, 3), (0, 4), (0, 5),
            (8, 1), (8, 2), (8, 3), (8, 4), (8, 5),
            
            # Row y=2: # # # ###  -> obstacles at x=2, x=4, x=6, x=7
            (2, 2), (4, 2), (6, 2), (7, 2),
            
            # Row y=3: #   # D #  -> obstacle at x=4
            (4, 3),
            
            # Row y=4: ### # ###  -> obstacles at x=1, x=2, x=4, x=6, x=7
            (1, 4), (2, 4), (4, 4), (6, 4), (7, 4),
        ]
        
        grid = Grid(width, height, obstacles)
        
        # Attacker at (1, 5), target at (2, 1)
        attacker = make_attacker(1, 5, target=(2, 1), grid=grid)
        # Attacker at (7, 5), target at (7, 1)
        attacker = make_attacker(7, 5, target=(7, 1), grid=grid)
        
        # Two defenders to block the main bottleneck
        defender1 = make_defender(4, 5, grid=grid)
        defender2 = make_defender(6, 3, grid=grid)

        print("\nGrid layout for test_two_bottlenecks:")
        grid.print_grid()  # Optional: visualize the grid for debugging
        
        targets = [(2, 1), (7, 1)]
        
        strategy = BottleneckStrategy(use_true_targets=True)
        assignment = strategy.allocate(grid, [defender1, defender2], targets, [attacker])
        
        self.assertEqual(len(assignment), 2)
        
        assigned_positions = set(assignment.values())
        
        # The bottleneck should be around (3, 4) or (5, 4) region
        # depending on path constraints. At minimum, defenders shouldn't all
        # cluster at the target itself.
        self.assertNotEqual(
            assigned_positions,
            {(2, 1), (7, 1)},
            "Defenders should not all be assigned to the target itself"
        )
        
        print(f"✓ Test passed: defenders spread to {assigned_positions}")

    # =====================================================================
    # Test 3: No Bottleneck (Open Space 1)
    # =====================================================================
    #
    # Layout:
    # _______
    #| AD   |
    #| D  T |
    # ___T___
    #
    # Open space with no obstacle groups -> no bottleneck.
    # Strategy should fall back to random assignment.
    #
    def test_no_bottleneck_open_space1(self):
        """
        Grid with no significant obstacle groups -> no bottleneck to find.
        Strategy should fall back to random assignment to available targets.
        """
        width, height = 7, 3
        obstacles = [
        ]
        
        grid = Grid(width, height, obstacles)
        
        attacker = make_attacker(1, 1, target=(5, 1), grid=grid)
        
        defender1 = make_defender(2, 1, grid=grid)
        defender2 = make_defender(1, 2, grid=grid)

        print("\nGrid layout for test_no_bottleneck_open_space1:")
        grid.print_grid()  # Optional: visualize the grid for debugging
        
        targets = [(4, 2), (5, 1)]
        
        strategy = BottleneckStrategy(use_true_targets=True)
        assignment = strategy.allocate(grid, [defender1, defender2], targets, [attacker])
        
        # No bottleneck found -> fallback to random from available targets
        self.assertEqual(len(assignment), 2)
        assigned_positions = set(assignment.values())
        self.assertTrue(
            assigned_positions.issubset(set(targets)),
            f"With no bottleneck, defenders should be assigned to available targets. "
            f"Got {assigned_positions}, targets are {targets}"
        )
        
        print(f"✓ Test open space 1 passed: no bottleneck, fallback to targets: {assigned_positions}")

    # =====================================================================
    # Test 4: No Bottleneck (Open Space 2)
    # =====================================================================
    #
    # Layout:
    # _______
    #|       |
    #|A  T  D|
    #|A  T  D|
    # _______
    #
    # Open space with no obstacle groups -> no bottleneck.
    # Strategy should fall back to random assignment.
    #
    def test_no_bottleneck_open_space2(self):
        """
        Grid with no significant obstacle groups -> no bottleneck to find.
        Strategy should fall back to random assignment to available targets.
        """
        width, height = 7, 4
        obstacles = [
        ]
        
        grid = Grid(width, height, obstacles)
        
        attacker1 = make_attacker(0, 1, target=(3, 1), grid=grid)
        attacker2 = make_attacker(0, 2, target=(3, 2), grid=grid)
        
        defender1 = make_defender(6, 1, grid=grid)
        defender2 = make_defender(6, 2, grid=grid)

        print("\nGrid layout for test_no_bottleneck_open_space2:")
        grid.print_grid()  # Optional: visualize the grid for debugging
        
        targets = [(3, 1), (3, 2)]
        
        strategy = BottleneckStrategy(use_true_targets=True)
        assignment = strategy.allocate(grid, [defender1, defender2], targets, [attacker1, attacker2])
        
        # No bottleneck found -> fallback to random from available targets
        self.assertEqual(len(assignment), 2)
        assigned_positions = set(assignment.values())
        self.assertTrue(
            assigned_positions.issubset(set(targets)),
            f"With no bottleneck, defenders should be assigned to available targets. "
            f"Got {assigned_positions}, targets are {targets}"
        )
        
        print(f"✓ Test open space 2 passed: no bottleneck, fallback to targets: {assigned_positions}")


if __name__ == "__main__":
    # Run with verbose output to see the print statements
    unittest.main(verbosity=2)