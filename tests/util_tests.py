from allocation_strategies.allocation_strategy import AllocationStrategy
from core_components.agent import Agent
from core_components.agent_type import AgentType
from core_components.grid import Grid


def make_attacker(x, y, target):
    """Build an attacker and set its (already-known) target, satisfying
    Simulation's precondition that every attacker arrives with a target."""
    attacker = Agent(x, y, AgentType.ATTACKER)
    attacker.set_target(target)
    return attacker


def make_defender(x, y):
    return Agent(x, y, AgentType.DEFENDER)


class FixedStrategy(AllocationStrategy):
    """Test double: returns exactly the given defender->target mapping,
    ignoring grid/targets/attackers entirely. Lets tests pin exactly
    which defender goes where without depending on RandomStrategy's
    shuffling or GreedyStrategy's distance math. Subclasses
    AllocationStrategy (rather than just duck-typing .allocate) so it
    satisfies any isinstance checks the real code may do."""

    def __init__(self, mapping):
        self.mapping = mapping

    def allocate(self, grid, defenders, targets, attackers):
        return dict(self.mapping)


class FixedStrategyWithBottlenecks(FixedStrategy):
    """Same as FixedStrategy, but also exposes `last_bottlenecks`, the
    attribute Simulation duck-types on to distinguish BottleneckStrategy
    runs from Random/Greedy ones."""

    def __init__(self, mapping, bottlenecks):
        super().__init__(mapping)
        self.last_bottlenecks = bottlenecks


def print_simulation_step(grid: Grid, snapshot, title: str = ""):
    """Helper to print grid visualization and snapshot details at a step."""
    if title:
        print(f"\n--- {title} ---")
    
    # Map current positions from the snapshot
    defenders_pos = {a.position for a in snapshot.defenders}
    attackers_pos = {a.position for a in snapshot.attackers}
    targets_pos = set(snapshot.targets)

    print(f"Step {snapshot.step}:")

    height, width = grid.get_dimensions()
    for y in range(height):
        row_str = []
        for x in range(width):
            pos = (x, y)
            if grid.is_obstacle(pos):
                char = "# "
            elif pos in defenders_pos and pos in targets_pos:
                char = "D*"  # Defender on target
            elif pos in attackers_pos and pos in targets_pos:
                char = "A*"  # Attacker on target
            elif pos in defenders_pos:
                char = "D "
            elif pos in attackers_pos:
                char = "A "
            elif pos in targets_pos:
                char = "T "
            else:
                char = ". "
            row_str.append(char)
        print(" ".join(row_str))
        
    print(f"Captured Targets: {snapshot.captured_targets}")
    print(f"Protected Targets: {snapshot.protected_targets}")
    print(f"Bottlenecks Identified: {snapshot.bottleneck_vertices}")