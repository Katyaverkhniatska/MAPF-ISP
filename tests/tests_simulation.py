import unittest
from unittest.mock import patch
from allocation_strategies.bottleneck_strategy import BottleneckStrategy
from allocation_strategies.greedy_strategy import GreedyStrategy
from allocation_strategies.random_strategy import RandomStrategy
from core_components.agent import Agent
from core_components.agent_type import AgentType
from core_components.grid import Grid
from simulation_engine.simulation import Simulation
from tests.util_tests import make_attacker, make_defender, print_simulation_step, FixedStrategy, FixedStrategyWithBottlenecks


class TestSimulationConstruction(unittest.TestCase):

    def test_raises_if_attacker_has_no_target(self):
        """Precondition: every attacker must already have a target before
        Simulation is constructed -- Simulation only allocates defenders."""
        grid = Grid(5, 5, obstacles=[])
        attacker = make_attacker(0, 0, target=None, grid=grid)  # target never set
        defender = make_defender(1, 1, grid=grid)

        with self.assertRaises(ValueError):
            Simulation(grid, [defender], [attacker], [(2, 2)], RandomStrategy())

    def test_allocation_runs_once_and_sets_defender_targets(self):
        """Constructor should call strategy.allocate() and push the result
        onto each defender via Agent.set_target()."""
        grid = Grid(5, 5, obstacles=[])
        defender = make_defender(0, 0, grid=grid)
        target = (3, 3)
        strategy = FixedStrategy({defender: target})

        sim = Simulation(grid, [defender], [], [target], strategy, max_steps=10)

        self.assertEqual(sim.assignment, {defender: target})
        self.assertEqual(defender.get_target(), target)

    def test_bottleneck_vertices_picked_up_when_strategy_provides_them(self):
        """Simulation duck-types on `last_bottlenecks`: present -> copied
        into self.bottleneck_vertices (and every snapshot)."""
        grid = Grid(5, 5, obstacles=[])
        defender = make_defender(0, 0, grid=grid)
        target = (2, 2)
        strategy = FixedStrategyWithBottlenecks({defender: target}, {(1, 1), (1, 2)})

        sim = Simulation(grid, [defender], [], [target], strategy, max_steps=1)

        self.assertEqual(sim.bottleneck_vertices, {(1, 1), (1, 2)})
        self.assertEqual(sim.history[0].bottleneck_vertices, {(1, 1), (1, 2)})

    def test_bottleneck_vertices_empty_for_strategy_without_attribute(self):
        """Random/Greedy don't set last_bottlenecks -- getattr's default
        should keep them working against the same Simulation, unmodified."""
        grid = Grid(5, 5, obstacles=[])
        defender = make_defender(0, 0, grid=grid)
        strategy = RandomStrategy()

        sim = Simulation(grid, [defender], [], [(2, 2)], strategy, max_steps=1)

        self.assertEqual(sim.bottleneck_vertices, set())


class TestInitialSnapshot(unittest.TestCase):
    """Step 0 must capture pre-existing occupancy before anyone moves."""

    def test_defender_already_on_target_is_protected_immediately(self):
        grid = Grid(5, 5, obstacles=[])
        target = (2, 2)
        defender = make_defender(*target, grid=grid)  # starts exactly on its future target
        strategy = FixedStrategy({defender: target})

        sim = Simulation(grid, [defender], [], [target], strategy, max_steps=5)

        self.assertIn(target, sim.protected_targets)
        self.assertEqual(sim.history[0].step, 0)
        self.assertTrue(sim.finished)  # only target already resolved
        self.assertEqual(len(sim.history), 1)  # no stepping needed

    def test_attacker_already_on_target_is_captured_immediately(self):
        grid = Grid(5, 5, obstacles=[])
        target = (2, 2)
        attacker = make_attacker(*target, target=target, grid=grid)  # starts on its own target

        sim = Simulation(grid, [], [attacker], [target], RandomStrategy(), max_steps=5)

        self.assertIn(target, sim.captured_targets)
        self.assertTrue(sim.finished)
        self.assertEqual(len(sim.history), 1)


