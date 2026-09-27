import unittest
from collections import Counter

from scenario_management.scenario_loader import ScenarioTemplate, SpawnArea, ScenarioValidationError
from core_components.grid import Grid
from scenario_management.scenario_generator import ScenarioGenerator, GeneratedLayout
from typing import Any, Dict

def make_template(**overrides):
    defaults: Dict[str, Any] = dict(
        grid=Grid(12, 10, obstacles=[(4, 2), (4, 3)]),
        obstacles=[(4, 2), (4, 3)],
        targets=[(11, 3), (11, 7)],
        attacker_area=SpawnArea(0, 9, 0, 2),
        defender_area=SpawnArea(0, 9, 4, 8),
        num_attackers=3,
        num_defenders=2,
        predefined_targets=False,
        max_steps=50,
    )
    defaults.update(overrides)
    return ScenarioTemplate(**defaults)


class TestScenarioGenerator(unittest.TestCase):

    def test_generate_returns_correct_counts(self):
        tpl = make_template()
        gen = ScenarioGenerator(seed=42)
        layout = gen.generate(tpl)
        self.assertIsInstance(layout, GeneratedLayout)
        self.assertEqual(len(layout.attacker_positions), 3)
        self.assertEqual(len(layout.defender_positions), 2)
        self.assertEqual(len(layout.attacker_targets), 3)

    def test_no_overlap_between_attacker_and_defender_positions(self):
        tpl = make_template(
            attacker_area=SpawnArea(0, 9, 0, 5),
            defender_area=SpawnArea(0, 9, 3, 8),
        )
        gen = ScenarioGenerator(seed=1)
        for _ in range(20):
            layout = gen.generate(tpl)
            self.assertTrue(
                set(layout.attacker_positions).isdisjoint(layout.defender_positions)
            )

    def test_positions_avoid_obstacles_and_targets(self):
        tpl = make_template()
        gen = ScenarioGenerator(seed=7)
        obstacle_set = set(tpl.obstacles)
        target_set = set(tpl.targets)
        for _ in range(20):
            layout = gen.generate(tpl)
            for pos in layout.attacker_positions + layout.defender_positions:
                self.assertNotIn(pos, obstacle_set)
                self.assertNotIn(pos, target_set)

    def test_positions_within_declared_areas(self):
        tpl = make_template()
        gen = ScenarioGenerator(seed=3)
        for _ in range(10):
            layout = gen.generate(tpl)
            for (x, y) in layout.attacker_positions:
                self.assertTrue(0 <= y <= 9 and 0 <= x <= 2)
            for (x, y) in layout.defender_positions:
                self.assertTrue(0 <= y <= 9 and 4 <= x <= 8)

    def test_predefined_targets_exact_match_required(self):
        tpl = make_template(predefined_targets=True, num_attackers=3)  # 2 targets, 3 attackers
        gen = ScenarioGenerator(seed=1)
        with self.assertRaises(ScenarioValidationError) as ctx:
            gen.generate(tpl)
        self.assertIn("must exactly match", str(ctx.exception))

    def test_predefined_targets_assigns_in_file_order(self):
        tpl = make_template(predefined_targets=True, num_attackers=2)
        gen = ScenarioGenerator(seed=1)
        layout = gen.generate(tpl)
        self.assertEqual(layout.attacker_targets, [(11, 3), (11, 7)])

    def test_random_targets_every_attacker_has_a_target_in_pool(self):
        tpl = make_template(predefined_targets=False, num_attackers=5)
        gen = ScenarioGenerator(seed=9)
        layout = gen.generate(tpl)
        for t in layout.attacker_targets:
            self.assertIn(t, tpl.targets)

    def test_random_targets_fair_distribution_shuffled_round_robin(self):
        # 4 attackers, 2 targets -> each target must get exactly 2 attackers
        # (shuffled round-robin guarantees this; independent random picks would not).
        tpl = make_template(predefined_targets=False, num_attackers=4)
        gen = ScenarioGenerator(seed=5)
        layout = gen.generate(tpl)
        counts = Counter(layout.attacker_targets)
        self.assertEqual(counts[(11, 3)], 2)
        self.assertEqual(counts[(11, 7)], 2)

    def test_same_seed_reproduces_identical_sequence(self):
        tpl = make_template()
        gen_a = ScenarioGenerator(seed=123)
        gen_b = ScenarioGenerator(seed=123)
        for _ in range(5):
            la = gen_a.generate(tpl)
            lb = gen_b.generate(tpl)
            self.assertEqual(la.attacker_positions, lb.attacker_positions)
            self.assertEqual(la.defender_positions, lb.defender_positions)
            self.assertEqual(la.attacker_targets, lb.attacker_targets)

    def test_consecutive_calls_on_same_generator_differ(self):
        # Same seeded stream, called repeatedly, should not just repeat
        # the same layout every time (that would defeat batch variety).
        tpl = make_template()
        gen = ScenarioGenerator(seed=55)
        layouts = [gen.generate(tpl) for _ in range(5)]
        attacker_sets = [tuple(sorted(l.attacker_positions)) for l in layouts]
        self.assertTrue(len(set(attacker_sets)) > 1, "all 5 layouts were identical")

    def test_overlap_cannibalization_can_raise_runtime_error(self):
        # Areas fully overlap on a tiny grid: 3 free cells total (row=0,
        # cols 0..2), need 2 attackers + 2 defenders = 4 agents. The
        # loader's own overlap check would already reject this at
        # template-parse time; here we bypass the loader and construct
        # the ScenarioTemplate directly to exercise the generator's own
        # runtime safety net in isolation.
        tpl = make_template(
            grid=Grid(3, 1, obstacles=[]),
            obstacles=[],
            targets=[(2, 0)],
            attacker_area=SpawnArea(0, 0, 0, 2),
            defender_area=SpawnArea(0, 0, 0, 2),
            num_attackers=1,
            num_defenders=2,
        )
        gen = ScenarioGenerator(seed=1)
        # Free cells excluding target (2,0): (0,0) and (1,0) -> only 2 free
        # cells, 1 attacker + 2 defenders = 3 agents needed -> must fail.
        with self.assertRaises(ScenarioValidationError):
            gen.generate(tpl)


if __name__ == "__main__":
    unittest.main()