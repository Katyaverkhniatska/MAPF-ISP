from typing import Dict, List, Optional, Set

from core_components.agent import Agent
from core_components.grid import Grid, Vertex
from allocation_strategies.allocation_strategy import AllocationStrategy
from pathfinding.path_finder import PathFinder
from simulation_engine.step_snapshot import AgentSnapshot, StepSnapshot


class Simulation:
    """
    Orchestrates a single-stage AAP simulation: defenders are allocated
    once via `strategy`, then every agent re-plans its next single step
    with A* every tick (LRA*-style), until every target is captured or
    protected, or max_steps is reached.

    Precondition: every attacker in `attackers` must already have its
    target set via Agent.set_target() before construction -- Simulation
    only assigns targets to *defenders*, via the allocation strategy.
    """

    def __init__(
        self,
        grid: Grid,
        defenders: List[Agent],
        attackers: List[Agent],
        targets: List[Vertex],
        strategy: AllocationStrategy,
        max_steps: int = 200,
    ):
        for attacker in attackers:
            if attacker.get_target() is None:
                raise ValueError(
                    "All attackers must have a target set before the "
                    "simulation starts; Simulation only allocates defenders."
                )

        self.grid = grid
        self.defenders = list(defenders)
        self.attackers = list(attackers)
        self.targets = list(targets)
        self.strategy = strategy
        self.max_steps = max_steps
        self.path_finder = PathFinder(grid)

        self._agent_ids: Dict[Agent, int] = {
            agent: i for i, agent in enumerate(self.defenders + self.attackers)
        }

        self.step_count = 0
        self.captured_targets: Set[Vertex] = set()
        self.protected_targets: Set[Vertex] = set()
        self.finished = False
        self.history: List[StepSnapshot] = []

        self.assignment = self._apply_allocation()
        # Duck-typed: only BottleneckStrategy sets this; Random/Greedy
        # simply don't have it, so getattr's default keeps them working
        # unmodified against the same Simulation.
        self.bottleneck_vertices: Set[Vertex] = set(
            getattr(strategy, "last_bottlenecks", set())
        )

        # Step 0: capture the initial arrangement before anyone moves,
        # in case an agent already starts on a target.
        self._update_target_states()
        self.history.append(self._build_snapshot())
        self._check_finished()

    # ------------------------------------------------------------------
    # Allocation (runs once -- this is single-stage, per the paper)
    # ------------------------------------------------------------------
    def _apply_allocation(self) -> Dict[Agent, Vertex]:
        assignment = self.strategy.allocate(
            self.grid, self.defenders, self.targets, self.attackers
        )
        for defender, target in assignment.items():
            defender.set_target(target)
        return assignment

    # ------------------------------------------------------------------
    # Stepping
    # ------------------------------------------------------------------
    def run(self) -> List[StepSnapshot]:
        while not self.finished:
            self.step()
        return self.history

    def step(self) -> Optional[StepSnapshot]:
        if self.finished:
            return None

        self.step_count += 1
        self._mark_all_agents_taken()
        # Defenders move first, then attackers -- matches the paper's
        # own turn-based framing (Fig. 6: "It is defenders' turn").
        self._move_group(self.defenders)
        self._move_group(self.attackers)
        self._update_target_states()

        snapshot = self._build_snapshot()
        self.history.append(snapshot)
        self._check_finished()
        return snapshot

    def _check_finished(self):
        unresolved = set(self.targets) - self.captured_targets - self.protected_targets
        if not unresolved or self.step_count >= self.max_steps:
            self.finished = True
            
    # ------------------------------------------------------------------
    # Movement (LRA*: replan one step at a time against current occupancy)
    # ------------------------------------------------------------------
    def _mark_all_agents_taken(self):
        for agent in self.defenders + self.attackers:
            self.grid.mark_taken(agent.get_position())

    def _move_group(self, agents: List[Agent]):
        for agent in agents:
            self._move_one(agent)

    def _move_one(self, agent: Agent):
        target = agent.get_target()
        pos = agent.get_position()
        if target is None or pos == target:
            return

        try:
            path = self.path_finder.find_path(pos, target)
        except ValueError:
            path = None

        if not path or len(path) < 2:
            # blocked or already arrived -- stay put
            return

        next_pos = path[1]
        # Defensive: PathFinder should already avoid TAKEN/obstacle cells
        # (Bottleneck already relies on this), so this should be
        # unreachable -- kept as a safety net against future changes.
        if self.grid.is_taken(next_pos) or self.grid.is_obstacle(next_pos):
            return

        self.grid.unmark_taken(pos)
        agent.move_to(*next_pos)
        self.grid.mark_taken(next_pos)

    # ------------------------------------------------------------------
    # Target resolution
    # ------------------------------------------------------------------
    def _update_target_states(self):
        positions = {a.get_position(): a for a in self.defenders + self.attackers}
        unresolved = set(self.targets) - self.captured_targets - self.protected_targets
        for target in unresolved:
            occupant = positions.get(target)
            if occupant is not None:
                if occupant in self.defenders:
                    self.protected_targets.add(target)
                else:
                    self.captured_targets.add(target)
                continue  # no need to check the other group if already resolved

            if self.strategy.__class__.__name__ == "BottleneckStrategy":
                # Check if any attacker can still reach this target
                attacker_can_reach = False
                for attacker in self.attackers:
                    if attacker.get_target() == target:
                        try:
                            path = self.path_finder.find_path(attacker.get_position(), target)
                            if path:
                                attacker_can_reach = True
                                break
                        except ValueError as e:
                            pass

                # If no attacker can reach the target, meaning that defenders 
                # successfully blocked all the paths, it is considered protected
                if not attacker_can_reach:
                    self.protected_targets.add(target)

    # ------------------------------------------------------------------
    # Snapshotting
    # ------------------------------------------------------------------
    def _snapshot_agent(self, agent: Agent) -> AgentSnapshot:
        return AgentSnapshot(
            agent_id=self._agent_ids[agent],
            position=agent.get_position(),
            target=agent.get_target(),
        )

    def _build_snapshot(self) -> StepSnapshot:
        return StepSnapshot(
            step=self.step_count,
            attackers=[self._snapshot_agent(a) for a in self.attackers],
            defenders=[self._snapshot_agent(d) for d in self.defenders],
            targets=list(self.targets),
            captured_targets=set(self.captured_targets),
            protected_targets=set(self.protected_targets),
            assignment=self.assignment,
            bottleneck_vertices=set(self.bottleneck_vertices),
        )