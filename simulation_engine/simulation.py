from typing import Dict, List, Optional, Set

from allocation_strategies.bottleneck_strategy import BottleneckStrategy
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
        # print(f"\nStep: {self.step_count}")
        # print("\nMark taken:")
        self._mark_all_agents_taken()
        # Defenders move first, then attackers
        # print(f"\nMove defenders:")
        self._move_group(self.defenders)
        # print(f"\nMove attackers:")
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
            # print(f" {agent.get_position()}")

    def _move_group(self, agents: List[Agent]):
        for agent in agents:
            self._move_one(agent)

    def _move_one(self, agent: Agent):
        target = agent.get_target()
        pos = agent.get_position()
        # print(f"\n  Moving ({agent}) from {pos}")
        if target is None or pos == target:
            return

        # Temporarily unmark start node so PathFinder isn't blocked by self
        was_taken = self.grid.is_taken(pos)
        if was_taken:
            self.grid.unmark_taken(pos)

        try:
            path = self.path_finder.find_path(pos, target)
        except ValueError:
            path = None
        finally:
            if was_taken:
                self.grid.mark_taken(pos)

        if not path or len(path) < 2:
            # print(f"    Path {path} is not available")
            # blocked or already arrived -- stay put
            return

        next_pos = path[1]
        # print(f"    to {next_pos}")
        # Defensive: PathFinder should already avoid TAKEN/obstacle cells
        # (Bottleneck already relies on this), so this should be
        # unreachable -- kept as a safety net against future changes.
        if self.grid.is_taken(next_pos) or self.grid.is_obstacle(next_pos):
            # print("TRIED TO MOVE TO TAKEN OR OBSTACLE")
            return

        self.grid.unmark_taken(pos)
        agent.move_to(*next_pos)
        self.grid.mark_taken(next_pos)

    # ------------------------------------------------------------------
    # Target resolution
    # ------------------------------------------------------------------
    def _update_target_states(self):
        defender_positions = {d.get_position() for d in self.defenders}
        attacker_positions = {a.get_position() for a in self.attackers}

        unresolved = set(self.targets) - self.captured_targets - self.protected_targets
        for target in unresolved:
            if target in defender_positions:
                self.protected_targets.add(target)
                continue
            elif target in attacker_positions:
                self.captured_targets.add(target)
                continue

            if isinstance(self.strategy, BottleneckStrategy):
                # Only trust "no path" as PERMANENT if every defender that
                # could be forming the cut has already settled on its
                # assigned bottleneck vertex -- otherwise it's a transient
                # artifact of agents still moving into place.
                settled = all(
                    d.get_position() == d.get_target()
                    for d in self.defenders
                    if d.get_target() not in self.targets
                )
                if not settled:
                    continue  # don't evaluate reachability yet this tick
                
                attacker_can_reach = False
                for attacker in self.attackers:
                    if attacker.get_target() == target:
                        a_pos = attacker.get_position()
                        
                        # Temporarily unmark ONLY this attacker's start position 
                        # so pathfinding isn't blocked by its own cell, 
                        # while leaving defender blockades active on the grid.
                        was_taken = self.grid.is_taken(a_pos)
                        if was_taken:
                            self.grid.unmark_taken(a_pos)

                        try:
                            path = self.path_finder.find_path(a_pos, target)
                            if path:
                                attacker_can_reach = True
                                break
                        except ValueError:
                            pass
                        finally:
                            if was_taken:
                                self.grid.mark_taken(a_pos)

                # If defenders block all paths to this target, it is protected
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