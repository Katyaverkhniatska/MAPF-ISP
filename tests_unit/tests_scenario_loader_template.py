import unittest
import tempfile
from pathlib import Path
from scenario_management.scenario_loader import (
    ScenarioLoader, ScenarioValidationError, ScenarioTemplate, SpawnArea,
)


class TestScenarioTemplateJson(unittest.TestCase):

    def _valid_template_dict(self):
        return {
            "width": 12, "height": 10,
            "obstacles": [[4, 2], [4, 3]],
            "targets": [[11, 3], [11, 7]],
            "attacker_area": {"row_min": 0, "row_max": 9, "col_min": 0, "col_max": 2},
            "defender_area": {"row_min": 0, "row_max": 9, "col_min": 4, "col_max": 8},
            "num_attackers": 3,
            "num_defenders": 2,
            "predefined_targets": False,
        }

    def test_load_valid_template(self):
        import json
        tpl = ScenarioLoader.template_from_json(json.dumps(self._valid_template_dict()))
        self.assertIsInstance(tpl, ScenarioTemplate)
        self.assertEqual(tpl.grid.get_dimensions(), (12, 10))
        self.assertTrue(tpl.grid.is_obstacle((4, 2)))
        self.assertEqual(tpl.targets, [(11, 3), (11, 7)])
        self.assertEqual(tpl.attacker_area, SpawnArea(0, 9, 0, 2))
        self.assertEqual(tpl.defender_area, SpawnArea(0, 9, 4, 8))
        self.assertEqual(tpl.num_attackers, 3)
        self.assertEqual(tpl.num_defenders, 2)
        self.assertFalse(tpl.predefined_targets)
        self.assertEqual(tpl.max_steps, 50)  # default

    def test_load_from_real_template_json_file(self):
        import json
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(self._valid_template_dict(), tmp)
            tmp_path = Path(tmp.name)
        try:
            tpl = ScenarioLoader.template_from_json(tmp_path)
            self.assertEqual(tpl.num_attackers, 3)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_predefined_targets_flag_and_custom_max_steps(self):
        import json
        data = self._valid_template_dict()
        data["predefined_targets"] = True
        data["max_steps"] = 75
        tpl = ScenarioLoader.template_from_json(json.dumps(data))
        self.assertTrue(tpl.predefined_targets)
        self.assertEqual(tpl.max_steps, 75)

    def test_missing_attacker_area_raises_error(self):
        import json
        data = self._valid_template_dict()
        del data["attacker_area"]
        with self.assertRaises(ScenarioValidationError) as ctx:
            ScenarioLoader.template_from_json(json.dumps(data))
        self.assertIn("attacker_area", str(ctx.exception))

    def test_missing_defender_area_raises_error(self):
        import json
        data = self._valid_template_dict()
        del data["defender_area"]
        with self.assertRaises(ScenarioValidationError) as ctx:
            ScenarioLoader.template_from_json(json.dumps(data))
        self.assertIn("defender_area", str(ctx.exception))

    def test_area_missing_bound_field_raises_error(self):
        import json
        data = self._valid_template_dict()
        del data["attacker_area"]["col_max"]
        with self.assertRaises(ScenarioValidationError) as ctx:
            ScenarioLoader.template_from_json(json.dumps(data))
        self.assertIn("col_max", str(ctx.exception))

    def test_area_min_greater_than_max_raises_error(self):
        import json
        data = self._valid_template_dict()
        data["attacker_area"]["row_min"] = 8
        data["attacker_area"]["row_max"] = 2
        with self.assertRaises(ScenarioValidationError) as ctx:
            ScenarioLoader.template_from_json(json.dumps(data))
        self.assertIn("row_min", str(ctx.exception))

    def test_area_out_of_grid_bounds_raises_error(self):
        import json
        data = self._valid_template_dict()
        data["attacker_area"]["col_max"] = 999
        with self.assertRaises(ScenarioValidationError) as ctx:
            ScenarioLoader.template_from_json(json.dumps(data))
        self.assertIn("out of grid width", str(ctx.exception))

    def test_no_targets_raises_error(self):
        import json
        data = self._valid_template_dict()
        data["targets"] = []
        with self.assertRaises(ScenarioValidationError) as ctx:
            ScenarioLoader.template_from_json(json.dumps(data))
        self.assertIn("at least one target", str(ctx.exception))

    def test_non_positive_counts_raise_error(self):
        import json
        data = self._valid_template_dict()
        data["num_attackers"] = 0
        with self.assertRaises(ScenarioValidationError):
            ScenarioLoader.template_from_json(json.dumps(data))

        data2 = self._valid_template_dict()
        data2["num_defenders"] = -1
        with self.assertRaises(ScenarioValidationError):
            ScenarioLoader.template_from_json(json.dumps(data2))

    def test_not_enough_free_cells_for_attackers_raises_error(self):
        import json
        data = self._valid_template_dict()
        # Shrink the attacker area to a single free cell, but ask for 3 attackers.
        data["attacker_area"] = {"row_min": 0, "row_max": 0, "col_min": 0, "col_max": 0}
        with self.assertRaises(ScenarioValidationError) as ctx:
            ScenarioLoader.template_from_json(json.dumps(data))
        self.assertIn("attacker_area only has", str(ctx.exception))

    def test_not_enough_free_cells_for_defenders_raises_error(self):
        import json
        data = self._valid_template_dict()
        data["defender_area"] = {"row_min": 0, "row_max": 0, "col_min": 4, "col_max": 4}
        data["num_defenders"] = 5
        with self.assertRaises(ScenarioValidationError) as ctx:
            ScenarioLoader.template_from_json(json.dumps(data))
        self.assertIn("defender_area only has", str(ctx.exception))

    def test_obstacles_and_targets_excluded_from_free_cell_count(self):
        import json
        # A 1x3 attacker area where the only 3 cells are obstacle, target, free.
        data = self._valid_template_dict()
        data["width"], data["height"] = 3, 1
        data["obstacles"] = [[0, 0]]
        data["targets"] = [[1, 0]]
        data["attacker_area"] = {"row_min": 0, "row_max": 0, "col_min": 0, "col_max": 2}
        data["defender_area"] = {"row_min": 0, "row_max": 0, "col_min": 0, "col_max": 2}
        data["num_attackers"] = 1
        data["num_defenders"] = 1
        # Only cell (2,0) is free; areas overlap fully, so union has 1 free
        # cell but 2 agents are required -> must fail.
        with self.assertRaises(ScenarioValidationError) as ctx:
            ScenarioLoader.template_from_json(json.dumps(data))
        self.assertIn("overlap", str(ctx.exception))

    def test_overlapping_areas_with_enough_room_succeeds(self):
        import json
        data = self._valid_template_dict()
        # Make the areas overlap but keep plenty of free cells.
        data["attacker_area"] = {"row_min": 0, "row_max": 9, "col_min": 0, "col_max": 5}
        data["defender_area"] = {"row_min": 0, "row_max": 9, "col_min": 3, "col_max": 8}
        tpl = ScenarioLoader.template_from_json(json.dumps(data))
        self.assertEqual(tpl.num_attackers, 3)
        self.assertEqual(tpl.num_defenders, 2)

    def test_invalid_max_steps_raises_error(self):
        import json
        data = self._valid_template_dict()
        data["max_steps"] = 0
        with self.assertRaises(ScenarioValidationError):
            ScenarioLoader.template_from_json(json.dumps(data))


