from typing import List, Set, Dict
from core_components.agent import Agent
from core_components.grid import Grid, Vertex

class StepSnapshot:
    step: int                           # Timestep number (0, 1, 2, ...)
    grid: Grid                          # Grid state (obstacles, taken cells)
    attackers: List[Agent]              # Current attacker positions
    defenders: List[Agent]              # Current defender positions
    targets: List[Vertex]               # All target locations
    reached_targets: Set[Vertex]        # Targets reached *this step*
    assignment: Dict[Agent, Vertex]     # Defender → assigned target
    
    def __repr__(self) -> str: # type: ignore
        """Human-readable snapshot for debugging"""
        