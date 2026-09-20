import itertools
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

    def __init__(self, use_true_targets: bool = False):
        self.use_true_targets = use_true_targets
        self.attackers_starting_positions: Set[Vertex] = set()
        self.VICINITY_RADIUS = 0

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

        max_vicinity_radius = max(grid.get_dimensions())  # upper bound on how far to search for a gap
        self.VICINITY_RADIUS = max_vicinity_radius

        # δ⁰_A — fixed for the rest of this call, per Algorithm 1.
        guessed_targets = self._determine_attacker_targets(attackers, targets)

        while available_defenders:
            paths = self._simulate_attacker_paths(
                grid, attackers, guessed_targets, forbidden, path_finder
            )
            if not paths:
                # No attacker has a viable path at all; nothing left to exploit.
                break

            frequency = self._vertex_frequency(paths)
            w = self._select_frequent_vertex(frequency, available_defenders)
            print("The chosen vertex:")
            print(w)

            bottleneck = self._search_vicinity(grid, w, forbidden, attackers, guessed_targets, paths, path_finder)
            print("Bottleneck:")
            print(bottleneck)
            if not bottleneck:
                break

            # Paper: D' subseteq Davailable, |D'| = |B|. If fewer defenders
            # remain than the bottleneck needs, block as much of it as we
            # can with what's left (the loop will then terminate naturally
            # since available_defenders becomes empty).
            chosen_defenders = available_defenders[: len(bottleneck)]
            print(f"Chosen defenders (up to {len(bottleneck)}):")
            print(chosen_defenders)
            bottleneck_vertices = list(bottleneck)[: len(chosen_defenders)]

            for defender, vertex in zip(chosen_defenders, bottleneck_vertices):
                assignment[defender] = vertex

            available_defenders = available_defenders[len(chosen_defenders):]
            forbidden |= set(bottleneck_vertices)

        # Leftover defenders (no bottleneck left to block, or ran out of
        # bottlenecks before running out of defenders): assign at random,
        # as in the paper's assignToDefenders(Tavailable, Davailable).
        if available_targets:
            random.shuffle(available_targets)
            # Cycle through available targets so every defender gets assigned
            for defender, target in zip(available_defenders, itertools.cycle(available_targets)):
                assignment[defender] = target

            available_defenders = []

        if available_defenders:
            print(
                f"Warning: {len(available_defenders)} defenders left unassigned; "
                "not enough targets to assign them to."
            )
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
                # print(f"Attacker at {start} heading for {goal}")
                if goal is None or start == goal:
                    continue
                try:
                    path = path_finder.find_path(start, goal)
                except ValueError:
                    # print(f"No path found for attacker at {start} to goal {goal}")
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

        allowed_frequent = [(v, f) for (v, f) in frequency.items() if v not in self.attackers_starting_positions]

        # All the paths were containing the starting vertices only, which inherently means agents were already in targets
        if not allowed_frequent:
            RuntimeError("No available positions for defenders")

        allowed_frequent = dict(allowed_frequent)
        
        max_freq = max(allowed_frequent.values())
        candidates = [v for v, f in frequency.items() if f == max_freq]

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
    def _search_vicinity(
        self,
        grid: Grid,
        w: Vertex,
        forbidden: Set[Vertex],
        attackers: List[Agent],
        guessed_targets: Dict[Agent, Vertex],
        original_paths: List[List[Vertex]],
        path_finder: PathFinder,
    ) -> List[Vertex]:
        """
        Searches vicinity of hotspot 'w' using local obstacle component grouping.
        """
        discovered_obstacles: Set[Vertex] = set()

        for radius in range(1, max(self.VICINITY_RADIUS, 3) + 1):
            # 1. Accumulate obstacles on the fringe ring (Chebyshev distance = radius)
            discovered_obstacles |= self._fringe_obstacles(grid, w, radius)
            if len(discovered_obstacles) < 2:
                continue

            # 2. Group obstacles LOCALLY within the current window bounds
            # Prevents outer map borders from merging separate internal walls
            components = self._local_obstacle_components(grid, discovered_obstacles, w, radius)

            if len(components) > 1:
                # 3. Find shortest 4-connected passable path between local components
                gap = self._shortest_gap_between_components(grid, components, forbidden, w)
                
                # 4. Verify candidate gap actually alters attacker trajectories
                if gap and self._is_real_bottleneck(
                    grid, gap, forbidden, attackers, guessed_targets, original_paths, path_finder
                ):
                    return gap

        return []

    
    def _local_obstacle_components(
        self, grid: Grid, local_obstacles: Set[Vertex], w: Vertex, radius: int
    ) -> List[Set[Vertex]]:
        """
        Groups local_obstacles into components using 8-connectivity, restricting
        flood-fill strictly to vertices inside the Chebyshev window W(w, radius).
        """
        wx, wy = w
        window_min_x, window_max_x = wx - radius, wx + radius
        window_min_y, window_max_y = wy - radius, wy + radius

        def in_window(pos: Vertex) -> bool:
            x, y = pos
            return window_min_x <= x <= window_max_x and window_min_y <= y <= window_max_y

        unvisited = set(local_obstacles)
        components = []

        while unvisited:
            seed = unvisited.pop()
            component = {seed}
            queue = [seed]

            while queue:
                curr = queue.pop()
                cx, cy = curr

                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nbr = (cx + dx, cy + dy)
                        if (
                            in_window(nbr)
                            and grid.is_in_bounds(nbr)
                            and grid.is_obstacle(nbr)
                        ):
                            if nbr in unvisited:
                                component.add(nbr)
                                unvisited.remove(nbr)
                                queue.append(nbr)

            components.append(component)

        return components

    def _global_obstacle_components(self, grid: Grid, local_obstacles: Set[Vertex]) -> List[Set[Vertex]]:
        """
        Clusters local_obstacles into components based on whether they are connected 
        via ANY continuous 8-connected obstacle path across the full grid.
        """
        unvisited = set(local_obstacles)
        components = []

        while unvisited:
            seed = unvisited.pop()
            component = {seed}
            
            # Flood-fill across the global grid obstacle map starting from seed
            queue = [seed]
            visited_global = {seed}

            while queue:
                curr = queue.pop()
                cx, cy = curr
                
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nbr = (cx + dx, cy + dy)
                        if grid.is_in_bounds(nbr) and grid.is_obstacle(nbr) and nbr not in visited_global:
                            visited_global.add(nbr)
                            queue.append(nbr)
                            if nbr in unvisited:
                                component.add(nbr)
                                unvisited.remove(nbr)

            components.append(component)

        return components

    def _is_real_bottleneck(
        self,
        grid: Grid,
        candidate_gap: List[Vertex],
        forbidden: Set[Vertex],
        attackers: List[Agent],
        guessed_targets: Dict[Agent, Vertex],
        original_paths: List[List[Vertex]],
        path_finder: PathFinder,
    ) -> bool:
        """
        Paper Section 4.3: Validates candidate bottleneck by re-simulating paths.
        Returns True if blocking candidate_gap changes attacker paths or path lengths.
        """
        test_forbidden = forbidden | set(candidate_gap)
        new_paths = self._simulate_attacker_paths(
            grid, attackers, guessed_targets, test_forbidden, path_finder
        )

        # If attackers are completely blocked or their path lengths change, it is a true bottleneck
        if len(new_paths) != len(original_paths):
            return True

        orig_costs = [len(p) for p in original_paths]
        new_costs = [len(p) for p in new_paths]

        return orig_costs != new_costs

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
        Groups obstacle cells into connected components under 4-connectivity,
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
        via multi-source BFS.

        - Obstacle proximity uses 8-connectivity (sharing at least one vertex).
        - Grid path propagation uses 4-connectivity (orthogonal agent steps).
        """
        first, *rest = components
        other_obstacles = set().union(*rest) if rest else set()
        if not other_obstacles:
            return []

        def passable(pos: Vertex) -> bool:    
            if pos not in forbidden:
                return grid.is_passable(pos)
            return False

        def touches_other_component(pos: Vertex) -> bool:
            x, y = pos
            # Corrected: Check all 8 neighboring directions for obstacle contact
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    if (x + dx, y + dy) in other_obstacles:
                        return True
            return False

        def dist_to_w(pos: Vertex) -> float:
            return (pos[0] - w[0]) ** 2 + (pos[1] - w[1]) ** 2

        from collections import deque

        dist: Dict[Vertex, int] = {}
        parent: Dict[Vertex, Vertex | None] = {}
        queue = deque()

        # Seed initial passable cells 8-adjacent to the first obstacle component
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

            if best_depth is not None and depth > best_depth:
                break

            if touches_other_component(current):
                if best_depth is None:
                    best_depth = depth
                if depth == best_depth:
                    best_candidates.append(current)
                continue

            cx, cy = current
            # Path traversal across empty grid spaces strictly uses 4-connectivity
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
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