class TestScenarioTemplateCsv(unittest.TestCase):

    VALID_CSV = """
    GRID, 12, 10
    OBSTACLE, 4, 2
    OBSTACLE, 4, 3
    TARGET, 11, 3
    TARGET, 11, 7
    ATTACKER_AREA, 0, 9, 0, 2
    DEFENDER_AREA, 0, 9, 4, 8
    COUNTS, 3, 2
    FLAG, predefined_targets, false
    """

    def test_load_valid_template_csv(self):
        tpl = ScenarioLoader.template_from_csv(self.VALID_CSV)
        self.assertEqual(tpl.grid.get_dimensions(), (12, 10))
        self.assertEqual(tpl.num_attackers, 3)
        self.assertEqual(tpl.num_defenders, 2)
        self.assertFalse(tpl.predefined_targets)
        self.assertEqual(tpl.max_steps, 50)

    def test_load_from_real_template_csv_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
            tmp.write(self.VALID_CSV)
            tmp_path = Path(tmp.name)
        try:
            tpl = ScenarioLoader.template_from_csv(tmp_path)
            self.assertEqual(tpl.num_defenders, 2)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_predefined_targets_true_and_max_steps(self):
        csv_text = self.VALID_CSV.replace(
            "FLAG, predefined_targets, false", "FLAG, predefined_targets, true"
        ) + "\nMAX_STEPS, 30"
        tpl = ScenarioLoader.template_from_csv(csv_text)
        self.assertTrue(tpl.predefined_targets)
        self.assertEqual(tpl.max_steps, 30)

    def test_missing_area_raises_error(self):
        csv_text = """
        GRID, 12, 10
        TARGET, 11, 3
        DEFENDER_AREA, 0, 9, 4, 8
        COUNTS, 3, 2
        """
        with self.assertRaises(ScenarioValidationError) as ctx:
            ScenarioLoader.template_from_csv(csv_text)
        self.assertIn("attacker_area", str(ctx.exception))

    def test_unknown_flag_name_raises_error(self):
        csv_text = self.VALID_CSV + "\nFLAG, made_up_flag, true"
        with self.assertRaises(ScenarioValidationError) as ctx:
            ScenarioLoader.template_from_csv(csv_text)
        self.assertIn("Unknown FLAG", str(ctx.exception))

    def test_malformed_area_row_raises_error(self):
        csv_text = """
        GRID, 12, 10
        TARGET, 11, 3
        ATTACKER_AREA, 0, 9, 0
        DEFENDER_AREA, 0, 9, 4, 8
        COUNTS, 3, 2
        """
        with self.assertRaises(ScenarioValidationError) as ctx:
            ScenarioLoader.template_from_csv(csv_text)
        self.assertIn("ATTACKER_AREA row requires", str(ctx.exception))

    def test_malformed_counts_row_raises_error(self):
        csv_text = """
        GRID, 12, 10
        TARGET, 11, 3
        ATTACKER_AREA, 0, 9, 0, 2
        DEFENDER_AREA, 0, 9, 4, 8
        COUNTS, 3
        """
        with self.assertRaises(ScenarioValidationError) as ctx:
            ScenarioLoader.template_from_csv(csv_text)
        self.assertIn("COUNTS row requires", str(ctx.exception))

    def test_unknown_tag_still_rejected_in_template_csv(self):
        csv_text = self.VALID_CSV + "\nBOGUS_TAG, 1, 2"
        with self.assertRaises(ScenarioValidationError) as ctx:
            ScenarioLoader.template_from_csv(csv_text)
        self.assertIn("Unknown entity type tag", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()