import itertools
import random
from collections import deque
from typing import Dict, List, Set

from allocation_strategies.allocation_strategy import AllocationStrategy
from core_components.agent import Agent
from core_components.grid import Grid, Vertex
from pathfinding.path_finder import PathFinder


class BottleneckStrategy(AllocationStrategy):
    """
    Bottleneck Simulation Allocation directly following Algorithm 1 in
    Ivanová & Surynek (2017).
    """

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

        if not defenders:
            return {}
        if not targets:
            raise ValueError("Cannot allocate defenders: no targets available.")

        path_finder = PathFinder(grid)
        available_defenders: List[Agent] = list(defenders)
        available_targets: List[Vertex] = list(targets)
        forbidden: Set[Vertex] = set()
        self.attackers_starting_positions = {a.get_position() for a in attackers}
        assignment: Dict[Agent, Vertex] = {}

        # Fixed guess delta_A' made once at the start (Algorithm 1)
        guessed_targets = self._determine_attacker_targets(attackers, targets)

        counter = 0
        while available_defenders:
            print(f"Count {counter}")
            counter+=1
            # Step 1: Simulate shortest paths avoiding forbidden nodes
            paths = self._simulate_attacker_paths(
                grid, attackers, guessed_targets, forbidden, path_finder
            )
            print("Paths:")
            for p in paths:
                print(f"    {p}")
            if not paths:
                break

            # Step 2: Vertex frequency computation
            frequency = self._vertex_frequency(paths)
            if not frequency:
                break

            print(f"\nFrequencies: ")
            for V in frequency.keys():
                print(f"    vertex: {V}, freq.: {frequency.get(V)}")

            # Step 3: Select w in argmax f(v) closest to defender centroid
            w = self._select_frequent_vertex(frequency, available_defenders)

            # Step 4: Search vicinity of w for bottleneck B
            bottleneck = self._search_vicinity(
                grid, w, forbidden, attackers, guessed_targets, paths, path_finder
            )

            if not bottleneck:
                break  # Algorithm 1 breaks if B is empty

            # Step 5: Assign defenders to bottleneck B
            num_to_assign = min(len(available_defenders), len(bottleneck))
            chosen_defenders = available_defenders[:num_to_assign]
            bottleneck_vertices = bottleneck[:num_to_assign]

            for defender, vertex in zip(chosen_defenders, bottleneck_vertices):
                assignment[defender] = vertex

            available_defenders = available_defenders[num_to_assign:]
            forbidden |= set(bottleneck_vertices)

        # Fallback: assign remaining defenders to random targets (Algorithm 1)
        if available_targets and available_defenders:
            random.shuffle(available_targets)
            for defender, target in zip(available_defenders, itertools.cycle(available_targets)):
                assignment[defender] = target
            available_defenders = []

        return assignment

    def _determine_attacker_targets(
        self, attackers: List[Agent], targets: List[Vertex]
    ) -> Dict[Agent, Vertex]:
        if self.use_true_targets:
            return {a: target for a in attackers if (target := a.get_target()) is not None}
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
                if vertex not in self.attackers_starting_positions:
                    frequency[vertex] = frequency.get(vertex, 0) + 1
        return frequency

    def _select_frequent_vertex(
        self, frequency: Dict[Vertex, int], available_defenders: List[Agent]
    ) -> Vertex:
        max_freq = max(frequency.values())
        candidates = [v for v, f in frequency.items() if f == max_freq]

        if len(candidates) == 1:
            return candidates[0]

        # Centroid tie-breaking as specified in Section 4.3
        cx = sum(d.get_position()[0] for d in available_defenders) / len(available_defenders)
        cy = sum(d.get_position()[1] for d in available_defenders) / len(available_defenders)

        def dist_to_centroid(v: Vertex) -> float:
            return (v[0] - cx) ** 2 + (v[1] - cy) ** 2

        return min(candidates, key=dist_to_centroid)

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
        max_radius = max(grid.get_dimensions())

        for radius in range(1, max_radius + 1):
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

    def _local_obstacle_components(
        self, grid: Grid, local_obstacles: Set[Vertex], w: Vertex, radius: int
    ) -> List[Set[Vertex]]:
        wx, wy = w
        window_min_x, window_max_x = wx - radius, wx + radius
        window_min_y, window_max_y = wy - radius, wy + radius

        def in_window(pos: Vertex) -> bool:
            return window_min_x <= pos[0] <= window_max_x and window_min_y <= pos[1] <= window_max_y

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
                        if in_window(nbr) and grid.is_in_bounds(nbr) and grid.is_obstacle(nbr):
                            if nbr in unvisited:
                                component.add(nbr)
                                unvisited.remove(nbr)
                                queue.append(nbr)

            components.append(component)

        components.sort(key=lambda c: (min(v[0] for v in c), min(v[1] for v in c)))
        return components

    def _shortest_gap_between_components(
        self,
        grid: Grid,
        components: List[Set[Vertex]],
        forbidden: Set[Vertex],
        w: Vertex,
    ) -> List[Vertex]:
        print(f"\nIn _shortest_gap_between_components")
        print(f"W: {w}")
        print("Components:")
        for c in components:
            print(f"    {c}")
        first, *rest = components
        print(f"Fist: {first}")
        other_obstacles = set().union(*rest) if rest else set()
        if not other_obstacles:
            return []
        print(f"Other obstacles: {other_obstacles}")

        def passable(pos: Vertex) -> bool:
            return pos not in forbidden and grid.is_passable(pos)

        def touches_other_component(pos: Vertex) -> bool:
            x, y = pos
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    if (x + dx, y + dy) in other_obstacles:
                        return True
            return False

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

        target = min(best_candidates, key=lambda pos: (pos[0] - w[0]) ** 2 + (pos[1] - w[1]) ** 2)
        path = [target]
        curr = path[-1]
        while (curr := parent.get(curr)) is not None:
            path.append(curr)
        return list(reversed(path))

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
        Validates if blocking candidate_gap alters attacker trajectories,
        matching Section 4.3 ("If updated paths are unchanged...").
        """
        test_forbidden = forbidden | set(candidate_gap)
        new_paths = self._simulate_attacker_paths(
            grid, attackers, guessed_targets, test_forbidden, path_finder
        )

        # Path count changed (some attacker cut off entirely)
        if len(new_paths) != len(original_paths):
            return True

        # Path trajectories/lengths changed (detours forced)
        orig_costs = [len(p) for p in original_paths]
        new_costs = [len(p) for p in new_paths]

        return orig_costs != new_costs