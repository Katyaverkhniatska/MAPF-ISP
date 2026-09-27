import statistics as stats
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from simulation_engine.batch_runner import BatchResult, SimulationStatistics


@dataclass
class StrategySummary:
    """One strategy's row in the comparison table."""
    strategy_name: str

    runs_completed: int             # (strategy, iteration) pairs that ran successfully
    runs_failed: int                # runtime failures for this strategy specifically

    success_rate_mean: float
    success_rate_std: float

    targets_protected_mean: float
    targets_captured_mean: float

    # Attacker/defender arrival times can be None for a given run (nobody
    # arrived), so mean/count are reported separately: `_count` is how
    # many runs actually contributed a value, out of `runs_completed`.
    avg_attacker_time_mean: Optional[float]
    avg_attacker_time_count: int
    avg_defender_time_mean: Optional[float]
    avg_defender_time_count: int

    defender_efficiency_mean: float
    total_steps_mean: float

    win_count: int                  # iterations where this strategy protected the most targets (ties count for all)


@dataclass
class BatchSummary:
    """The full comparison result: one summary per strategy, plus batch-level context."""
    requested_iterations: int
    iterations_completed: int
    generation_failures: int
    iterations_used_for_win_count: int   # iterations where every strategy succeeded
    strategies: Dict[str, StrategySummary]


def aggregate(result: BatchResult) -> BatchSummary:
    strategies: Dict[str, StrategySummary] = {}

    for name, calcs in result.strategy_results.items():
        successful = [c for c in calcs if c is not None]

        success_rates = [c.success_rate() for c in successful]
        protected = [float(c.targets_protected()) for c in successful]
        captured = [float(c.targets_captured()) for c in successful]
        efficiency = [c.defender_efficiency() for c in successful]
        steps = [float(c.total_steps()) for c in successful]

        attacker_times = [c.average_attacker_time() for c in successful]
        attacker_times_valid = [t for t in attacker_times if t is not None]
        defender_times = [c.average_defender_time() for c in successful]
        defender_times_valid = [t for t in defender_times if t is not None]

        strategies[name] = StrategySummary(
            strategy_name=name,
            runs_completed=len(successful),
            runs_failed=result.strategy_failures.get(name, 0),
            success_rate_mean=_mean(success_rates),
            success_rate_std=_pstdev(success_rates),
            targets_protected_mean=_mean(protected),
            targets_captured_mean=_mean(captured),
            avg_attacker_time_mean=_mean_or_none(attacker_times_valid),
            avg_attacker_time_count=len(attacker_times_valid),
            avg_defender_time_mean=_mean_or_none(defender_times_valid),
            avg_defender_time_count=len(defender_times_valid),
            defender_efficiency_mean=_mean(efficiency),
            total_steps_mean=_mean(steps),
            win_count=0,  # filled in below
        )

    win_counts, iterations_used = _compute_win_counts(result)
    for name, count in win_counts.items():
        strategies[name].win_count = count

    return BatchSummary(
        requested_iterations=result.requested_iterations,
        iterations_completed=result.iterations_completed,
        generation_failures=result.generation_failures,
        iterations_used_for_win_count=iterations_used,
        strategies=strategies,
    )


def _compute_win_counts(result: BatchResult) -> Tuple[Dict[str, int], int]:
    """
    For each iteration where every strategy has a non-None result (a fair,
    paired comparison), the strategy(ies) with the most protected targets
    each get a win. Iterations where any strategy failed are skipped
    entirely for this metric, since there's nothing fair to compare.
    """
    names = list(result.strategy_results.keys())
    wins = {name: 0 for name in names}
    if not names:
        return wins, 0

    iterations_used = 0
    length = result.iterations_completed
    for i in range(length):
        row = {name: result.strategy_results[name][i] for name in names}
        if any(calc is None for calc in row.values()):
            continue
        # Rebuild as a narrowed dict (values known non-None here) rather
        # than relying on the type checker to infer that from the `any()`
        # check above -- it can't propagate that narrowing into a
        # dict comprehension's values.
        resolved: Dict[str, SimulationStatistics] = {
            name: calc for name, calc in row.items() if calc is not None
        }
        iterations_used += 1
        best = max(calc.targets_protected() for calc in resolved.values())
        for name, calc in resolved.items():
            if calc.targets_protected() == best:
                wins[name] += 1

    return wins, iterations_used


def _mean(values: List[float]) -> float:
    return stats.mean(values) if values else 0.0


def _mean_or_none(values: List[float]) -> Optional[float]:
    return stats.mean(values) if values else None


def _pstdev(values: List[float]) -> float:
    # Population stdev: we treat the completed runs as the entire
    # population of interest for this batch, not a sample of a larger
    # one. len < 2 -> 0.0 (no spread to report).
    return stats.pstdev(values) if len(values) >= 2 else 0.0