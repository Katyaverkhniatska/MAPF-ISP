import random
from dataclasses import dataclass
from typing import List, Optional

from core_components.grid import Vertex
from scenario_management.scenario_loader import ScenarioTemplate, ScenarioValidationError, SpawnArea


@dataclass
class GeneratedLayout:
    """
    One concrete, random arrangement produced from a ScenarioTemplate.
    Coordinates only -- no Grid/Agent objects -- so the same layout can be
    replayed identically against several strategies, each of which needs
    its own fresh Grid and Agent instances (Simulation mutates both).
    """
    attacker_positions: List[Vertex]
    defender_positions: List[Vertex]
    # attacker_targets[i] is the target for attacker_positions[i]
    attacker_targets: List[Vertex]


class ScenarioGenerator:
    """
    Produces a fresh random agent arrangement from a ScenarioTemplate.

    One instance wraps a single `random.Random` stream. Seed the instance
    once per batch run (or leave `seed=None` for OS entropy): every call
    to `generate()` then draws the *next* values from that stream, so
    each iteration gets a different layout, while the whole sequence of
    N layouts is reproducible if the same starting seed is reused later.
    Reseeding before every iteration would defeat the point -- it would
    either repeat the same layout (same seed every time) or gain nothing
    over just using one seed (different seed every time).
    """

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    def generate(self, template: ScenarioTemplate) -> GeneratedLayout:
        self.validate(template)

        obstacle_set = set(template.obstacles)
        target_set = set(template.targets)

        def free_cells(area: SpawnArea):
            return [c for c in area.cells() if c not in obstacle_set and c not in target_set]

        attacker_free = free_cells(template.attacker_area)
        defender_free_all = free_cells(template.defender_area)

        # The loader already checked that there's *enough total room* for
        # both areas combined (including the overlap case). But that's a
        # necessary, not sufficient, condition for any particular random
        # draw: if the areas overlap, an unlucky attacker sample could
        # still eat into cells defenders needed. So we place attackers
        # first, then re-check what's actually left for defenders.
        attacker_positions = self._rng.sample(attacker_free, template.num_attackers)
        taken = set(attacker_positions)

        defender_candidates = [c for c in defender_free_all if c not in taken]
        if len(defender_candidates) < template.num_defenders:
            raise ScenarioValidationError(
                f"Not enough free cells remain for defenders after placing attackers "
                f"({len(defender_candidates)} available, {template.num_defenders} required). "
                f"This can happen when attacker_area and defender_area overlap heavily; "
                f"try again, enlarge defender_area, or reduce agent counts."
            )
        defender_positions = self._rng.sample(defender_candidates, template.num_defenders)

        attacker_targets = self._assign_targets(template)

        return GeneratedLayout(
            attacker_positions=attacker_positions,
            defender_positions=defender_positions,
            attacker_targets=attacker_targets,
        )

    # ------------------------------------------------------------------
    def _assign_targets(self, template: ScenarioTemplate) -> List[Vertex]:
        if template.predefined_targets:
            # Exact-match already enforced by validate(); each attacker
            # gets the target at the same index, in file order.
            return list(template.targets)

        # Shuffled round-robin: repeatedly shuffle a full copy of the
        # target pool and append it, then trim to length. This spreads
        # attackers evenly across targets (unlike independent random
        # picks, which could leave a target with zero attackers aimed at
        # it) while still varying the assignment across iterations.
        assigned: List[Vertex] = []
        while len(assigned) < template.num_attackers:
            chunk = list(template.targets)
            self._rng.shuffle(chunk)
            assigned.extend(chunk)
        return assigned[:template.num_attackers]

    # ------------------------------------------------------------------
    @staticmethod
    def validate(template: ScenarioTemplate) -> None:
        """
        Checks that don't depend on any particular random draw, so they
        can (and should) be run once up front by a batch runner before
        spending time on iterations that would fail anyway.
        """
        if template.predefined_targets and len(template.targets) != template.num_attackers:
            raise ScenarioValidationError(
                f"predefined_targets is true, so num_attackers "
                f"({template.num_attackers}) must exactly match the number of "
                f"targets ({len(template.targets)})."
            )