class TestStepping(unittest.TestCase):

    def test_defenders_move_before_attackers_each_tick(self):
        """Matches the paper's turn-based framing: defenders move first."""
        grid = Grid(5, 5, obstacles=[])
        defender = make_defender(0, 0, grid=grid)
        attacker = make_attacker(4, 4, target=(4, 4), grid=grid)  # already there, won't move
        strategy = FixedStrategy({defender: (1, 1)})

        sim = Simulation(grid, [defender], [attacker], [(1, 1)], strategy, max_steps=1)

        order = []
        original_move_one = sim._move_one

        def spy(agent):
            order.append(agent)
            return original_move_one(agent)

        with patch.object(sim, "_move_one", side_effect=spy):
            sim.step()

        self.assertEqual(order, [defender, attacker])

    def test_defender_reaches_target_over_multiple_steps(self):
        """On an open grid, LRA* replanning should converge on the shortest
        (Manhattan) path: 3 steps to cover a distance of 3."""
        grid = Grid(5, 5, obstacles=[])
        defender = make_defender(0, 0, grid=grid)
        target = (0, 3)
        strategy = FixedStrategy({defender: target})

        sim = Simulation(grid, [defender], [], [target], strategy, max_steps=10)
        history = sim.run()

        self.assertTrue(sim.finished)
        self.assertEqual(sim.step_count, 3)
        self.assertIn(target, sim.protected_targets)
        self.assertIs(history, sim.history)

    def test_agent_already_at_target_does_not_move(self):
        grid = Grid(5, 5, obstacles=[])
        target = (1, 1)
        defender = make_defender(*target, grid=grid)
        strategy = FixedStrategy({defender: target})

        sim = Simulation(grid, [defender], [], [target], strategy, max_steps=3)
        sim.step()

        self.assertEqual(defender.get_position(), target)

    def test_unreachable_target_hits_max_steps_without_resolution(self):
        """A wall fully separating the defender from its target (same
        layout as PathFinder's own test_no_path_exists) should leave the
        target unresolved until max_steps forces the run to stop."""
        obstacles = [(1, 0), (1, 1), (1, 2), (1, 3), (1, 4)]
        grid = Grid(5, 5, obstacles=obstacles)
        defender = make_defender(0, 2, grid=grid)
        target = (4, 2)
        strategy = FixedStrategy({defender: target})

        sim = Simulation(grid, [defender], [], [target], strategy, max_steps=3)
        sim.run()

        self.assertTrue(sim.finished)
        self.assertEqual(sim.step_count, 3)
        self.assertNotIn(target, sim.protected_targets)
        self.assertNotIn(target, sim.captured_targets)
        self.assertEqual(defender.get_position(), (0, 2))  # never moved

    def test_step_returns_none_once_finished(self):
        grid = Grid(5, 5, obstacles=[])
        target = (1, 1)
        defender = make_defender(*target, grid=grid)
        strategy = FixedStrategy({defender: target})

        sim = Simulation(grid, [defender], [], [target], strategy, max_steps=5)
        self.assertTrue(sim.finished)  # resolved at construction time
        self.assertIsNone(sim.step())


class TestTargetResolution(unittest.TestCase):

    def test_mixed_capture_and_protection(self):
        """One target captured by an attacker, another protected by a
        defender, in the same run."""
        grid = Grid(10, 10, obstacles=[])
        captured_target = (0, 0)
        protected_target = (9, 9)

        attacker = make_attacker(*captured_target, target=captured_target, grid=grid)
        defender = make_defender(*protected_target, grid=grid)
        strategy = FixedStrategy({defender: protected_target})

        sim = Simulation(
            grid,
            [defender],
            [attacker],
            [captured_target, protected_target],
            strategy,
            max_steps=5,
        )

        self.assertEqual(sim.captured_targets, {captured_target})
        self.assertEqual(sim.protected_targets, {protected_target})
        self.assertTrue(sim.finished)


class TestSnapshotAgentIds(unittest.TestCase):

    def test_agent_ids_are_stable_and_disjoint_between_groups(self):
        """_agent_ids enumerates defenders then attackers, so ids should be
        stable across steps and unique across the whole roster."""
        grid = Grid(5, 5, obstacles=[])
        defenders = [make_defender(0, 0, grid=grid), make_defender(1, 0, grid=grid)]
        attackers = [make_attacker(4, 4, target=(4, 4), grid=grid)]
        strategy = FixedStrategy({defenders[0]: (2, 2), defenders[1]: (3, 3)})

        sim = Simulation(
            grid, defenders, attackers, [(2, 2), (3, 3)], strategy, max_steps=5
        )
        sim.step()

        first_ids = {s.agent_id for s in sim.history[0].defenders + sim.history[0].attackers}
        last_ids = {s.agent_id for s in sim.history[-1].defenders + sim.history[-1].attackers}
        self.assertEqual(first_ids, last_ids)
        self.assertEqual(len(first_ids), 3)

