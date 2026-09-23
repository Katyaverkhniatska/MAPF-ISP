import unittest
from scenarious.scenario_loader import ScenarioLoader, ScenarioValidationError

class TestScenarioLoader(unittest.TestCase):

    def test_load_valid_json(self):
        raw_json = """{
            "width": 5, "height": 5,
            "obstacles": [[1, 1]],
            "targets": [[4, 4]],
            "defenders": [{"x": 0, "y": 0}],
            "attackers": [{"x": 0, "y": 1, "target": [4, 4]}]
        }"""
        scenario = ScenarioLoader.from_json(raw_json)
        self.assertEqual(scenario.grid.get_dimensions(), (5, 5))
        self.assertTrue(scenario.grid.is_obstacle((1, 1)))
        self.assertEqual(len(scenario.defenders), 1)
        self.assertEqual(len(scenario.attackers), 1)
        self.assertEqual(scenario.attackers[0].get_target(), (4, 4))

    def test_out_of_bounds_raises_error(self):
        raw_json = """{
            "width": 5, "height": 5,
            "obstacles": [[10, 1]],
            "targets": [[4, 4]],
            "defenders": [],
            "attackers": []
        }"""
        with self.assertRaises(ScenarioValidationError) as ctx:
            ScenarioLoader.from_json(raw_json)
        self.assertIn("out of bounds", str(ctx.exception))

    def test_invalid_grid_dimension_raises_error(self):
        raw_json = '{"width": -5, "height": 5}'
        with self.assertRaises(ScenarioValidationError):
            ScenarioLoader.from_json(raw_json)

    def test_load_valid_csv(self):
        raw_csv = """
        GRID, 10, 10
        OBSTACLE, 2, 2
        DEFENDER, 0, 0
        ATTACKER, 1, 1, 9, 9
        TARGET, 9, 9
        """
        scenario = ScenarioLoader.from_csv(raw_csv)
        self.assertEqual(scenario.grid.get_dimensions(), (10, 10))
        self.assertTrue(scenario.grid.is_obstacle((2, 2)))
        self.assertEqual(scenario.attackers[0].get_target(), (9, 9))