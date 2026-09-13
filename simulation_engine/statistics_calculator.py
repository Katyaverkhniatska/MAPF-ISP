from typing import Dict, List, Optional, Set

from simulation_engine.step_snapshot import StepSnapshot


class StatisticsCalculator:
    """
    Aggregated metrics derived from a full simulation run: the list of
    StepSnapshot objects Simulation records, from step 0 (the initial
    arrangement, before anyone moves) through the final step.

    A snapshot only carries immutable AgentSnapshot records (agent_id +
    position + target) rather than live Agent objects -- Agent isn't
    hashable/stable across steps the way agent_id is -- so every
    per-agent metric here is keyed by agent_id (int), matching the ids
    Simulation itself assigns via `_agent_ids`.

    Note: `captured_targets` / `protected_targets` on StepSnapshot are
    *cumulative* sets (they only grow across the run), not per-step
    deltas, so all the totals below are read off the final snapshot
    rather than summed across every snapshot.
    """

    snapshots: List[StepSnapshot]

    def __init__(self, snapshots: List[StepSnapshot]):
        self.snapshots = snapshots

        final = snapshots[-1] if snapshots else None

        self.__total_steps = final.step if final else 0
        self.__total_targets = len(snapshots[0].targets) if snapshots else 0

        self.__targets_captured = len(final.captured_targets) if final else 0
        self.__targets_protected = len(final.protected_targets) if final else 0
        self.__targets_reached = self.__targets_captured + self.__targets_protected

        self.__defenders_number = len(snapshots[0].defenders) if snapshots else 0
        self.__attackers_number = len(snapshots[0].attackers) if snapshots else 0

        self.__attacker_times: Dict[int, Optional[int]] = self._compute_arrival_times(
            is_attacker=True
        )
        self.__defender_times: Dict[int, Optional[int]] = self._compute_arrival_times(
            is_attacker=False
        )

        self.__targets_blocked_per_defender: Dict[int, int] = (
            self._compute_targets_blocked_per_defender()
        )
        self.__paths_intercepted: Dict[int, int] = self._compute_paths_intercepted()

    # ------------------------------------------------------------------
    # Per-agent time-to-target
    # ------------------------------------------------------------------
    def _compute_arrival_times(self, is_attacker: bool) -> Dict[int, Optional[int]]:
        """
        First step at which each agent's position equals its target.
        None if the agent has no target, or never arrives within the
        recorded snapshots (i.e. it was blocked for the whole run).
        """
        times: Dict[int, Optional[int]] = {}

        for snapshot in self.snapshots:
            agents = snapshot.attackers if is_attacker else snapshot.defenders
            for agent in agents:
                if agent.agent_id in times:
                    continue  # already recorded this agent's first arrival
                if agent.target is not None and agent.position == agent.target:
                    times[agent.agent_id] = snapshot.step

        # Every agent that took part gets an entry, even if it never arrived.
        if self.snapshots:
            seed = self.snapshots[0].attackers if is_attacker else self.snapshots[0].defenders
            for agent in seed:
                times.setdefault(agent.agent_id, None)

        return times

    # ------------------------------------------------------------------
    # Per-defender: how many targets it personally ended up protecting
    # ------------------------------------------------------------------
    def _compute_targets_blocked_per_defender(self) -> Dict[int, int]:
        if not self.snapshots:
            return {}

        counts: Dict[int, int] = {d.agent_id: 0 for d in self.snapshots[0].defenders}
        credited: Set = set()

        for snapshot in self.snapshots:
            newly_protected = snapshot.protected_targets - credited
            if not newly_protected:
                continue

            positions = {d.position: d.agent_id for d in snapshot.defenders}
            for target in newly_protected:
                defender_id = positions.get(target)
                if defender_id is not None:
                    counts[defender_id] = counts.get(defender_id, 0) + 1
            credited |= newly_protected

        return counts

    # ------------------------------------------------------------------
    # Per-attacker: how many recorded steps its path was intercepted by
    # a bottleneck vertex (i.e. it occupied one of the cells
    # BottleneckStrategy chose to block, rather than passing around it)
    # ------------------------------------------------------------------
    def _compute_paths_intercepted(self) -> Dict[int, int]:
        if not self.snapshots:
            return {}

        counts: Dict[int, int] = {a.agent_id: 0 for a in self.snapshots[0].attackers}

        for snapshot in self.snapshots:
            if not snapshot.bottleneck_vertices:
                continue
            for attacker in snapshot.attackers:
                if attacker.position in snapshot.bottleneck_vertices:
                    counts[attacker.agent_id] = counts.get(attacker.agent_id, 0) + 1

        return counts

    # ------------------------------------------------------------------
    # Public ratio metrics
    # ------------------------------------------------------------------
    def success_rate(self) -> float:
        """(targets_protected / total_targets) * 100"""
        if self.__total_targets == 0:
            return 0.0
        return (self.__targets_protected / self.__total_targets) * 100

    def average_attacker_time(self) -> float:
        """Mean steps-to-target across attackers that actually arrived."""
        times = [t for t in self.__attacker_times.values() if t is not None]
        if not times:
            return 0.0
        return sum(times) / len(times)

    def average_defender_time(self) -> float:
        """Mean steps-to-target across defenders that actually arrived."""
        times = [t for t in self.__defender_times.values() if t is not None]
        if not times:
            return 0.0
        return sum(times) / len(times)

    def defender_efficiency(self) -> float:
        """targets_protected / num_defenders"""
        if self.__defenders_number == 0:
            return 0.0
        return self.__targets_protected / self.__defenders_number

    # ------------------------------------------------------------------
    # Read-only accessors for the raw aggregates behind the ratios above
    # ------------------------------------------------------------------
    def total_steps(self) -> int:
        return self.__total_steps

    def total_targets(self) -> int:
        return self.__total_targets

    def targets_reached(self) -> int:
        return self.__targets_reached

    def targets_captured(self) -> int:
        return self.__targets_captured

    def targets_protected(self) -> int:
        return self.__targets_protected

    def attacker_times(self) -> Dict[int, Optional[int]]:
        return dict(self.__attacker_times)

    def defender_times(self) -> Dict[int, Optional[int]]:
        return dict(self.__defender_times)

    def targets_blocked_per_defender(self) -> Dict[int, int]:
        return dict(self.__targets_blocked_per_defender)

    def paths_intercepted(self) -> Dict[int, int]:
        return dict(self.__paths_intercepted)