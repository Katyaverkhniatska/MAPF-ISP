from typing import List, Set, Dict
from core_components.agent import Agent
from core_components.grid import Grid, Vertex

from dataclasses import dataclass, field
from typing import List, Set, Dict, Optional

@dataclass
class StepSnapshot:
    step: int
    grid: Grid
    attackers: List[Agent]
    defenders: List[Agent]
    targets: List[Vertex]
    captured_targets: Set[Vertex] = field(default_factory=set)    # attacker got there
    protected_targets: Set[Vertex] = field(default_factory=set)   # defender got there
    assignment: Dict[Agent, Vertex] = field(default_factory=dict)
    bottleneck_vertices: Set[Vertex] = field(default_factory=set) # for the GUI overlay
    def __repr__(self) -> str: # type: ignore
        """Human-readable snapshot for debugging"""
        