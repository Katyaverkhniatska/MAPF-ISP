from abc import ABC, abstractmethod
from core_components.agent import Agent
from core_components.grid import Grid


class AllocationStrategy(ABC):
    """
    Abstract base class defining the interface that all allocation strategies must implement.
    A strategy takes the current grid state, list of defenders, list of targets,
    and list of attackers, and returns a target assignment for each defender.
    """

    @abstractmethod
    def allocate(
        self,
        grid: Grid,
        defenders: list[Agent],
        targets: list[tuple[int, int]],
        attackers: list[Agent]
    ) -> dict[Agent, tuple[int, int]]:
        """
        Assign each defender a target position to move towards.

        Args:
            grid:      Current grid state
            defenders: List of defender agents to be assigned
            targets:   List of (x, y) target positions on the grid
            attackers: List of attacker agents (used by smarter strategies like Bottleneck)

        Returns:
            A dictionary mapping each defender Agent to a target (x, y) position
        """
        pass