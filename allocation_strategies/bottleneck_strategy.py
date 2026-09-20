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
        if not defenders:
            return {}

        path_finder = PathFinder(grid)

        available_defenders: List[Agent] = list(defenders)
        available_targets: List[Vertex] = list(targets)
        forbidden: Set[Vertex] = set()
        self.attackers_starting_positions = {a.get_position() for a in attackers}
        assignment: Dict[Agent, Vertex] = {}

        self.VICINITY_RADIUS = max(grid.get_dimensions())

        guessed_targets = self._determine_attacker_targets(attackers, targets)

        while available_defenders:
            paths = self._simulate_attacker_paths(
                grid, attackers, guessed_targets, forbidden, path_finder
            )
            if not paths:
                break

            frequency = self._vertex_frequency(paths)
            w = self._select_frequent_vertex(frequency, available_defenders)

            bottleneck = self._search_vicinity(grid, w, forbidden, attackers, guessed_targets, paths, path_finder)
            if not bottleneck:
                break

            chosen_defenders = available_defenders[: len(bottleneck)]
            bottleneck_vertices = list(bottleneck)[: len(chosen_defenders)]

            for defender, vertex in zip(chosen_defenders, bottleneck_vertices):
                assignment[defender] = vertex

            available_defenders = available_defenders[len(chosen_defenders):]
            forbidden |= set(bottleneck_vertices)

        # Assign leftover defenders to remaining targets
        if available_targets:
            random.shuffle(available_targets)
            for defender, target in zip(available_defenders, itertools.cycle(available_targets)):
                assignment[defender] = target

            available_defenders = []

        if available_defenders:
            raise ValueError(
                f"Failed to allocate all defenders: {len(available_defenders)} defender(s) "
                "left unassigned because no targets were available."
            )

        return assignment

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
        if not targets:
            return {}
        return {attacker: random.choice(targets) for attacker in attackers}

    def _simulate_attacker_paths(
        self,
        grid: Grid,
        attackers: List[Agent],
        guessed_targets: Dict[Agent, Vertex],
        forbidden: Set[Vertex],
        path_finder: PathFinder,
    ) -> List[List[Vertex]]:
        previously_taken = self._mark_forbidden(grid, forbidden)
        try:
            paths = []
            for attacker in attackers:
                start = attacker.get_position()
                goal = guessed_targets.get(attacker)
                if goal is None or start == goal:
                    continue
                try:
                    path = path_finder.find_path(start, goal)
                except ValueError:
                    path = None
                
                if path:
                    paths.append(path)
            return paths
        finally:
            self._unmark_forbidden(grid, forbidden, previously_taken)

    def _mark_forbidden(self, grid: Grid, forbidden: Set[Vertex]) -> Set[Vertex]:
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

    def _vertex_frequency(self, paths: List[List[Vertex]]) -> Dict[Vertex, int]:
        frequency: Dict[Vertex, int] = {}
        for path in paths:
            for vertex in path:
                frequency[vertex] = frequency.get(vertex, 0) + 1
        return frequency

    def _select_frequent_vertex(
        self, frequency: Dict[Vertex, int], available_defenders: List[Agent]
    ) -> Vertex:
        allowed_frequent = [(v, f) for (v, f) in frequency.items() if v not in self.attackers_starting_positions]

        if not allowed_frequent:
            raise RuntimeError("No available positions for defenders.")

        allowed_frequent_dict = dict(allowed_frequent)
        
        max_freq = max(allowed_frequent_dict.values())
        candidates = [v for v, f in allowed_frequent_dict.items() if f == max_freq]

        if len(candidates) == 1:
            return candidates[0]

        cx = sum(d.get_position()[0] for d in available_defenders) / len(available_defenders)
        cy = sum(d.get_position()[1] for d in available_defenders) / len(available_defenders)

        def dist_to_defenders(v: Vertex) -> float:
            return (v[0] - cx) ** 2 + (v[1] - cy) ** 2

        return min(candidates, key=dist_to_defenders)

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
        discovered_obstacles: Set[Vertex] = set()

        for radius in range(1, max(self.VICINITY_RADIUS, 3) + 1):
            discovered_obstacles |= self._fringe_obstacles(grid, w, radius)
            if len(discovered_obstacles) < 2:
                continue

            components = self._local_obstacle_components(grid, discovered_obstacles, w, radius)

            if len(components) > 1:
                gap = self._shortest_gap_between_components(grid, components, forbidden, w)
                
                if gap and self._is_real_bottleneck(
                    grid, gap, forbidden, attackers, guessed_targets, original_paths, path_finder
                ):
                    return gap

        return []

    def _local_obstacle_components(
        self, grid: Grid, local_obstacles: Set[Vertex], w: Vertex, radius: int
    ) -> List[Set[Vertex]]:
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
        test_forbidden = forbidden | set(candidate_gap)
        new_paths = self._simulate_attacker_paths(
            grid, attackers, guessed_targets, test_forbidden, path_finder
        )

        if len(new_paths) != len(original_paths):
            return True

        orig_costs = [len(p) for p in original_paths]
        new_costs = [len(p) for p in new_paths]

        return orig_costs != new_costs

    def _fringe_obstacles(self, grid: Grid, center: Vertex, radius: int) -> Set[Vertex]:
        cx, cy = center
        fringe = set()
        grid_width, grid_height = grid.get_dimensions()
        for x in range(cx - radius, cx + radius + 1):
            for y in range(cy - radius, cy + radius + 1):
                if max(abs(x - cx), abs(y - cy)) != radius:
                    continue
                if 0 <= x < grid_width and 0 <= y < grid_height:
                    if grid.is_obstacle((x, y)):
                        fringe.add((x, y))
        return fringe

    def _shortest_gap_between_components(
        self,
        grid: Grid,
        components: List[Set[Vertex]],
        forbidden: Set[Vertex],
        w: Vertex,
    ) -> List[Vertex]:
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