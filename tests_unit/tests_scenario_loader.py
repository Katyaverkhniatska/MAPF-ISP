import unittest
import tempfile
from pathlib import Path
from scenario_management.scenario_loader import ScenarioLoader, ScenarioValidationError

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

    def test_load_from_real_json_file(self):
        """Tests reading a valid scenario from an actual JSON file on disk."""
        json_content = """{
            "width": 4, "height": 4,
            "obstacles": [[2, 2]],
            "targets": [[3, 3]],
            "defenders": [{"x": 0, "y": 0}],
            "attackers": [{"x": 1, "y": 0, "target": [3, 3]}]
        }"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            tmp.write(json_content)
            tmp_path = Path(tmp.name)

        try:
            scenario = ScenarioLoader.from_json(tmp_path)
            self.assertEqual(scenario.grid.get_dimensions(), (4, 4))
            self.assertTrue(scenario.grid.is_obstacle((2, 2)))
            self.assertEqual(len(scenario.defenders), 1)
            self.assertEqual(len(scenario.attackers), 1)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

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

    def test_load_from_real_csv_file(self):
        """Tests reading a valid scenario from an actual CSV file on disk."""
        csv_content = """
        # Test CSV File
        GRID, 6, 6
        OBSTACLE, 1, 1
        DEFENDER, 0, 0
        TARGET, 5, 5
        ATTACKER, 0, 1, 5, 5
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
            tmp.write(csv_content)
            tmp_path = Path(tmp.name)

        try:
            scenario = ScenarioLoader.from_csv(tmp_path)
            self.assertEqual(scenario.grid.get_dimensions(), (6, 6))
            self.assertTrue(scenario.grid.is_obstacle((1, 1)))
            self.assertEqual(len(scenario.targets), 1)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

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

    def test_invalid_json_syntax_raises_error(self):
        """Tests that malformed JSON syntax throws a ScenarioValidationError."""
        bad_json = '{"width": 5, "height": 5, '  # Unclosed JSON
        with self.assertRaises(ScenarioValidationError) as ctx:
            ScenarioLoader.from_json(bad_json)
        self.assertIn("Failed to parse JSON string", str(ctx.exception))

    def test_missing_grid_in_csv_raises_error(self):
        """Tests that a CSV missing the GRID tag raises an error."""
        bad_csv = """
        OBSTACLE, 1, 1
        DEFENDER, 0, 0
        """
        with self.assertRaises(ScenarioValidationError) as ctx:
            ScenarioLoader.from_csv(bad_csv)
        self.assertIn("Missing GRID specification", str(ctx.exception))

    def test_unknown_csv_tag_raises_error(self):
        """Tests that unrecognized row tags in CSV raise an error."""
        bad_csv = """
        GRID, 5, 5
        UNKNOWN_TAG, 1, 2
        """
        with self.assertRaises(ScenarioValidationError) as ctx:
            ScenarioLoader.from_csv(bad_csv)
        self.assertIn("Unknown entity type tag", str(ctx.exception))

    def test_malformed_csv_row_values_raise_error(self):
        """Tests that non-integer inputs or incomplete rows throw errors."""
        bad_csv = """
        GRID, 5, 5
        OBSTACLE, invalid_x, 2
        """
        with self.assertRaises(ScenarioValidationError) as ctx:
            ScenarioLoader.from_csv(bad_csv)
        self.assertIn("Malformed CSV entry", str(ctx.exception))