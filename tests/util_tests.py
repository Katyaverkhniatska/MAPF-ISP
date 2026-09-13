from allocation_strategies.allocation_strategy import AllocationStrategy
from core_components.agent import Agent
from core_components.agent_type import AgentType


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
