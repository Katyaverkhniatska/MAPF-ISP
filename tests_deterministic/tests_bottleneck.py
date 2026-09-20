import unittest
from core_components.grid import Grid
from allocation_strategies.bottleneck_strategy import BottleneckStrategy
from tests_unit.util_tests import make_attacker, make_defender

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
        
        print(f"✓ Test simple map passed: defender was assigned to the gap")
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
        attacker1 = make_attacker(1, 5, target=(2, 1), grid=grid)
        # Attacker at (7, 5), target at (7, 1)
        attacker2 = make_attacker(7, 5, target=(7, 1), grid=grid)
        
        # Two defenders to block the main bottleneck
        defender1 = make_defender(4, 5, grid=grid)
        defender2 = make_defender(6, 3, grid=grid)

        targets = [(2, 1), (7, 1)]
        
        strategy = BottleneckStrategy(use_true_targets=True)
        assignment = strategy.allocate(grid, [defender1, defender2], targets, [attacker1, attacker2])
        
        self.assertEqual(len(assignment), 2)
        assigned_positions = set(assignment.values())
        
        self.assertNotEqual(
            assigned_positions,
            {(2, 1), (7, 1)},
            "Defenders should not all be assigned to the targets themselves"
        )

        self.assertEqual(
            # Due to 4-connectivity, (3,3) is also a blocking position and is closer to defender
            assigned_positions, {(3, 3), (5, 4)},
            f"Expected bottlenecks blocked, got {assigned_positions}"
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
        obstacles = []
        
        grid = Grid(width, height, obstacles)
        
        attacker = make_attacker(1, 1, target=(5, 1), grid=grid)
        
        defender1 = make_defender(2, 1, grid=grid)
        defender2 = make_defender(1, 2, grid=grid)
        
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
        obstacles = []
        
        grid = Grid(width, height, obstacles)
        
        attacker1 = make_attacker(0, 1, target=(3, 1), grid=grid)
        attacker2 = make_attacker(0, 2, target=(3, 2), grid=grid)
        
        defender1 = make_defender(6, 1, grid=grid)
        defender2 = make_defender(6, 2, grid=grid)
        
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

    #  . # . . 
    #  . # . .
    #  A D . T  <- Defender D starts at (2, 2), directly inside the gap
    #  . # . .
    #  , # . .
    def test_spawns_inside_a_gap(self):
        """
        Defender's starting positions is a gap. Should correctly identify it and not move so it breaks
        the existing block.
        """
        width, height = 4, 5
        obstacles = [
            (1, 0), (1, 1), (1, 3), (1, 4)
        ]
        gap = (1, 2)

        grid = Grid(width, height, obstacles)
        grid.print_grid()

        target = (3, 2)
        attacker = make_attacker(0, 2, target, grid)
        defender = make_defender(1, 2, grid)

        strategy = BottleneckStrategy(use_true_targets=True)
        assignment = strategy.allocate(grid, [defender], [target], [attacker])

        self.assertEqual(len(assignment), 1)

        assigned = list(assignment.values())[0]

        self.assertEqual(
            assigned, gap,
            f"Expected to remain in the gap, got {assigned}"
        )

        print(f"✓ Test spawns inside a gap passed, remained in the position {assigned}")


class TestBottleneckInsufficientDefenders(unittest.TestCase):
    """
    When available defenders are fewer than the gap width (e.g., 2 defenders for a 3-cell gap),
    partially blocking the gap leaves an open cell that allows attackers through at zero extra cost.
    
    Since the bottleneck cannot be effectively sealed, the strategy should fall back 
    to assigning defenders to target locations.
    """

    #  # # # # # # # # #
    #  # . . . # . . . #
    #  # D . . . . . . #
    #  # A . . . . . T #
    #  # D . . . . . . #
    #  # . . . # . . . #
    #  # # # # # # # # #

    def test_insufficient_defenders_falls_back_to_targets(self):
        width, height = 9, 7
        obstacles = []
        for x in range(width):
            obstacles += [(x, 0), (x, height - 1)]
        for y in range(height):
            obstacles += [(0, y), (width - 1, y)]
            
        # Wall at x=4 with a 3-cell wide opening at y=2, 3, 4
        for y in [1, 5]:
            obstacles.append((4, y))

        grid = Grid(width, height, obstacles)
        target = (7, 3)

        attacker = make_attacker(1, 3, target=target, grid=grid)
        d1 = make_defender(1, 2, grid=grid)
        d2 = make_defender(1, 4, grid=grid)

        strategy = BottleneckStrategy(use_true_targets=True)
        assignment = strategy.allocate(grid, [d1, d2], [target], [attacker])

        assigned_positions = set(assignment.values())

        # With insufficient defenders to seal the 3-cell door,
        # defenders must fall back to target assignment rather than wasting positions in the gap.
        self.assertEqual(len(assignment), 2)
        self.assertIn(
            target, 
            assigned_positions,
            f"Defenders should fall back to target position {target}, but got {assigned_positions}"
        )

        print(f"✓ Test insufficient defenders passed: no suitable bottleneck, fallback to a target: {assigned_positions}")

class TestBottleneckSequentialChokepoints(unittest.TestCase):
    #  # # # # # # # # # # # # #
    #  # . . . # . . . # . . . #
    #  # . A . . . . . . . . T #
    #  # . . . . . . . . . . . #
    #  # . . D . . . . # D . . #
    #  # . . . # . . . # . . . #
    #  # # # # # # # # # # # # #
    def test_two_chokepoints_in_series(self):
        """
        To test sequential chokepoint discovery, the first wall gap is 3 cells wide (y=2,3,4)
        while only 2 defenders are available. This leaves a 1-cell opening so attackers can 
        still traverse to the second wall at x=8, allowing the next iteration to discover the 
        second chokepoint.
        """
        width, height = 13, 7
        obstacles = []
        for x in range(width):
            obstacles += [(x, 0), (x, height - 1)]
        for y in range(height):
            obstacles += [(0, y), (width - 1, y)]

        # Wall at x=4: 3-cell gap at y=2, 3, 4 (obstacle only at y=1, y=5)
        for y in [1, 5]:
            obstacles.append((4, y))
            
        # Wall at x=8: 2-cell gap at y=2, 3 (obstacles at y=1, y=4, y=5)
        for y in [1, 4, 5]:
            obstacles.append((8, y))

        grid = Grid(width, height, obstacles)
        target = (11, 2)

        attacker = make_attacker(2, 2, target=target, grid=grid)
        d1 = make_defender(3, 4, grid=grid)
        d2 = make_defender(9, 4, grid=grid)

        strategy = BottleneckStrategy(use_true_targets=True)
        assignment = strategy.allocate(grid, [d1, d2], [target], [attacker])

        self.assertEqual(len(assignment), 2)
        assigned = set(assignment.values())

        gap_first_wall = {(4, 2), (4, 3), (4, 4)}
        # Due to 4-connectivity there are several ways to block a gap
        gap_second_wall = {(8, 2), (8, 3)}
        gap_second_wall_front = {(7, 2), (7, 3)}
        gap_second_wall_back = {(9, 2), (9, 3)}

        self.assertFalse(
            assigned & gap_first_wall,
            f"Expected no defenders in {gap_first_wall}, got {assigned}",
        )
        self.assertTrue(
            (assigned & gap_second_wall) or (assigned & gap_second_wall_back) or (assigned & gap_second_wall_front), 
            f"Expected all defenders around {gap_second_wall}, got {assigned}",
        )
        print(f"✓ Test multiple chockepoints passed: ignored a wider bottleneck, blocked the correct one {assigned}")

class TestBottleneckNoAvailablePaths(unittest.TestCase):
    # # # # # #
    # # D . . #
    # # # # # #
    # . A . . .
    # . . . T .

    def test_no_available_paths(self):
        """
        The defender is fully surrounded by the obstacles. The strategy should still
        assign it to a target.
        """
        width, height = 5, 5
        obstacles = [
            (0, 0), (1, 0), (2, 0), (3, 0), (4, 0),
            (0, 1), (4, 1),
            (0, 2), (1, 2), (2, 2), (3, 2), (4, 2)
        ]

        grid = Grid(width, height, obstacles)
        target = (3, 4)

        attacker = make_attacker(1, 3, target, grid)
        defender = make_defender(1, 1, grid)

        strategy = BottleneckStrategy(use_true_targets=True)
        assignment = strategy.allocate(grid, [defender], [target], [attacker])

        self.assertEqual(len(assignment), 1)

        assigned_pos = list(assignment.values())[0]
        self.assertEqual(
            assigned_pos, target,
            f"Expected fallback to target, got {assigned_pos}"
        )

        print(f"✓ Test with no paths passed: no suitable bottleneck, fallback to a target: {assigned_pos}")

if __name__ == "__main__":
    # Run with verbose output to see the print statements
    unittest.main()