import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Dict, Any, Union, Optional

from core_components.agent_type import AgentType
from core_components.grid import Grid, Vertex
from core_components.agent import Agent


class ScenarioValidationError(Exception):
    """Raised when scenario data fails validation rules."""
    pass


@dataclass
class Scenario:
    """A fully concrete scenario: exact agent positions, ready to run as-is."""
    grid: Grid
    defenders: List[Agent]
    attackers: List[Agent]
    targets: List[Vertex]


@dataclass
class SpawnArea:
    """Rectangular region (inclusive bounds) that agents may spawn within."""
    row_min: int
    row_max: int
    col_min: int
    col_max: int

    def cells(self):
        for x in range(self.col_min, self.col_max + 1):
            for y in range(self.row_min, self.row_max + 1):
                yield (x, y)


@dataclass
class ScenarioTemplate:
    """
    A scenario "blueprint" for batch/comparison mode: obstacles and targets
    are fixed, but agent positions (and possibly attacker targets) are
    regenerated fresh every iteration by a generator, not by this loader.
    """
    grid: Grid
    obstacles: List[Vertex]
    targets: List[Vertex]
    attacker_area: SpawnArea
    defender_area: SpawnArea
    num_attackers: int
    num_defenders: int
    predefined_targets: bool
    max_steps: int = 50


