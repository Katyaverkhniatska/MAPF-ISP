import unittest
from typing import Any, Dict, Optional

from core_components.grid import Grid
from scenario_management.scenario_loader import ScenarioTemplate, SpawnArea
from simulation_engine.batch_runner import BatchRunner, BatchResult, SimulationStatistics
from simulation_engine.batch_aggregator import aggregate


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


class TestBatchAggregatorOnRealRun(unittest.TestCase):
    """Sanity checks against an actual BatchRunner run (using the stub strategies)."""

    def test_basic_shape_and_run_counts(self):
        tpl = make_template()
        result = BatchRunner(tpl, ["Random", "Greedy", "Bottleneck"], iterations=6, seed=10).run()
        summary = aggregate(result)

        self.assertEqual(summary.requested_iterations, 6)
        self.assertEqual(summary.iterations_completed, 6)
        self.assertEqual(summary.generation_failures, 0)
        self.assertEqual(set(summary.strategies.keys()), {"Random", "Greedy", "Bottleneck"})

        for name, s in summary.strategies.items():
            self.assertEqual(s.runs_completed, 6)
            self.assertEqual(s.runs_failed, 0)
            self.assertTrue(0.0 <= s.success_rate_mean <= 1.0)
            self.assertGreaterEqual(s.total_steps_mean, 0)

        # every iteration succeeded for every strategy -> all 6 usable for win count
        self.assertEqual(summary.iterations_used_for_win_count, 6)

    def test_win_counts_sum_covers_every_used_iteration_at_least_once(self):
        tpl = make_template()
        result = BatchRunner(tpl, ["Random", "Greedy", "Bottleneck"], iterations=8, seed=20).run()
        summary = aggregate(result)
        total_wins = sum(s.win_count for s in summary.strategies.values())
        # each used iteration contributes >=1 win (ties give multiple),
        # so total wins across strategies must be >= iterations used.
        self.assertGreaterEqual(total_wins, summary.iterations_used_for_win_count)


class TestBatchAggregatorSynthetic(unittest.TestCase):
    """Feed a hand-built BatchResult so the math itself is checked precisely."""

    class FakeCalc:
        """
        Structurally satisfies the SimulationStatistics Protocol (same
        method names/signatures as StatisticsCalculator) without needing
        to subclass it or construct real StepSnapshots.
        """
        def __init__(self, protected: int, captured: int, sr: float,
                     atk_time: Optional[float], def_time: Optional[float],
                     eff: float, steps: int):
            self._protected, self._captured, self._sr = protected, captured, sr
            self._atk_time, self._def_time, self._eff, self._steps = atk_time, def_time, eff, steps
        def targets_protected(self) -> int: return self._protected
        def targets_captured(self) -> int: return self._captured
        def success_rate(self) -> float: return self._sr
        def average_attacker_time(self) -> Optional[float]: return self._atk_time
        def average_defender_time(self) -> Optional[float]: return self._def_time
        def defender_efficiency(self) -> float: return self._eff
        def total_steps(self) -> int: return self._steps

    def test_none_entries_excluded_from_means_and_counted_as_failures(self):
        result = BatchResult(
            requested_iterations=3,
            iterations_completed=3,
            generation_failures=0,
            strategy_results={
                "A": [
                    self.FakeCalc(2, 0, 1.0, 5, 4, 1.0, 10),
                    None,  # A failed this iteration
                    self.FakeCalc(1, 1, 0.5, 6, None, 0.5, 12),
                ],
            },
            strategy_failures={"A": 1},
        )
        summary = aggregate(result)
        a = summary.strategies["A"]
        self.assertEqual(a.runs_completed, 2)
        self.assertEqual(a.runs_failed, 1)
        self.assertAlmostEqual(a.targets_protected_mean, 1.5)  # mean of [2, 1], skipping None
        self.assertEqual(a.avg_attacker_time_count, 2)          # both successful runs had a value
        self.assertEqual(a.avg_defender_time_count, 1)          # one of the two had None here
        assert a.avg_defender_time_mean
        self.assertAlmostEqual(a.avg_defender_time_mean, 4.0)

    def test_win_count_skips_iteration_where_any_strategy_failed(self):
        result = BatchResult(
            requested_iterations=2,
            iterations_completed=2,
            generation_failures=0,
            strategy_results={
                "A": [self.FakeCalc(2, 0, 1.0, 5, 4, 1.0, 10), self.FakeCalc(1, 0, 0.5, 5, 4, 0.5, 10)],
                "B": [self.FakeCalc(1, 0, 0.5, 5, 4, 0.5, 10), None],  # B fails iteration 1
            },
            strategy_failures={"A": 0, "B": 1},
        )
        summary = aggregate(result)
        # Only iteration 0 is usable (both succeeded there); A protected
        # more (2 vs 1), so A gets the win and iteration 1 is excluded.
        self.assertEqual(summary.iterations_used_for_win_count, 1)
        self.assertEqual(summary.strategies["A"].win_count, 1)
        self.assertEqual(summary.strategies["B"].win_count, 0)

    def test_tied_iteration_gives_win_to_both(self):
        result = BatchResult(
            requested_iterations=1,
            iterations_completed=1,
            generation_failures=0,
            strategy_results={
                "A": [self.FakeCalc(2, 0, 1.0, 5, 4, 1.0, 10)],
                "B": [self.FakeCalc(2, 0, 1.0, 5, 4, 1.0, 10)],
            },
            strategy_failures={"A": 0, "B": 0},
        )
        summary = aggregate(result)
        self.assertEqual(summary.strategies["A"].win_count, 1)
        self.assertEqual(summary.strategies["B"].win_count, 1)

    def test_no_successful_runs_yields_zeroed_means_not_a_crash(self):
        result = BatchResult(
            requested_iterations=2,
            iterations_completed=2,
            generation_failures=0,
            strategy_results={"A": [None, None]},
            strategy_failures={"A": 2},
        )
        summary = aggregate(result)
        a = summary.strategies["A"]
        self.assertEqual(a.runs_completed, 0)
        self.assertEqual(a.runs_failed, 2)
        self.assertEqual(a.success_rate_mean, 0.0)
        self.assertIsNone(a.avg_attacker_time_mean)
        self.assertEqual(a.avg_attacker_time_count, 0)
        self.assertEqual(a.win_count, 0)

    def test_single_run_has_zero_std_not_an_error(self):
        result = BatchResult(
            requested_iterations=1,
            iterations_completed=1,
            generation_failures=0,
            strategy_results={"A": [self.FakeCalc(2, 0, 0.7, 5, 4, 1.0, 10)]},
            strategy_failures={"A": 0},
        )
        summary = aggregate(result)
        self.assertEqual(summary.strategies["A"].success_rate_std, 0.0)


if __name__ == "__main__":
    unittest.main()