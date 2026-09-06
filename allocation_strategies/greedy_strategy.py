import math
from allocation_strategies.allocation_strategy import AllocationStrategy
from core_components.agent import Agent
from core_components.grid import Grid, Vertex


class GreedyStrategy(AllocationStrategy):
    """
    Assigns each defender to the closest available target using Euclidean distance.
    Each target is assigned to at most one defender (greedy one-to-one matching).
    If there are more defenders than targets, remaining defenders share
    the closest target available.
    """

    def allocate(
        self,
        grid: Grid,
        defenders: list[Agent],
        targets: list[Vertex],
        attackers: list[Agent]
    ) -> dict[Agent, tuple[int, int]]:
        """
        Greedily assigns each defender to the nearest unassigned target.

        Note:
            Attackers are not considered in this strategy.
            Assignment is not globally optimal — it is greedy per defender.
        """
        if not defenders or not targets:
            return {}

        available_targets = targets.copy()
        assignment = {}

        for defender in defenders:
            if available_targets:
                closest = min(
                    available_targets,
                    key=lambda t: math.dist(defender.get_position(), t)
                )
                assignment[defender] = closest
                available_targets.remove(closest)
            else:
                # More defenders than targets — assign closest from all targets
                assignment[defender] = min(
                    targets,
                    key=lambda t: math.dist(defender.get_position(), t)
                )

        return assignment