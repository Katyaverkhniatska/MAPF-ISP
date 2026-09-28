# MAPF-ISP
Individual Software Project Charles University
Author: Verkhniatska Yekateryna

# Adversarial Area Protection Visualization Tool

A Python-based interactive visualization and comparison tool for exploring defender allocation strategies in the Adversarial Area Protection (AAP) problem.

---------------

## Project Structure
 
```
MAP-ISP/
├── core_components/
│   ├── agent.py                  # ✅ Agent class (position, type, movement, target assignment)
│   ├── agent_type.py             # ✅ AgentType enum (ATTACKER, DEFENDER)
│   ├── grid.py                   # ✅ Grid class (environment, obstacles)
│   └── grid_availability.py      # ✅ GridAvailability enum (PASSABLE, OBSTACLE, TAKEN)
│
├── allocation_strategies/
│   ├── allocation_strategy.py    # ✅ Base AllocationStrategy class
│   ├── random_strategy.py        # ✅ Random allocation
│   ├── greedy_strategy.py        # ✅ Greedy allocation
│   └── bottleneck_strategy.py    # ✅ Bottleneck simulation allocation
│
├── simulation_engine/           
│   ├── simulation.py             # ✅ Simulation orchestrator
│   ├── step_snapshot.py          # ✅ State snapshot data class
│   ├── statistics_calculator.py  # ✅ Metrics derivation
│   ├── batch_runner.py           # 📝 Runs every strategy against paired, generated layouts
│   └── batch_aggregator.py       # 📝 Aggregates a batch run into per-strategy summaries
│
├── pathfinding/
│   ├── a_star.py                 # ✅ A* algorithm implementation
│   └── path_finder.py            # ✅ PathFinder class wrapper
│
├── tests_deterministic/
|   ├── tests_bottleneck.py       # ✅ Deterministic map tests for BottleneckStrategy
|   └── tests_simulation.py       # ✅ Unit and deterministic tests for simulation components
│
├── tests_unit/
|   ├── util_tests.py                     # ✅ Util and helper methods for testing
|   ├── tests_general.py                  # ✅ Unit tests for core components
│   ├── tests_scenario_loader.py          # ✅ Unit tests for scenario loader
│   ├── tests_scenario_loader_template.py # 📝 Unit tests for scenario templates loader
│   ├── tests_scenario_generator.py       # 📝 Unit tests for random layout generation
│   ├── tests_batch_runner.py             # 📝 Unit tests for the batch runner
│   └── tests_batch_aggregator.py         # 📝 Unit tests for batch statistics aggregation
|
├── visualization/
│   ├── simulation_window.py      # ✅ Tkinter GUI main window
│   ├── control_panel.py          # ✅ GUI controls panel
│   ├── grid_canvas.py            # ✅ Main canvas that renders grid
│   ├── scenario_selector.py      # ✅ Panel for selecting maps and strategies
│   ├── statistics_panel.py       # ✅ Panel showing statistics values
│   └── batch_results_window.py   # 📝 Pop-up comparison table for batch mode
│
├── scenario_management/
│   ├── scenario_loader.py        # ✅ JSON/CSV scenario and templates parsing
│   └── scenario_generator.py     # ✅ Generates randomized agent layouts from a template
│
├── main.py                       # Application entry point
├── README.md                     # This file
├── Dockerfile                    # Docker configuration
├── compose.yaml                  # Docker comppose.yaml file
├── README.Docker.md              # Docker README.md file with usage instructions
└── .gitignore                    # Git ignore rules
```

**Legend:** ✅ = Implemented and tested |  ⏳ = Planned, not yet implemented | 📝 = New in this version

---

## Current Status

### ✅ Completed & Production-Ready (Backend)

#### Phase 1: Core Components
- **Grid System** — 2D grid with obstacle tracking, passability queries, and neighbor lookups
  - Bounds checking on all operations
  - `GridAvailability` enum for cell states (PASSABLE, OBSTACLE, TAKEN)
  - Methods: `is_passable()`, `get_neighbors()`, `mark_obstacles()`, `mark_taken()`, `get_grid_state()`
  - **Test Coverage:** 15+ unit tests, all passing

