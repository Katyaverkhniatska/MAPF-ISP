import random
from typing import Dict, List, Set

from allocation_strategies.allocation_strategy import AllocationStrategy
from core_components.agent import Agent
from core_components.grid import Grid, Vertex
from core_components.grid_availability import GridAvailability
from pathfinding.path_finder import PathFinder


class BottleneckStrategy(AllocationStrategy):
    """
    Bottleneck Simulation Allocation.

    High-level idea: repeatedly simulate attacker paths towards their targets,
    find the vertex crossed by the most simulated paths, search its vicinity
    for a "bottleneck" (a gap between two separate groups of obstacles), and
    if one is found, assign defenders to block it. Vertices used to block a
    bottleneck become forbidden for subsequent path simulations, so the next
    iteration routes attackers around it and can reveal further bottlenecks.
    The process stops when there are no more available defenders or no more
    bottlenecks are found; any leftover defenders are assigned to remaining
    targets at random (as in RandomStrategy).

    Attacker targets: per Algorithm 1, defenders don't know attackers'
    true intended targets. A guess δ⁰_A is made once per allocate()
    call — one random target per attacker, drawn from the known target
    set — and every path simulation in the while-loop below is run
    against that fixed guess. Only the *paths* change between
    iterations, as newly-forbidden bottleneck vertices force re-routing.

    Set use_true_targets=True to bypass the guess and use each
    attacker's actual known target instead (useful as an idealized
    baseline for comparison, not paper-accurate).
    """

    MAX_VICINITY_RADIUS = 6  # expanding-square search limit around w

    def __init__(self, use_true_targets: bool = False):
        self.use_true_targets = use_true_targets
        self.attackers_starting_positions: Set[Vertex] = set()

    def allocate(
        self,
        grid: Grid,
        defenders: List[Agent],
        targets: List[Vertex],
        attackers: List[Agent],
    ) -> Dict[Agent, Vertex]:
        path_finder = PathFinder(grid)

        available_defenders: List[Agent] = list(defenders)
        available_targets: List[Vertex] = list(targets)
        forbidden: Set[Vertex] = set()
        self.attackers_starting_positions: Set[Vertex] = {a.get_position() for a in attackers}
        assignment: Dict[Agent, Vertex] = {}

        # δ⁰_A — fixed for the rest of this call, per Algorithm 1.
        guessed_targets = self._determine_attacker_targets(attackers, targets)

        while available_defenders:
            paths = self._simulate_attacker_paths(
                grid, attackers, guessed_targets, forbidden, path_finder
            )
            if not paths:
                print("No paths found for attackers; all are blocked or have no targets.")
                # No attacker has a viable path at all; nothing left to exploit.
                break

            frequency = self._vertex_frequency(paths)
            print("Vertex frequency:")
            print(frequency)
            w = self._select_frequent_vertex(frequency, available_defenders)
            print("The chosen vertex:")
            print(w)

            bottleneck = self._search_vicinity(grid, w, forbidden)
            print("Bottleneck:")
            print(bottleneck)
            if not bottleneck:
                break

            # Paper: D' subseteq Davailable, |D'| = |B|. If fewer defenders
            # remain than the bottleneck needs, block as much of it as we
            # can with what's left (the loop will then terminate naturally
            # since available_defenders becomes empty).
            chosen_defenders = available_defenders[: len(bottleneck)]
            bottleneck_vertices = list(bottleneck)[: len(chosen_defenders)]

            for defender, vertex in zip(chosen_defenders, bottleneck_vertices):
                assignment[defender] = vertex

            available_defenders = available_defenders[len(chosen_defenders):]
            forbidden |= set(bottleneck_vertices)

        # Leftover defenders (no bottleneck left to block, or ran out of
        # bottlenecks before running out of defenders): assign at random,
        # as in the paper's assignToDefenders(Tavailable, Davailable).
        # Sample WITHOUT replacement so leftover defenders spread across
        # distinct targets instead of piling onto the same one.
        random.shuffle(available_targets)
        for defender, target in zip(available_defenders, available_targets):
            assignment[defender] = target

        return assignment

    # ------------------------------------------------------------------
    # Step 0: guess attacker targets (δ⁰_A)
    # ------------------------------------------------------------------

    def _determine_attacker_targets(
        self, attackers: List[Agent], targets: List[Vertex]
    ) -> Dict[Agent, Vertex]:
        if self.use_true_targets:
            return {
                a: target
                for a in attackers 
                if (target := a.get_target()) is not None
            }
        return self._guess_attacker_targets(attackers, targets)

    def _guess_attacker_targets(
        self, attackers: List[Agent], targets: List[Vertex]
    ) -> Dict[Agent, Vertex]:
        """
        δ⁰_A: random guess of each attacker's intended target, made
        once per allocate() call. Sampled with replacement — several
        attackers may plausibly be guessed as heading for the same
        target.
        """
        if not targets:
            return {}
        return {attacker: random.choice(targets) for attacker in attackers}

    # ------------------------------------------------------------------
    # Step 1: simulate shortest paths of attackers to their targets
    # ------------------------------------------------------------------ 
    
    
    def _simulate_attacker_paths(
        self,
        grid: Grid,
        attackers: List[Agent],
        guessed_targets: Dict[Agent, Vertex],
        forbidden: Set[Vertex],
        path_finder: PathFinder,
    ) -> List[List[Vertex]]:
        """
        Computes each attacker's shortest path to its (known) target, avoiding
        forbidden vertices. Forbidden vertices are temporarily marked TAKEN on
        the grid for the duration of pathfinding, then restored, since the
        underlying AStar has no separate 'forbidden set' parameter.
        """
        previously_taken = self._mark_forbidden(grid, forbidden)
        try:
            paths = []
            for attacker in attackers:
                start = attacker.get_position()
                goal = guessed_targets.get(attacker)
                print(f"Attacker at {start} heading for {goal}")
                if goal is None or start == goal:
                    continue
                try:
                    path = path_finder.find_path(start, goal)
                except ValueError:
                    print(f"No path found for attacker at {start} to goal {goal}")
                    path = None
                
                if path:
                    paths.append(path)
            return paths
        finally:
            self._unmark_forbidden(grid, forbidden, previously_taken)

    def _mark_forbidden(self, grid: Grid, forbidden: Set[Vertex]) -> Set[Vertex]:
        """Marks forbidden vertices as TAKEN; returns those already TAKEN before (to restore correctly)."""
        already_taken = set()
        for pos in forbidden:
            if grid.is_taken(pos):
                already_taken.add(pos)
            else:
                grid.mark_taken(pos)
        return already_taken

    def _unmark_forbidden(self, grid: Grid, forbidden: Set[Vertex], already_taken: Set[Vertex]):
        for pos in forbidden:
            if pos not in already_taken:
                grid.unmark_taken(pos)

    # ------------------------------------------------------------------
    # Step 2: f(v) = number of paths passing through v
    # ------------------------------------------------------------------
    def _vertex_frequency(self, paths: List[List[Vertex]]) -> Dict[Vertex, int]:
        frequency: Dict[Vertex, int] = {}
        for path in paths:
            for vertex in path:
                frequency[vertex] = frequency.get(vertex, 0) + 1
        return frequency

    def _select_frequent_vertex(
        self, frequency: Dict[Vertex, int], available_defenders: List[Agent]
    ) -> Vertex:
        """
        w in argmax_v f(v), tie-broken by distance to an approximate
        location of the defenders (paper section 4.3: "The closer a vertex
        is to the defenders, the better chance the defenders have to
        capture it before the attackers pass through it... we use the
        distance from an approximate location of defenders in order to
        select one vertex of maximum frequency.").

        We approximate the defenders' location as the centroid of the
        currently available (unassigned) defenders.
        """
        max_freq = max(frequency.values())
        candidates = [v for v, f in frequency.items() 
                      if f == max_freq and v not in self.attackers_starting_positions]
        if len(candidates) == 1:
            return candidates[0]

        cx = sum(d.get_position()[0] for d in available_defenders) / len(available_defenders)
        cy = sum(d.get_position()[1] for d in available_defenders) / len(available_defenders)

        def dist_to_defenders(v: Vertex) -> float:
            return (v[0] - cx) ** 2 + (v[1] - cy) ** 2

        return min(candidates, key=dist_to_defenders)

    # ------------------------------------------------------------------
    # Step 3: searchVicinity(w) - expanding square, look for a gap between
    # two separate groups (connected components) of obstacles
    # ------------------------------------------------------------------
    def _search_vicinity(self, grid: Grid, w: Vertex, forbidden: Set[Vertex]) -> List[Vertex]:
        discovered_obstacles: Set[Vertex] = set()

        for radius in range(1, self.MAX_VICINITY_RADIUS + 1):
            discovered_obstacles |= self._fringe_obstacles(grid, w, radius)

            components = self._connected_components(discovered_obstacles)
            if len(components) > 1:
                gap = self._shortest_gap_between_components(grid, components, forbidden, w)
                if gap:
                    return gap
        return []

    def _fringe_obstacles(self, grid: Grid, center: Vertex, radius: int) -> Set[Vertex]:
        """Obstacle cells lying on the square 'ring' at Chebyshev distance == radius from center."""
        cx, cy = center
        fringe = set()
        for x in range(cx - radius, cx + radius + 1):
            for y in range(cy - radius, cy + radius + 1):
                if max(abs(x - cx), abs(y - cy)) != radius:
                    continue
                grid_width, grid_height = grid.get_dimensions()
                if 0 <= x < grid_width and 0 <= y < grid_height:
                    if grid.is_obstacle((x, y)):
                        fringe.add((x, y))
        return fringe

    def _connected_components(self, obstacles: Set[Vertex]) -> List[Set[Vertex]]:
        """
        Groups obstacle cells into connected components under 8-connectivity,
        per the paper's footnote: two cells are 'in distance 1' if they share
        at least one point (i.e. including diagonal neighbors).
        """
        unvisited = set(obstacles)
        components: List[Set[Vertex]] = []

        while unvisited:
            start = next(iter(unvisited))
            stack = [start]
            component = set()
            while stack:
                current = stack.pop()
                if current in component:
                    continue
                component.add(current)
                unvisited.discard(current)
                cx, cy = current
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        neighbor = (cx + dx, cy + dy)
                        if neighbor in unvisited:
                            stack.append(neighbor)
            components.append(component)

        return components

    def _shortest_gap_between_components(
        self,
        grid: Grid,
        components: List[Set[Vertex]],
        forbidden: Set[Vertex],
        w: Vertex,
    ) -> List[Vertex]:
        """
        Finds the shortest path of passable, non-forbidden cells connecting
        one obstacle component to another (the "gap" / bottleneck itself),
        via multi-source BFS from the first component to any cell adjacent
        to a different component.

        When several cells are tied for the shortest such path, the tie is
        broken by picking whichever tied cell is closest to `w` — the
        frequency hotspot that triggered this vicinity search in the first
        place — rather than whichever cell a fixed dx/dy loop order happens
        to enqueue first. Without this, cells that are diagonally adjacent
        to an obstacle (touches_other_component uses 8-connectivity, per
        the paper's footnote on obstacle grouping) can tie with, and be
        returned ahead of, the cell that actually sits directly between the
        two obstacle groups — even though the latter is the more natural
        "real" gap and the one closest to where the attacker traffic was
        concentrated.
        """
        first, *rest = components
        other_obstacles = set().union(*rest) if rest else set()
        if not other_obstacles:
            return []

        def passable(pos: Vertex) -> bool:    
            if not pos in forbidden:
                return grid.is_passable(pos)
            return False

        def touches_other_component(pos: Vertex) -> bool:
            x, y = pos
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                if (x + dx, y + dy) in other_obstacles:
                    return True
            return False

        def dist_to_w(pos: Vertex) -> float:
            return (pos[0] - w[0]) ** 2 + (pos[1] - w[1]) ** 2

        # Multi-source BFS from all passable cells adjacent to `first`,
        # processed level-by-level so we can collect every cell that
        # touches the other component at the minimum depth, instead of
        # stopping at the first one dequeued.
        from collections import deque

        dist: Dict[Vertex, int] = {}
        parent: Dict[Vertex, Vertex | None]= {}
        queue = deque()

        for ox, oy in first:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    candidate = (ox + dx, oy + dy)
                    if passable(candidate) and candidate not in dist:
                        dist[candidate] = 0
                        parent[candidate] = None
                        queue.append(candidate)

        best_depth = None
        best_candidates: List[Vertex] = []

        while queue:
            current = queue.popleft()
            depth = dist[current]

            # BFS processes cells in non-decreasing depth order, so once
            # we've moved past the depth at which a solution was found,
            # every remaining candidate is farther and can be ignored.
            if best_depth is not None and depth > best_depth:
                break

            if touches_other_component(current):
                if best_depth is None:
                    best_depth = depth
                if depth == best_depth:
                    best_candidates.append(current)
                # A touching cell is a terminal candidate; don't expand
                # past it, but other same-depth cells still need checking.
                continue

            cx, cy = current
            for dx, dy in [(-1, 0), (0, 1), (0, -1), (1, 0)]:
                neighbor = (cx + dx, cy + dy)
                if passable(neighbor) and neighbor not in dist:
                    dist[neighbor] = depth + 1
                    parent[neighbor] = current
                    queue.append(neighbor)

        if not best_candidates:
            return []

        target = min(best_candidates, key=dist_to_w)
        path = [target]
        curr = path[-1]
        while (curr := parent.get(curr)) is not None:
            path.append(curr)
        return list(reversed(path))