class ScenarioLoader:
    """
    Parses and validates Scenario / ScenarioTemplate specifications from
    JSON and CSV formats.
    """

    # ------------------------------------------------------------------
    # Concrete scenarios (exact agent positions)
    # ------------------------------------------------------------------
    @classmethod
    def from_json(cls, source: Union[str, Path]) -> Scenario:
        """Loads and validates a scenario from a JSON file or JSON string.

        Expected JSON Row Formats:
        "width": _,
        "height": _,
        "obstacles": [[_, _], ...],
        "targets": [[_, _], ...],
        "defenders": [
            {"x": _, "y": _},
            {"x": _, "y": _}
        ],
        "attackers": [
            {"x": _, "y": _, "target": [_, _]}
        ]
        """
        data = cls._load_json_data(source)
        return cls._parse_dict(data)

    @classmethod
    def from_csv(cls, source: Union[str, Path]) -> Scenario:
        """
        Loads and validates a scenario from a CSV file or CSV string.

        Expected CSV Row Formats:
          GRID,width,height
          OBSTACLE,x,y
          ATTACKER,x,y,target_x,target_y (target_x/y optional)
          DEFENDER,x,y
          TARGET,x,y
        """
        data = cls._load_csv_data(source)
        return cls._parse_dict(data)

    # ------------------------------------------------------------------
    # Templates (areas + counts, for batch/comparison mode)
    # ------------------------------------------------------------------
    @classmethod
    def template_from_json(cls, source: Union[str, Path]) -> ScenarioTemplate:
        """Loads and validates a ScenarioTemplate from a JSON file or JSON string.

        Expected JSON Row Formats:
        "width": _,
        "height": _,
        "obstacles": [[_, _], ...],
        "targets": [[_, _], ...],
        "attacker_area": {"row_min": _, "row_max": _, "col_min": _, "col_max": _},
        "defender_area": {"row_min": _, "row_max": _, "col_min": _, "col_max": _},
        "num_attackers": _,
        "num_defenders": _,
        "predefined_targets": true|false,
        "max_steps": _   (optional, defaults to 50)
        """
        data = cls._load_json_data(source)
        return cls._parse_template_dict(data)

    @classmethod
    def template_from_csv(cls, source: Union[str, Path]) -> ScenarioTemplate:
        """
        Loads and validates a ScenarioTemplate from a CSV file or CSV string.

        Expected CSV Row Formats:
          GRID,width,height
          OBSTACLE,x,y
          TARGET,x,y
          ATTACKER_AREA,row_min,row_max,col_min,col_max
          DEFENDER_AREA,row_min,row_max,col_min,col_max
          COUNTS,num_attackers,num_defenders
          FLAG,predefined_targets,true|false
          MAX_STEPS,n   (optional)
        """
        data = cls._load_csv_template_data(source)
        return cls._parse_template_dict(data)

    # ------------------------------------------------------------------
    # Shared raw loading (text -> dict), format-agnostic
    # ------------------------------------------------------------------
    @staticmethod
    def _looks_like_path(source: Union[str, Path]) -> bool:
        """
        Safely checks whether `source` refers to an existing file. A raw
        JSON/CSV string can exceed the OS's max filename length, which
        makes Path.exists() raise OSError instead of returning False --
        so that's treated the same as "not a path".
        """
        try:
            path = Path(source)
            return path.exists() and path.is_file()
        except OSError:
            return False

    @classmethod
    def _load_json_data(cls, source: Union[str, Path]) -> Dict[str, Any]:
        if cls._looks_like_path(source):
            path = Path(source)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                raise ScenarioValidationError(f"Invalid JSON format in file {path}: {e}")
        else:
            try:
                return json.loads(str(source))
            except json.JSONDecodeError as e:
                raise ScenarioValidationError(f"Failed to parse JSON string: {e}")

    @classmethod
    def _read_lines(cls, source: Union[str, Path]) -> List[str]:
        if cls._looks_like_path(source):
            with open(Path(source), "r", encoding="utf-8") as f:
                return f.readlines()
        return str(source).strip().splitlines()

    @classmethod
    def _load_csv_data(cls, source: Union[str, Path]) -> Dict[str, Any]:
        """Parses the concrete-scenario CSV tags (GRID/OBSTACLE/ATTACKER/DEFENDER/TARGET)."""
        lines = cls._read_lines(source)

        data: Dict[str, Any] = {
            "width": None,
            "height": None,
            "obstacles": [],
            "attackers": [],
            "defenders": [],
            "targets": []
        }

        reader = csv.reader(lines)
        for line_num, row in enumerate(reader, 1):
            row = [item.strip() for item in row if item.strip()]
            if not row or row[0].startswith("#"):
                continue  # Skip empty lines and comments

            tag = row[0].upper()
            try:
                if tag == "GRID":
                    if len(row) < 3:
                        raise ScenarioValidationError("GRID row requires width and height.")
                    data["width"] = int(row[1])
                    data["height"] = int(row[2])

                elif tag == "OBSTACLE":
                    data["obstacles"].append([int(row[1]), int(row[2])])

                elif tag == "DEFENDER":
                    data["defenders"].append({"x": int(row[1]), "y": int(row[2])})

                elif tag == "TARGET":
                    data["targets"].append([int(row[1]), int(row[2])])

                elif tag == "ATTACKER":
                    attacker_dict: Dict[str, Any]
                    attacker_dict = {"x": int(row[1]), "y": int(row[2])}
                    if len(row) >= 5:
                        attacker_dict["target"] = [int(row[3]), int(row[4])]
                    data["attackers"].append(attacker_dict)

                else:
                    raise ScenarioValidationError(f"Unknown entity type tag '{tag}' on line {line_num}.")

            except (ValueError, IndexError) as e:
                raise ScenarioValidationError(f"Malformed CSV entry on line {line_num} ({row}): {e}")

        if data["width"] is None or data["height"] is None:
            raise ScenarioValidationError("Missing GRID specification in CSV input.")

        return data

    @classmethod
    def _load_csv_template_data(cls, source: Union[str, Path]) -> Dict[str, Any]:
        """Parses the template CSV tags (GRID/OBSTACLE/TARGET/*_AREA/COUNTS/FLAG/MAX_STEPS)."""
        lines = cls._read_lines(source)

        data: Dict[str, Any] = {
            "width": None,
            "height": None,
            "obstacles": [],
            "targets": [],
            "attacker_area": None,
            "defender_area": None,
            "num_attackers": None,
            "num_defenders": None,
            "predefined_targets": False,
            "max_steps": 50,
        }

        def parse_area(row: List[str], label: str) -> Dict[str, int]:
            if len(row) < 5:
                raise ScenarioValidationError(
                    f"{label} row requires row_min,row_max,col_min,col_max.")
            return {
                "row_min": int(row[1]), "row_max": int(row[2]),
                "col_min": int(row[3]), "col_max": int(row[4]),
            }

        reader = csv.reader(lines)
        for line_num, row in enumerate(reader, 1):
            row = [item.strip() for item in row if item.strip()]
            if not row or row[0].startswith("#"):
                continue

            tag = row[0].upper()
            try:
                if tag == "GRID":
                    if len(row) < 3:
                        raise ScenarioValidationError("GRID row requires width and height.")
                    data["width"] = int(row[1])
                    data["height"] = int(row[2])

                elif tag == "OBSTACLE":
                    data["obstacles"].append([int(row[1]), int(row[2])])

                elif tag == "TARGET":
                    data["targets"].append([int(row[1]), int(row[2])])

                elif tag == "ATTACKER_AREA":
                    data["attacker_area"] = parse_area(row, "ATTACKER_AREA")

                elif tag == "DEFENDER_AREA":
                    data["defender_area"] = parse_area(row, "DEFENDER_AREA")

                elif tag == "COUNTS":
                    if len(row) < 3:
                        raise ScenarioValidationError("COUNTS row requires num_attackers,num_defenders.")
                    data["num_attackers"] = int(row[1])
                    data["num_defenders"] = int(row[2])

                elif tag == "FLAG":
                    if len(row) < 3:
                        raise ScenarioValidationError("FLAG row requires a name and a value.")
                    if row[1].lower() == "predefined_targets":
                        data["predefined_targets"] = row[2].strip().lower() in ("true", "1", "yes")
                    else:
                        raise ScenarioValidationError(f"Unknown FLAG '{row[1]}' on line {line_num}.")

                elif tag == "MAX_STEPS":
                    if len(row) < 2:
                        raise ScenarioValidationError("MAX_STEPS row requires a value.")
                    data["max_steps"] = int(row[1])

                else:
                    raise ScenarioValidationError(f"Unknown entity type tag '{tag}' on line {line_num}.")

            except (ValueError, IndexError) as e:
                raise ScenarioValidationError(f"Malformed CSV entry on line {line_num} ({row}): {e}")

        if data["width"] is None or data["height"] is None:
            raise ScenarioValidationError("Missing GRID specification in CSV input.")

        return data

    # ------------------------------------------------------------------
    # Small shared helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_point(pt: Any, name: str) -> Tuple[int, int]:
        if isinstance(pt, dict):
            if "x" in pt and "y" in pt:
                return int(pt["x"]), int(pt["y"])
            if "pos" in pt and isinstance(pt["pos"], (list, tuple)) and len(pt["pos"]) == 2:
                return int(pt["pos"][0]), int(pt["pos"][1])
        elif isinstance(pt, (list, tuple)) and len(pt) >= 2:
            return int(pt[0]), int(pt[1])
        raise ScenarioValidationError(f"Invalid coordinate format for {name}: {pt}")

    @staticmethod
    def _extract_boundaries(area_name: str, area_data: Any) -> SpawnArea:
        if not isinstance(area_data, dict):
            raise ScenarioValidationError(f"'{area_name}' must be an object with row/col bounds.")
        required = ("row_min", "row_max", "col_min", "col_max")
        missing = [k for k in required if k not in area_data]
        if missing:
            raise ScenarioValidationError(
                f"'{area_name}' is missing required field(s): {', '.join(missing)}.")
        try:
            values = {k: int(area_data[k]) for k in required}
        except (ValueError, TypeError):
            raise ScenarioValidationError(f"'{area_name}' bounds must be integers.")
        return SpawnArea(**values)

    # ------------------------------------------------------------------
    # Concrete scenario parsing (exact agents)
    # ------------------------------------------------------------------
    @classmethod
    def _parse_dict(cls, data: Dict[str, Any]) -> Scenario:
        """Internal driver to validate schema constraints and construct a concrete Scenario."""
        width, height, is_in_bounds = cls._parse_grid_dims(data)
        parse_point = cls._parse_point

        # Obstacles
        obstacles = cls._parse_points_list(
            data.get("obstacles", []), "Obstacle", is_in_bounds, width, height)
        grid = Grid(width, height, obstacles=obstacles)

        # Targets
        targets = cls._parse_points_list(
            data.get("targets", []), "Target", is_in_bounds, width, height)

        # Defenders
        raw_defenders = data.get("defenders", [])
        defenders: List[Agent] = []
        for idx, d_data in enumerate(raw_defenders):
            try:
                dx, dy = parse_point(d_data, f"Defender #{idx}")
            except (ValueError, TypeError):
                raise ScenarioValidationError(f"Defender #{idx} coordinate values must be integers.")
            if not is_in_bounds(dx, dy):
                raise ScenarioValidationError(f"Defender #{idx} position ({dx}, {dy}) is out of bounds.")
            defenders.append(Agent(dx, dy, AgentType.DEFENDER))

        # Attackers (+ round-robin fill-in for any without an explicit target)
        raw_attackers = data.get("attackers", [])
        attackers: List[Agent] = []
        untargeted: List[Agent] = []
        for idx, a_data in enumerate(raw_attackers):
            try:
                ax, ay = parse_point(a_data, f"Attacker #{idx}")
            except (ValueError, TypeError):
                raise ScenarioValidationError(f"Attacker #{idx} position values must be integers.")
            if not is_in_bounds(ax, ay):
                raise ScenarioValidationError(f"Attacker #{idx} position ({ax}, {ay}) is out of bounds.")

            agent = Agent(ax, ay, AgentType.ATTACKER)

            raw_target = None
            if isinstance(a_data, dict):
                raw_target = a_data.get("target")
            elif isinstance(a_data, (list, tuple)) and len(a_data) > 2:
                raw_target = a_data[2]

            if raw_target is not None:
                try:
                    tx, ty = parse_point(raw_target, f"Attacker #{idx} target")
                except (ValueError, TypeError):
                    raise ScenarioValidationError(f"Attacker #{idx} target coordinate values must be integers.")
                if not is_in_bounds(tx, ty):
                    raise ScenarioValidationError(f"Attacker #{idx} target ({tx}, {ty}) is out of bounds.")
                agent.set_target((tx, ty))
            else:
                untargeted.append(agent)

            grid.mark_taken(agent.get_position())
            attackers.append(agent)

        if untargeted and not targets:
            raise ScenarioValidationError(
                "Attackers without a target were given, but no targets are defined.")
        for i, agent in enumerate(untargeted):
            agent.set_target(targets[i % len(targets)])

        return Scenario(grid=grid, defenders=defenders, attackers=attackers, targets=targets)

    @classmethod
    def _parse_points_list(cls, raw_points, label: str, is_in_bounds, width: int, height: int) -> List[Vertex]:
        points: List[Vertex] = []
        for idx, pt in enumerate(raw_points):
            try:
                x, y = cls._parse_point(pt, f"{label} #{idx}")
            except (ValueError, TypeError):
                raise ScenarioValidationError(f"{label} #{idx} coordinate values must be integers.")
            if not is_in_bounds(x, y):
                raise ScenarioValidationError(
                    f"{label} #{idx} at ({x}, {y}) is out of bounds for grid {width}x{height}.")
            points.append((x, y))
        return points

    @classmethod
    def _parse_grid_dims(cls, data: Dict[str, Any]):
        width = data.get("width")
        height = data.get("height")
        if not isinstance(width, int) or not isinstance(height, int):
            raise ScenarioValidationError("Grid 'width' and 'height' must be integers.")
        if width <= 0 or height <= 0:
            raise ScenarioValidationError(
                f"Grid dimensions must be positive integers. Got width={width}, height={height}.")

        def is_in_bounds(x: int, y: int) -> bool:
            return 0 <= x < width and 0 <= y < height

        return width, height, is_in_bounds

    # ------------------------------------------------------------------
    # Template parsing (areas + counts, no concrete agents yet)
    # ------------------------------------------------------------------
    @classmethod
    def _parse_template_dict(cls, data: Dict[str, Any]) -> ScenarioTemplate:
        width, height, is_in_bounds = cls._parse_grid_dims(data)

        obstacles = cls._parse_points_list(
            data.get("obstacles", []), "Obstacle", is_in_bounds, width, height)
        grid = Grid(width, height, obstacles=obstacles)

        targets = cls._parse_points_list(
            data.get("targets", []), "Target", is_in_bounds, width, height)
        if not targets:
            raise ScenarioValidationError("A template must define at least one target.")

        if "attacker_area" not in data or data.get("attacker_area") is None:
            raise ScenarioValidationError("Template is missing 'attacker_area'.")
        if "defender_area" not in data or data.get("defender_area") is None:
            raise ScenarioValidationError("Template is missing 'defender_area'.")

        attacker_area = cls._extract_boundaries("attacker_area", data["attacker_area"])
        defender_area = cls._extract_boundaries("defender_area", data["defender_area"])

        cls._validate_area_bounds(attacker_area, "attacker_area", width, height)
        cls._validate_area_bounds(defender_area, "defender_area", width, height)

        num_attackers = data.get("num_attackers")
        num_defenders = data.get("num_defenders")
        if not isinstance(num_attackers, int) or num_attackers <= 0:
            raise ScenarioValidationError("'num_attackers' must be a positive integer.")
        if not isinstance(num_defenders, int) or num_defenders <= 0:
            raise ScenarioValidationError("'num_defenders' must be a positive integer.")

        predefined_targets = bool(data.get("predefined_targets", False))

        max_steps = data.get("max_steps", 50)
        if not isinstance(max_steps, int) or max_steps <= 0:
            raise ScenarioValidationError("'max_steps' must be a positive integer.")

        obstacle_set = set(obstacles)
        target_set = set(targets)

        # A cell must be free of obstacles AND targets to be spawnable (an
        # agent starting on a target would resolve it before step 1, which
        # would distort batch statistics).
        def free_cells(area: SpawnArea) -> List[Vertex]:
            return [c for c in area.cells() if c not in obstacle_set and c not in target_set]

        attacker_free = free_cells(attacker_area)
        if len(attacker_free) < num_attackers:
            raise ScenarioValidationError(
                f"attacker_area only has {len(attacker_free)} free cell(s), "
                f"but num_attackers={num_attackers}.")

        # Conservative check for the defender area: if it overlaps the
        # attacker area, assume attackers might occupy shared free cells
        # first, and require enough room in the union for everyone.
        defender_free = free_cells(defender_area)
        overlap = set(attacker_area.cells()) & set(defender_area.cells())
        if overlap:
            union_free = set(attacker_free) | set(defender_free)
            if len(union_free) < num_attackers + num_defenders:
                raise ScenarioValidationError(
                    f"attacker_area and defender_area overlap and together only have "
                    f"{len(union_free)} free cell(s), but {num_attackers + num_defenders} "
                    f"agents are required."
                )
        elif len(defender_free) < num_defenders:
            raise ScenarioValidationError(
                f"defender_area only has {len(defender_free)} free cell(s), "
                f"but num_defenders={num_defenders}.")

        return ScenarioTemplate(
            grid=grid,
            obstacles=obstacles,
            targets=targets,
            attacker_area=attacker_area,
            defender_area=defender_area,
            num_attackers=num_attackers,
            num_defenders=num_defenders,
            predefined_targets=predefined_targets,
            max_steps=max_steps,
        )

    @staticmethod
    def _validate_area_bounds(area: SpawnArea, name: str, width: int, height: int):
        if area.row_min > area.row_max:
            raise ScenarioValidationError(f"'{name}': row_min must be <= row_max.")
        if area.col_min > area.col_max:
            raise ScenarioValidationError(f"'{name}': col_min must be <= col_max.")
        if area.row_min < 0 or area.row_max >= height:
            raise ScenarioValidationError(
                f"'{name}': row bounds [{area.row_min}, {area.row_max}] out of grid height {height}.")
        if area.col_min < 0 or area.col_max >= width:
            raise ScenarioValidationError(
                f"'{name}': col bounds [{area.col_min}, {area.col_max}] out of grid width {width}.")