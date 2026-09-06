from typing import Dict
from core_components.agent import Agent
from simulation_engine.step_snapshot import StepSnapshot


class StatisticsCalculator:
    """Aggregated metrics from a full simulation"""
    __total_steps: int
    __total_targets: int
    __targets_reached: int
    __targets_captured: int
    __targets_protected: int
    __total_time_elapsed: int     # in seconds
    
    __attacker_times: Dict[Agent, int]  # steps to reach target (or None if blocked)
    __defender_times: Dict[Agent, int]  # steps to reach assigned position
    
    __targets_blocked_per_defender: Dict[Agent, int]
    __paths_intercepted: Dict[Agent, int]

    snapshots: list[StepSnapshot]
    __defenders_number: int
    __attackers_number: int

    def __init__(self, snapshots: list[StepSnapshot]):
        self.snapshots = snapshots
        self.__total_steps = len(snapshots)
        self.__total_targets = len(snapshots[0].targets) if snapshots else 0
        self.__targets_reached = sum(len(snapshot.reached_targets) for snapshot in snapshots)
        self.__targets_captured = sum(len(snapshot.reached_targets) for snapshot in snapshots if snapshot.step == self.__total_steps - 1)
        self.__targets_protected = sum(len(snapshot.reached_targets) for snapshot in snapshots if snapshot.step == self.__total_steps - 1)
        self.__total_time_elapsed = sum(snapshot.step for snapshot in snapshots)

        self.__defenders_number = len(self.snapshots[0].defenders) if snapshots else 0
        self.__attackers_number = len(self.snapshots[0].attackers) if snapshots else 0

        # Initialize attacker and defender times
        self.__attacker_times = {agent: -1 for agent in self.snapshots[0].attackers}
        self.__defender_times = {agent: -1 for agent in self.snapshots[0].defenders}

        # Initialize targets blocked per defender and paths intercepted
        self.__targets_blocked_per_defender = {agent: -1 for agent in self.snapshots[0].attackers}
        self.__paths_intercepted = ... # type: ignore

    def success_rate(self) -> float:
        """(targets_protected / total_targets) * 100"""
        if self.__total_targets == 0:
            return 0.0
        return (self.__targets_protected / self.__total_targets) * 100

    def average_attacker_time(self) -> float:
        """Mean steps across all attackers (ignore blocked ones)"""
        times = [time for time in self.__attacker_times.values() if time is not None]
        if not times:
            return 0.0
        return sum(times) / len(times)

    def average_defender_time(self) -> float:
        """Mean steps across all defenders (ignore blocked ones)"""
        times = [time for time in self.__defender_times.values() if time is not None]
        if not times:
            return 0.0
        return sum(times) / len(times)
        
    def defender_efficiency(self) -> float: # type: ignore
        """targets_protected / num_defenders"""
        