- **Agent System** — Foundation for attackers and defenders
  - `Agent` class with position tracking and movement methods
  - `AgentType` enum to distinguish ATTACKER from DEFENDER
  - **Test Coverage:** Movement and position queries tested

- **Pathfinding (A\* Algorithm)** — Collision-aware route planning
  - Complete A* implementation with Manhattan distance heuristic
  - Handles obstacles and grid boundaries
  - Error handling: raises `ValueError` for invalid/unreachable positions
  - **Test Coverage:** 10 test cases covering straight paths, obstacle avoidance, edge cases, unreachable goals (all passing)

#### Phase 2: Allocation Strategies
- `AllocationStrategy` — Abstract base class defining the interface all strategies implement
- `RandomStrategy` — Assigns each defender to a random attacker target
  - Deterministic when seeded
  - Handles more defenders than targets by cycling through targets
  - **Test Coverage:** Boundary cases tested

- `GreedyStrategy` — Assigns each defender to its closest available target using Euclidean distance
  - One-to-one matching up to the number of targets
  - Fallback to closest global target for excess defenders
  - **Test Coverage:** Distance computation and tie-breaking verified

- `BottleneckStrategy` — Sophisticated simulation-based allocation
  - Simulates attacker paths to identify high-traffic vertices
  - Detects gaps between obstacle groups using expanding-square vicinity search
  - 8-connectivity for obstacle grouping (per paper footnote)
  - 4-connectivity for agent movement (per paper's grid model)
  - Deterministic tie-breaking: when path frequencies tie, picks vertex closest to defender centroid
  - Fallback to random assignment for leftover defenders
  - **Test Coverage:** 10+ unit tests for internal methods; 3 deterministic end-to-end tests (new)

#### Phase 3: Simulation Engine- `Simulation` — Orchestrates step-by-step simulation
  - Single-stage defender allocation (strategy applied once)
  - LRA* agent movement: agents replan one step at a time against current grid occupancy
  - Defenders move before attackers each turn (per paper's turn-based framing)
  - Collision-free movement: agents avoid occupied cells and obstacles
  - **Target Resolution:** Supports both physical target occupation and implicit protection (detects when attackers are completely blocked from reaching targets)
  - Early termination when all targets are either captured or protected
  - Full history recording: snapshots captured at every step (including step 0)
  - **Methods:** `step()`, `run()`, `_check_finished()`, `_update_target_states()`
  - **Test Coverage:** Integration and deterministic tests with all three strategies (52+ total tests passing)

- `StepSnapshot` — Immutable capture of grid state at a single simulation step
  - Stores agent positions (not references), making snapshots stable across steps
  - Tracks captured/protected/empty targets
  - Includes assignment dictionary and bottleneck vertices
  - **Methods:** `empty_targets` property, clean `__repr__` for debugging
  - **Test Coverage:** Verified through simulation history

- `StatisticsCalculator` — Derives metrics from full simulation run
  - **Ratio metrics:** `success_rate()`, `average_attacker_time()`, `average_defender_time()`, `defender_efficiency()`
  - **Per-agent metrics:** Arrival times for each attacker/defender (step at which they reached their target)
  - **Per-defender metrics:** How many targets each defender personally blocked
  - **Path analysis:** How many times each attacker occupied a bottleneck vertex
  - **Test Coverage:** Statistics aggregation verified on mock snapshots
  - **Note:** All metrics are read-only accessors; no mutations

#### Phase 4: Tkinter GUI
- `SimulationWindow` — Main application window
  - File dialog for scenario selection (not yet implemented)
  - Strategy selection dropdown (Random, Greedy, Bottleneck)
  - Simulation execution trigger
  - Play/pause/step forward/step backward controls
  - Current step display

- `GridCanvas` — Custom canvas widget for visualization
  - Side-by-side grid rendering (two strategies simultaneously) (not yet implemented, available for a single one)
  - Color coding: obstacles (black), attackers (red), defenders (blue), empty targets (white), captured targets (dark red), protected targets (green)
  - Live rendering as user steps through history

- `ControlPanel` — Playback controls
  - Play/Pause button (toggles auto-stepping)
  - Step Forward button (next snapshot)
  - Step Backward button (previous snapshot)
  - Current step display and progress indicator

- `StatisticsPanel` — Real-time metrics display
  - Targets captured, protected, empty
  - Success rate (%)
  - Average time to capture/protection
  - Defender efficiency

#### Phase 5: Scenario Management
- `ScenarioLoader` — Parse and validate input for two distinct use cases:
  - **Concrete scenarios** (`from_json` / `from_csv`) — exact agent positions, run as-is
    - JSON format: `{ "width": int, "height": int, "obstacles": [[x, y], ...], "attackers": [{x, y, target}, ...], "defenders": [{x, y}, ...], "targets": [[x, y], ...] }`
    - CSV format: One row per entity type (`GRID`, `OBSTACLE`, `ATTACKER`, `DEFENDER`, `TARGET`)
    - Attackers with no explicit target are auto-assigned round-robin from the target list
    - Validation: grid dimensions positive, all positions within bounds, meaningful error messages for malformed input
  - **Scenario templates** (`template_from_json` / `template_from_csv`, new) — a blueprint for batch mode: fixed obstacles/targets, but a rectangular `attacker_area` / `defender_area` plus `num_attackers` / `num_defenders` instead of exact positions, so a fresh layout can be generated every iteration
    - `predefined_targets` flag: `true` requires an exact attacker/target count match; `false` assigns targets randomly each iteration
    - Validation includes free-cell checks against obstacles/targets/area overlap before any iteration runs
  - **Test Coverage:** 33 unit tests (10 for concrete scenarios, 23 for templates), all passing
- `ScenarioGenerator` — Turns a `ScenarioTemplate` into one concrete, random `GeneratedLayout` (attacker/defender coordinates + attacker targets) per call
  - Wraps a single seeded `random.Random` stream: seeding once makes a whole batch's sequence of layouts reproducible, while each call still draws a fresh layout
  - Shuffled round-robin target assignment when `predefined_targets=false`, so every target gets a fair share of attackers rather than relying on independent random picks
  - Runtime safety net for overlapping spawn areas: re-checks free cells for defenders after attackers are placed, raising a clear error if a particular random draw left no room
  - **Test Coverage:** 11 unit tests, all passing

**Scenario Loader Details:**
The `ScenarioLoader` is the entry point for all scenario and template data. It handles two distinct use cases:
1. **Concrete Scenarios** (`from_json()`, `from_csv()`): Load exact agent positions for single-run playback
   - Parses grid dimensions, fixed obstacles, target locations, and exact attacker/defender coordinates
   - Validates all coordinates are within grid bounds and on non-obstacle cells
   - Automatically assigns targets to attackers with no explicit target using round-robin from the target list
   - Raises `ScenarioValidationError` with actionable messages for all malformed or inconsistent inputs
   - Format support: JSON (structured object) or CSV (tag-based rows like `GRID`, `OBSTACLE`, `ATTACKER`)
   
2. **Scenario Templates** (`template_from_json()`, `template_from_csv()`): Load blueprints for batch mode
   - Parses grid, fixed obstacles/targets, and rectangular spawn areas (`attacker_area`, `defender_area`) with agent counts
   - Validates areas are within grid bounds; checks that spawn areas have enough free cells (not blocked by obstacles or targets) to fit the requested number of agents
   - Checks area overlap and validates consistency (e.g., if areas overlap, combined free cells must accommodate both agent counts)
   - The `predefined_targets` flag controls whether attackers get fixed targets or random targets each iteration
   - Returns a `ScenarioTemplate` object passed to `ScenarioGenerator` to produce many random layouts for batch runs
   - Raises `ScenarioValidationError` up-front before any iteration begins, preventing wasted computation
**Error Handling:**
- Comprehensive validation at parse time: type checking (integers only), bounds checking, and free-cell capacity verification
- Early failure on semantic errors (e.g., "attacker_area has only 2 free cells but num_attackers=10")
- Some edge cases are still being refined (e.g., agents spawned on obstacle cells in certain generation patterns); additional test scenarios have been prepared to catch and refine these cases in the coming week
#### Phase 6 (new): Strategy Comparison / Batch Mode — ✅ Complete
Runs every strategy against many randomly generated layouts from the same template and aggregates statistics, to compare strategies rather than just visualize one run.
- `BatchRunner` (`simulation_engine/batch_runner.py`) — For each iteration, generates one layout and runs it against every requested strategy, so all strategies are compared on identical spawn positions (a paired comparison)
  - Builds fresh `Grid`/`Agent` objects and a fresh strategy instance per (iteration, strategy) pair, since `Simulation` mutates both
  - Two independent failure modes, tracked separately: a layout-generation failure skips that iteration for every strategy equally; a single strategy's runtime failure is recorded as `None` for that (strategy, iteration) slot without invalidating the other strategies' results — every strategy's result list stays the same length and index-aligned, so iteration *i* means the same layout for everyone
  - Progress callback support for responsive UI updates during long batch runs
  - **Test Coverage:** 9 unit tests, all passing
- `batch_aggregator.aggregate()` (`simulation_engine/batch_aggregator.py`) — Reduces a `BatchResult` into one `StrategySummary` per strategy: mean/std success rate, mean targets protected/captured, mean arrival times (excluding runs where nobody arrived), defender efficiency, mean total steps, and a **win count** (how often each strategy protected the most targets on the same layout, ties awarded to all)
  - **Test Coverage:** 7 unit tests, all passing
- `BatchResultsWindow` (`visualization/batch_results_window.py`) — Modal pop-up displaying strategy comparison results in a scrollable table
  - Columns: Strategy name, success rate %, protected targets, captured targets, win count, mean defender efficiency
  - Rows: One per strategy
  - Wired to "Compare strategies from file…" button in `SimulationWindow`
  - Allows users to load a scenario template, specify iteration count, and view aggregated statistics across all three strategies

---

## Development Roadmap
### Completed (Phase 1-6)
- [x] Core grid, agent, pathfinding
- [x] Three allocation strategies with unit tests
- [x] Simulation engine with full history tracking
- [x] Implicit target protection for blocked paths
- [x] Statistics calculator
- [x] Deterministic map tests for BottleneckStrategy & Simulation Engine (52 tests passing)
- [x] Implement Tkinter GUI components (`SimulationWindow`, `GridCanvas`)
- [x] Create scenario loader (JSON/CSV parsing)
- [x] Integration tests: GUI + simulation engine
- [x] Scenario template format + free-cell/area validation
- [x] Random layout generator with seeded reproducibility
- [x] Batch runner (paired multi-strategy execution) + statistics aggregation
- [x] Batch comparison results pop-up (scrollable table)
- [x] Wire "Compare strategies from file…" button into `SimulationWindow`
- [ ] Refine visualization (smooth scrolling, zoom, grid highlighting)
- [ ] Performance profiling on large grids (100+ steps)
### Final
- [ ] End-to-end testing (all features)
- [ ] Edge case handling (invalid scenarios, very long simulations, etc.)
- [ ] Documentation cleanup

---

## Technology Stack

- **Backend**: Python 3.11+ (standard library only — no external dependencies)
- **Frontend**: Tkinter (included with Python standard library)
- **Testing**: Python unittest
- **Version Control**: Git
- **Optional**: Docker for containerized development

---

## Running the Project

**Run core tests:**
```bash
python -m unittest discover -s tests_unit
python -m unittest discover -s tests_deterministic
```

```bash
python main.py
```

**Single-Run Algorithm visualization Mode**
1. Load a built-in scenario or click "Load scenario from a file" (JSON/CSV) to add your own to the dropdown
2. Select an allocation strategy (Random, Greedy, or Bottleneck)
3. Click "Load & Run"
4. Use play/pause/step controls to explore the results

**Batch/Comparison Mode:**
1. Click "Compare strategies from file…" button
2. Select a scenario template file (JSON or CSV format)
3. Specify the number of iterations to run (each strategy will run once per layout, with all strategies tested on identical spawn positions)
4. The tool runs all three strategies (Random, Greedy, Bottleneck) in parallel across the random layouts
5. Results pop up in a sortable comparison table showing:
   - Success rate % (targets protected across all iterations)
   - Mean protected/captured targets per run
   - Win count (how many layouts each strategy protected the most targets)
   - Defender efficiency metric
   - Mean total steps to completion

---

## Code Quality & Design Notes

### Architecture Highlights
- **Modularity:** Each component (Grid, Agent, Simulation, Strategy) has a single, clear responsibility
- **Extensibility:** New allocation strategies can be added by implementing `AllocationStrategy` interface without modifying existing code
- **Immutability:** `StepSnapshot` uses frozen dataclass with immutable position tuples, preventing accidental mutations across steps
- **Error Handling:** Validation at entry points (Grid bounds, pathfinding start/goal, scenario loading); exceptions with meaningful messages
- **Documentation:** All classes have docstrings; complex logic (e.g., BottleneckStrategy BFS) is well-commented

### Testing Philosophy
- Unit tests for each component (Grid, Agent, PathFinder, Strategies, Statistics)
- Edge cases: boundaries, unreachable goals, start == goal, obstacles at unusual positions
- Deterministic tests use fixed grids and seeds for reproducibility
- Integration tests verify full simulation pipeline with all strategies

### Known Implementation Details

#### BottleneckStrategy
- Uses **8-connectivity** for obstacle grouping
- Uses **4-connectivity** for agent movement (only orthogonal moves), matching the paper's grid model
- **Centroid heuristic:** When multiple vertices tie for maximum path frequency, picks the one closest to the centroid of available defenders. This is a reasonable interpretation of the paper's "approximate location of defenders," but alternatives (median position, closest to any defender) have not been empirically compared.
- **Tie-breaking in gap detection:** BFS returns the shortest path between obstacle components; when multiple cells are equidistant, chooses the one closest to the frequency hotspot `w` for consistency and determinism.

---

## Progress Tracking

| Component | Status | Tests | Notes |
|-----------|--------|-------|-------|
| Grid | ✅ Complete | - | Full feature set |
| Agent | ✅ Complete | - | Basic movement, target assignment |
| PathFinder (A*) | ✅ Complete | ✅ 9 passing | Production-ready |
| AllocationStrategy (base) | ✅ Complete | — | Interface defined |
| RandomStrategy | ✅ Complete | ✅ 4 Tests Passing | Deterministic with seed |
| GreedyStrategy | ✅ Complete | ✅ 5 Tests Passing | Correct distance-based assignment |
| BottleneckStrategy | ✅ Complete | ✅ 13 Unit and 8 Deterministic Passing | Methods tested; end-to-end |
| Simulation Engine | ✅ Complete | ✅ 13 Unit Tests and 4 Deterministic tests Passing | Full pipeline working |
| Statistics Calculator | ✅ Complete | - | All metrics functional |
| Tkinter GUI | ✅ Complete (single-run mode) | - | File loader for custom maps; batch-mode UI still planned |
| Scenario Loader | ✅ Complete | ✅ 33 Unit Tests Passing | Concrete scenarios + new template format (areas/counts) |
| Scenario Generator | ✅ Complete | ✅ 11 Unit Tests Passing | Seeded random layouts from a template, for batch mode |
| Batch Runner | ✅ Complete | ✅ 9 Unit Tests Passing | Paired multi-strategy execution, per-iteration failure isolation |
| Batch Aggregator | ✅ Complete | ✅ 7 Unit Tests Passing | Mean/std, arrival times, win counts across a batch |
| Batch Results GUI | 📝 New | — | Scrollable comparison pop-up; button wiring into `SimulationWindow` |

---

## Known Limitations & Notes for Coming Week
 
- **Edge case testing:** Some edge cases in scenario validation (e.g., agent spawn patterns on obstacles in overlapping areas) are being tested with a comprehensive error scenario suite (36 test files covering all error categories). These will be refined if needed over the coming week.
- **UI refinements:** Minor polish and adjustments to UI elements may be made within the next week; core functionality is complete and tested.
- **No external dependencies:** Project uses only Python standard library (including Tkinter for GUI), making it lightweight and easy to run without package installation.
---
 
*Last updated: 28 September 2026 — Project feature-complete with batch mode fully integrated. Scenario loader supports both concrete scenarios and templates. All core components tested (102+ tests passing); edge case validation ongoing.*