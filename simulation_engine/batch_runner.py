from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Protocol

from core_components.agent import Agent
from core_components.agent_type import AgentType
from core_components.grid import Grid, Vertex
from allocation_strategies.allocation_strategy import AllocationStrategy
from allocation_strategies.random_strategy import RandomStrategy
from allocation_strategies.greedy_strategy import GreedyStrategy
from allocation_strategies.bottleneck_strategy import BottleneckStrategy
from scenario_management.scenario_loader import ScenarioTemplate, ScenarioValidationError
from scenario_management.scenario_generator import ScenarioGenerator, GeneratedLayout
from simulation_engine.simulation import Simulation
from simulation_engine.statistics_calculator import StatisticsCalculator


class SimulationStatistics(Protocol):
    """
    Structural type for "anything with StatisticsCalculator's read-only
    accessors". BatchResult and the aggregator are typed against this
    Protocol instead of the concrete StatisticsCalculator class, so a
    test double only needs to implement these methods -- it doesn't need
    to subclass StatisticsCalculator (which requires real StepSnapshots
    to construct) to satisfy the type checker.
    """
    def success_rate(self) -> float: ...
    def targets_protected(self) -> int: ...
    def targets_captured(self) -> int: ...
    def average_attacker_time(self) -> Optional[float]: ...
    def average_defender_time(self) -> Optional[float]: ...
    def defender_efficiency(self) -> float: ...
    def total_steps(self) -> int: ...


# Single place that knows how to build a fresh strategy instance by name.
# Shared with single-run mode's own strategy selection would prevent the
# two modes from drifting apart (e.g. on use_true_targets); wiring that
# up is a follow-up, not done here to avoid touching simulation_window.py
# in this step.
STRATEGY_FACTORIES: Dict[str, Callable[[], AllocationStrategy]] = {
    "Random": lambda: RandomStrategy(),
    "Greedy": lambda: GreedyStrategy(),
    "Bottleneck": lambda: BottleneckStrategy(use_true_targets=False),
}


@dataclass
class BatchResult:
    """
    Raw per-iteration results. Every strategy's list is the SAME length
    (== iterations_completed) and index-aligned across strategies: entry
    i in every strategy's list corresponds to the same generated layout.
    A failed (strategy, iteration) run is recorded as None rather than
    omitted, so index i always means "the same iteration" for everyone --
    this alignment is what lets an aggregator later compare strategies
    fairly on the same layout (e.g. for a win-count metric), instead of
    accidentally comparing iteration 3 of one strategy against iteration
    4 of another because 3 was silently dropped.
    """
    requested_iterations: int = 0
    iterations_completed: int = 0          # iterations where layout generation succeeded
    generation_failures: int = 0           # iterations skipped entirely (all strategies)
    strategy_results: Dict[str, List[Optional[SimulationStatistics]]] = field(default_factory=dict)
    strategy_failures: Dict[str, int] = field(default_factory=dict)  # per-strategy runtime failures

    def runs_completed(self, strategy_name: str) -> int:
        return sum(1 for c in self.strategy_results.get(strategy_name, []) if c is not None)


class BatchRunner:
    """
    Runs every strategy in `strategy_names` against `iterations` freshly
    generated layouts from the same ScenarioTemplate, so each iteration
    is a paired comparison: all strategies face the identical spawn
    positions and (if randomized) target assignment for that iteration.
    """

    def __init__(
        self,
        template: ScenarioTemplate,
        strategy_names: List[str],
        iterations: int,
        seed: Optional[int] = None,
    ):
        if iterations <= 0:
            raise ValueError("iterations must be a positive integer.")
        unknown = [n for n in strategy_names if n not in STRATEGY_FACTORIES]
        if unknown:
            raise ValueError(f"Unknown strategy name(s): {unknown}")

        # Fail fast on template/strategy-count mismatches (e.g.
        # predefined_targets=True with the wrong number of targets)
        # before spending time on any iteration.
        ScenarioGenerator.validate(template)

        self.template = template
        self.strategy_names = list(strategy_names)
        self.iterations = iterations
        self.generator = ScenarioGenerator(seed=seed)

    def run(self, on_progress: Optional[Callable[[int, int], None]] = None) -> BatchResult:
        """
        `on_progress(completed_iterations, total_iterations)` is called
        after every iteration (whether it succeeded or was skipped), so a
        GUI can update a progress indicator without this class knowing
        anything about the GUI.
        """
        result = BatchResult(requested_iterations=self.iterations)
        for name in self.strategy_names:
            result.strategy_results[name] = []
            result.strategy_failures[name] = 0

        for i in range(self.iterations):
            try:
                layout = self.generator.generate(self.template)
            except ScenarioValidationError:
                # This one iteration's random draw didn't leave enough
                # room (e.g. overlapping areas, unlucky sample) -- skip
                # it for every strategy so the paired comparison stays
                # intact, and keep going.
                result.generation_failures += 1
                if on_progress:
                    on_progress(i + 1, self.iterations)
                continue

            result.iterations_completed += 1

            for name in self.strategy_names:
                try:
                    calc = self._run_one(name, layout)
                    result.strategy_results[name].append(calc)
                except Exception:
                    # A single strategy failing on this layout (e.g. an
                    # unreachable target causing a pathfinding error)
                    # doesn't invalidate the other strategies' runs on
                    # the same layout. Record None (not a skip) so every
                    # strategy's list stays the same length and index i
                    # keeps meaning "this iteration" for every strategy.
                    result.strategy_failures[name] += 1
                    result.strategy_results[name].append(None)

            if on_progress:
                on_progress(i + 1, self.iterations)

        return result

    # ------------------------------------------------------------------
    def _run_one(self, strategy_name: str, layout: GeneratedLayout) -> SimulationStatistics:
        grid, defenders, attackers = self._build_agents(layout)
        strategy = STRATEGY_FACTORIES[strategy_name]()
        sim = Simulation(
            grid, defenders, attackers, list(self.template.targets),
            strategy, max_steps=self.template.max_steps,
        )
        sim.run()
        return StatisticsCalculator(sim.history)

    def _build_agents(self, layout: GeneratedLayout):
        """
        Builds a completely fresh Grid and fresh Agent objects from the
        layout's coordinates. This must happen once per strategy, not
        once per iteration -- Simulation mutates agent positions and the
        grid's occupancy marks, so the same objects can't be reused for
        a second strategy on the "same" layout.
        """
        width, height = self.template.grid.get_dimensions()
        grid = Grid(width, height, obstacles=list(self.template.obstacles))

        defenders: List[Agent] = [
            Agent(x, y, AgentType.DEFENDER) for (x, y) in layout.defender_positions
        ]

        attackers: List[Agent] = []
        for (x, y), target in zip(layout.attacker_positions, layout.attacker_targets):
            agent = Agent(x, y, AgentType.ATTACKER)
            agent.set_target(target)
            grid.mark_taken((x, y))
            attackers.append(agent)

        return grid, defenders, attackers