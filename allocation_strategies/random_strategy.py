import random
from allocation_strategies.allocation_strategy import AllocationStrategy
from core_components.agent import Agent
from core_components.grid import Grid, Vertex


class RandomStrategy(AllocationStrategy):
    """
    Randomly assigns targets to defenders.
    Does not consider distance, attacker positions, or any other factors.
    """

    def allocate(
        self,
        grid: Grid,
        defenders: list[Agent],
        targets: list[Vertex],
        attackers: list[Agent]
    ) -> dict[Agent, Vertex]:
        """
        Randomly shuffles targets and assigns one to each defender.

        Note:
            If there are more defenders than targets, some defenders
            will share a target. If there are more targets than defenders,
            some targets will be left unassigned.
        """
        if not defenders:
            return {}

        if not targets:
            raise ValueError("Cannot allocate defenders: no targets available.")

        shuffled_targets = targets.copy()
        random.shuffle(shuffled_targets)

        return {
            defender: shuffled_targets[i % len(shuffled_targets)]
            for i, defender in enumerate(defenders)
        }