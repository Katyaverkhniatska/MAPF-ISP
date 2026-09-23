import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Dict, Any, Union

from core_components.agent_type import AgentType
from core_components.grid import Grid, Vertex
from core_components.agent import Agent


class ScenarioValidationError(Exception):
    """Raised when scenario data fails validation rules."""
    pass


@dataclass
class Scenario:
    grid: Grid
    defenders: List[Agent]
    attackers: List[Agent]
    targets: List[Vertex]


class ScenarioLoader:
    """
    Parses and validates Scenario specifications from JSON and CSV formats.
    """

    @classmethod
    def from_json(cls, source: Union[str, Path]) -> Scenario:
        """Loads and validates a scenario from a JSON file or JSON string."""
        path = Path(source)
        if path.exists() and path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                raise ScenarioValidationError(f"Invalid JSON format in file {path}: {e}")
        else:
            try:
                data = json.loads(str(source))
            except json.JSONDecodeError as e:
                raise ScenarioValidationError(f"Failed to parse JSON string: {e}")

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
        path = Path(source)
        if path.exists() and path.is_file():
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        else:
            lines = str(source).strip().splitlines()

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
                    attacker_dict : Dict[str, Any]
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

        return cls._parse_dict(data)

    @classmethod
    def _parse_dict(cls, data: Dict[str, Any]) -> Scenario:
        """Internal driver to validate schema constraints and construct Scenario objects."""

        # 1. Validate Grid Dimensions
        width = data.get("width")
        height = data.get("height")
        if not isinstance(width, int) or not isinstance(height, int):
            raise ScenarioValidationError("Grid 'width' and 'height' must be integers.")
        if width <= 0 or height <= 0:
            raise ScenarioValidationError(f"Grid dimensions must be positive integers. Got width={width}, height={height}.")

        def is_in_bounds(x: int, y: int) -> bool:
            return 0 <= x < width and 0 <= y < height

        def parse_point(pt: Any, name: str) -> Tuple[int, int]:
            if isinstance(pt, dict):
                if "x" in pt and "y" in pt:
                    return int(pt["x"]), int(pt["y"])
                if "pos" in pt and isinstance(pt["pos"], (list, tuple)) and len(pt["pos"]) == 2:
                    return int(pt["pos"][0]), int(pt["pos"][1])
            elif isinstance(pt, (list, tuple)) and len(pt) >= 2:
                return int(pt[0]), int(pt[1])
            raise ScenarioValidationError(f"Invalid coordinate format for {name}: {pt}")

        # 2. Parse and Validate Obstacles
        raw_obstacles = data.get("obstacles", [])
        obstacles: List[Vertex] = []
        for idx, obs in enumerate(raw_obstacles):
            try:
                x, y = parse_point(obs, f"Obstacle #{idx}")
            except (ValueError, TypeError):
                raise ScenarioValidationError(f"Obstacle #{idx} coordinate values must be integers.")
            if not is_in_bounds(x, y):
                raise ScenarioValidationError(f"Obstacle #{idx} at ({x}, {y}) is out of bounds for grid {width}x{height}.")
            obstacles.append((x, y))

        grid = Grid(width, height, obstacles=obstacles)

        # 3. Parse and Validate Targets
        raw_targets = data.get("targets", [])
        targets: List[Vertex] = []
        for idx, tgt in enumerate(raw_targets):
            try:
                tx, ty = parse_point(tgt, f"Target #{idx}")
            except (ValueError, TypeError):
                raise ScenarioValidationError(f"Target #{idx} coordinate values must be integers.")
            if not is_in_bounds(tx, ty):
                raise ScenarioValidationError(f"Target #{idx} at ({tx}, {ty}) is out of bounds.")
            targets.append((tx, ty))

        # 4. Parse and Validate Defenders
        raw_defenders = data.get("defenders", [])
        defenders: List[Agent] = []
        for idx, d_data in enumerate(raw_defenders):
            try:
                dx, dy = parse_point(d_data, f"Defender #{idx}")
            except (ValueError, TypeError):
                raise ScenarioValidationError(f"Defender #{idx} coordinate values must be integers.")

            if not is_in_bounds(dx, dy):
                raise ScenarioValidationError(f"Defender #{idx} position ({dx}, {dy}) is out of bounds.")

            agent = Agent(dx, dy, AgentType.DEFENDER)
            defenders.append(agent)

        # 5. Parse and Validate Attackers
        raw_attackers = data.get("attackers", [])
        attackers: List[Agent] = []
        for idx, a_data in enumerate(raw_attackers):
            try:
                ax, ay = parse_point(a_data, f"Attacker #{idx}")
            except (ValueError, TypeError):
                raise ScenarioValidationError(f"Attacker #{idx} position values must be integers.")

            if not is_in_bounds(ax, ay):
                raise ScenarioValidationError(f"Attacker #{idx} position ({ax}, {ay}) is out of bounds.")

            agent = Agent(ax, ay, AgentType.ATTACKER)

            # Determine target if specified
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

            attackers.append(agent)

        return Scenario(grid=grid, defenders=defenders, attackers=attackers, targets=targets)