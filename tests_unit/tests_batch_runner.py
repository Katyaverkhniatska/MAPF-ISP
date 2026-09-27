import unittest
from typing import Any, Dict

from core_components.grid import Grid
from scenario_management.scenario_loader import ScenarioTemplate, SpawnArea, ScenarioValidationError
from allocation_strategies.allocation_strategy import AllocationStrategy
from simulation_engine.batch_runner import BatchRunner, STRATEGY_FACTORIES


def make_template(**overrides) -> ScenarioTemplate:
    defaults: Dict[str, Any] = dict(
        grid=Grid(8, 6, obstacles=[]),
        obstacles=[],
        targets=[(7, 2), (7, 4)],
        attacker_area=SpawnArea(0, 5, 0, 1),
        defender_area=SpawnArea(0, 5, 3, 5),
        num_attackers=2,
        num_defenders=2,
        predefined_targets=False,
        max_steps=30,
    )
    defaults.update(overrides)
    return ScenarioTemplate(**defaults)


class TestBatchRunner(unittest.TestCase):

    def test_runs_all_strategies_for_every_iteration(self):
        tpl = make_template()
        runner = BatchRunner(tpl, ["Random", "Greedy", "Bottleneck"], iterations=5, seed=1)
        result = runner.run()

        self.assertEqual(result.requested_iterations, 5)
        self.assertEqual(result.iterations_completed, 5)
        self.assertEqual(result.generation_failures, 0)
        for name in ["Random", "Greedy", "Bottleneck"]:
            self.assertEqual(result.runs_completed(name), 5)
            self.assertEqual(result.strategy_failures[name], 0)

    def test_progress_callback_called_once_per_iteration(self):
        tpl = make_template()
        runner = BatchRunner(tpl, ["Random"], iterations=4, seed=2)
        calls = []
        runner.run(on_progress=lambda done, total: calls.append((done, total)))
        self.assertEqual(calls, [(1, 4), (2, 4), (3, 4), (4, 4)])

    def test_rejects_unknown_strategy_name(self):
        tpl = make_template()
        with self.assertRaises(ValueError):
            BatchRunner(tpl, ["NotAStrategy"], iterations=3)

    def test_rejects_non_positive_iterations(self):
        tpl = make_template()
        with self.assertRaises(ValueError):
            BatchRunner(tpl, ["Random"], iterations=0)

    def test_fails_fast_on_predefined_targets_mismatch(self):
        tpl = make_template(predefined_targets=True, num_attackers=3)  # 2 targets, 3 attackers
        with self.assertRaises(ScenarioValidationError):
            BatchRunner(tpl, ["Random"], iterations=5)

    def test_same_seed_gives_same_iteration_count_and_shape(self):
        tpl = make_template()
        r1 = BatchRunner(tpl, ["Greedy"], iterations=6, seed=99).run()
        r2 = BatchRunner(tpl, ["Greedy"], iterations=6, seed=99).run()
        self.assertEqual(r1.iterations_completed, r2.iterations_completed)
        self.assertEqual(r1.runs_completed("Greedy"), r2.runs_completed("Greedy"))
        # same seed -> same generated layouts -> same outcomes
        s1 = [c.targets_protected() for c in r1.strategy_results["Greedy"] if c is not None]
        s2 = [c.targets_protected() for c in r2.strategy_results["Greedy"] if c is not None]
        self.assertEqual(s1, s2)

    def test_generation_failure_skips_iteration_for_every_strategy_equally(self):
        # 1x3 grid, both areas cover the whole strip, target sits in the
        # middle cell -> only 2 free cells total. Requesting 1 attacker +
        # 2 defenders (3 agents) means every single generate() call will
        # fail -- so the whole batch is generation-failures, and every
        # strategy has 0 completed runs, not just some of them.
        tpl = make_template(
            grid=Grid(3, 1, obstacles=[]),
            obstacles=[],
            targets=[(1, 0)],
            attacker_area=SpawnArea(0, 0, 0, 2),
            defender_area=SpawnArea(0, 0, 0, 2),
            num_attackers=1,
            num_defenders=2,
        )
        runner = BatchRunner(tpl, ["Random", "Greedy"], iterations=4, seed=1)
        result = runner.run()

        self.assertEqual(result.generation_failures, 4)
        self.assertEqual(result.iterations_completed, 0)
        self.assertEqual(result.runs_completed("Random"), 0)
        self.assertEqual(result.runs_completed("Greedy"), 0)

    def test_strategy_failure_keeps_lists_index_aligned_across_strategies(self):
        # A strategy that raises on its 2nd call (0-indexed: fails at i=1)
        # must still leave every strategy's list the SAME length, with a
        # None placeholder at that index -- not silently shifted.
        tpl = make_template()

        class FlakyStrategy(AllocationStrategy):
            calls = 0
            def allocate(self, grid, defenders, targets, attackers):
                FlakyStrategy.calls += 1
                if FlakyStrategy.calls == 2:
                    raise RuntimeError("simulated failure")
                assignment = {}
                for i, d in enumerate(defenders):
                    if targets:
                        assignment[d] = targets[i % len(targets)]
                return assignment

        from simulation_engine import batch_runner as br_module
        original_factories = dict(br_module.STRATEGY_FACTORIES)
        br_module.STRATEGY_FACTORIES["Flaky"] = lambda: FlakyStrategy()
        try:
            runner = BatchRunner(tpl, ["Random", "Flaky"], iterations=4, seed=3)
            result = runner.run()

            self.assertEqual(len(result.strategy_results["Random"]), 4)
            self.assertEqual(len(result.strategy_results["Flaky"]), 4)
            # Exactly one None in Flaky's list, at the position it failed.
            none_positions = [i for i, c in enumerate(result.strategy_results["Flaky"]) if c is None]
            self.assertEqual(len(none_positions), 1)
            self.assertEqual(result.strategy_failures["Flaky"], 1)
            self.assertEqual(result.strategy_failures["Random"], 0)
            # Random has no None entries at all -- its list is fully populated
            # even though Flaky failed partway through.
            self.assertTrue(all(c is not None for c in result.strategy_results["Random"]))
        finally:
            br_module.STRATEGY_FACTORIES.clear()
            br_module.STRATEGY_FACTORIES.update(original_factories)

    def test_strategy_factories_cover_all_advertised_names(self):
        self.assertEqual(set(STRATEGY_FACTORIES.keys()), {"Random", "Greedy", "Bottleneck"})
        for name, factory in STRATEGY_FACTORIES.items():
            strat_a = factory()
            strat_b = factory()
            self.assertIsNot(strat_a, strat_b, f"{name} factory should build a fresh instance each call")


if __name__ == "__main__":
    unittest.main()