class TestSimulationDeterministic(unittest.TestCase):

    def test_empty_grid_two_attackers_two_defenders(self):
        """
        Empty 7x7 Grid:
        - 2 Targets in the center: (3, 3) and (3, 4)
        - 2 Attackers starting at (0, 3) and (0, 4)
        - 2 Defenders starting at (6, 3) and (6, 4)
        Defenders and attackers race to the center.
        """
        width, height = 7, 7
        obstacles = []
        grid = Grid(width, height, obstacles)

        t1, t2 = (3, 3), (3, 4)
        targets = [t1, t2]

        a1 = Agent(0, 3, AgentType.ATTACKER)
        a1.set_target(t1)
        a2 = Agent(0, 4, AgentType.ATTACKER)
        a2.set_target(t2)
        attackers = [a1, a2]

        d1 = Agent(6, 3, AgentType.DEFENDER)
        d2 = Agent(6, 4, AgentType.DEFENDER)
        defenders = [d1, d2]

        # Greedy strategy assigns closest defender to target
        strategy = GreedyStrategy()
        sim = Simulation(grid, defenders, attackers, targets, strategy, max_steps=10)

        print("\n==================================================")
        print("TEST 1: Empty Grid (2 Attackers, 2 Defenders, 2 Targets)")
        print("==================================================")

        # Print initial state (Step 0)
        print_simulation_step(grid, sim.history[0], "Initial State (Step 0)")

        # Run simulation tick-by-tick and display
        while not sim.finished:
            snapshot = sim.step()
            if snapshot:
                print_simulation_step(grid, snapshot)

        self.assertTrue(sim.finished)
        self.assertEqual(len(sim.protected_targets), 2, "Both targets should be protected by defenders")
        self.assertEqual(len(sim.captured_targets), 0, "No targets should be captured")

    def test_bottleneck_grid_two_attackers_three_defenders(self):
        """
        Grid with a vertical wall creating a 3-cell bottleneck passage:
        - Passage at x=3, y in [2, 3, 4]
        - 2 Attackers on the left: (0, 2) and (0, 4) heading for targets on the right
        - 3 Defenders on the left: (1, 2), (1, 3), and (1, 4)
        - 2 Targets on the right side: (5, 2) and (5, 4)
        """
        width, height = 7, 7
        
        # Vertical wall at x=3 with a 3-cell gap at y=2, 3, 4
        obstacles = [(3, 0), (3, 1), (3, 5), (3, 6)]
        grid = Grid(width, height, obstacles)

        t1, t2 = (5, 2), (5, 4)
        targets = [t1, t2]

        a1 = Agent(0, 2, AgentType.ATTACKER)
        a1.set_target(t1)
        a2 = Agent(0, 4, AgentType.ATTACKER)
        a2.set_target(t2)
        attackers = [a1, a2]

        d1 = Agent(1, 2, AgentType.DEFENDER)
        d2 = Agent(1, 3, AgentType.DEFENDER)
        d3 = Agent(1, 4, AgentType.DEFENDER)
        defenders = [d1, d2, d3]

        strategy = BottleneckStrategy(use_true_targets=True)
        sim = Simulation(grid, defenders, attackers, targets, strategy, max_steps=15)

        print("\n==================================================")
        print("TEST 2: Bottleneck Grid (2 Attackers, 3 Defenders, 3-cell gap)")
        print("==================================================")

        # Print initial state (Step 0)
        print_simulation_step(grid, sim.history[0], "Initial State (Step 0)")

        # Run simulation tick-by-tick and display
        while not sim.finished:
            snapshot = sim.step()
            if snapshot:
                print_simulation_step(grid, snapshot)

        self.assertTrue(sim.finished)
        self.assertGreaterEqual(
            len(sim.protected_targets), 1,
            "At least one target should be protected by defender bottleneck allocation"
        )

    def test_no_bottleneck_open_space(self):
        """
        Open space with no obstacle groups -> no bottleneck.
        Strategy should fall back to random assignment.
        """
        print("\nRunning test_no_bottleneck_open_space...")
        width, height = 7, 7
        obstacles = []
        grid = Grid(width, height, obstacles)

        t1, t2 = (3, 3), (3, 4)
        targets = [t1, t2]

        a1 = Agent(0, 3, AgentType.ATTACKER)
        a1.set_target(t1)
        a2 = Agent(0, 4, AgentType.ATTACKER)
        a2.set_target(t2)
        attackers = [a1, a2]

        d1 = Agent(6, 3, AgentType.DEFENDER)
        d2 = Agent(6, 4, AgentType.DEFENDER)
        defenders = [d1, d2]

        strategy = BottleneckStrategy(use_true_targets=True)
        sim = Simulation(grid, defenders, attackers, targets, strategy, max_steps=10)

        print("\n==================================================")
        print("TEST 3: No Bottleneck (Open Space)")
        print("==================================================")

        # Print initial state (Step 0)
        print_simulation_step(grid, sim.history[0], "Initial State (Step 0)")

        # Run simulation tick-by-tick and display
        while not sim.finished:
            snapshot = sim.step()
            if snapshot:
                print_simulation_step(grid, snapshot)

        self.assertTrue(sim.finished)


if __name__ == "__main__":
    unittest.main()