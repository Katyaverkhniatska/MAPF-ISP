from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from core_components.agent import Agent
from core_components.grid import Vertex


@dataclass(frozen=True)
class AgentSnapshot:
    """
    An immutable capture of one agent's state at a single step.
    Deliberately NOT a reference to the live Agent object -- position is
    a plain tuple (already immutable), so this can't drift when the real
    Agent moves on later steps.
    """
    agent_id: int
    position: Vertex
    target: Optional[Vertex]


@dataclass
class StepSnapshot:
    step: int
    attackers: List[AgentSnapshot]
    defenders: List[AgentSnapshot]
    targets: List[Vertex]
    captured_targets: Set[Vertex] = field(default_factory=set)   # attacker got there first
    protected_targets: Set[Vertex] = field(default_factory=set)  # defender got there first
    assignment: Dict[Agent, Vertex] = field(default_factory=dict)
    bottleneck_vertices: Set[Vertex] = field(default_factory=set)

    @property
    def empty_targets(self) -> Set[Vertex]:
        return set(self.targets) - self.captured_targets - self.protected_targets

    def __repr__(self) -> str:
        return (
            f"Step {self.step}: captured={len(self.captured_targets)}, "
            f"protected={len(self.protected_targets)}, "
            f"empty={len(self.empty_targets)}"
        )