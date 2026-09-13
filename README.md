# MAPF-ISP
Individual Software Project Charles University
Author: Verkhniatska Yekateryna

# Adversarial Area Protection Visualization Tool

A Python-based interactive visualization and comparison tool for exploring defender allocation strategies in the Adversarial Area Protection (AAP) problem.

---

## Project Structure
 
```
MAP-ISP/
├── core_components/
│   ├── agent.py                 # ✅ Agent class (position, type, movement)
│   ├── agent_type.py            # ✅ AgentType enum (ATTACKER, DEFENDER)
│   ├── grid.py                  # ✅ Grid class (environment, obstacles, pathfinding queries)
│   └── grid_availability.py     # ✅ GridAvailability enum (PASSABLE, OBSTACLE, TAKEN)
│
├── allocation_strategies/
│   ├── allocation_strategy.py   # ✅ Base AllocationStrategy class
│   ├── random_strategy.py       # ✅ Random allocation
│   ├── greedy_strategy.py       # ✅ Greedy allocation
│   └── bottleneck_strategy.py   # ✅ Bottleneck simulation allocation
│
├── simulation_engine/
│   ├── simulation.py            # ✅ Simulation orchestrator
│   ├── step_snapshot.py         # ✅ State snapshot data class
│   └── statistics_calculator.py # ✅ Metrics derivation
│
├── pathfinding/
│   ├── a_star.py                # ✅ A* algorithm implementation
│   └── path_finder.py           # ✅ PathFinder class wrapper
│
├── tests/                       # 📝
|   ├── tests_general.py         # ✅ Unit tests for core components
|   ├── tests_bottleneck.py      # ✅ Deterministic map tests for BottleneckStrategy
|   ├── tests_simulation.py      # ✅ Unit tests for simulation components
│
├── visualization/
│   └── simulation_window.py     # ⏳ Tkinter GUI main window (not yet implemented)
│
├── scenarios/
│   └── scenario_loader.py       # ⏳ JSON/CSV scenario parsing (not yet implemented)
│
├── main.py                      # ⏳ Application entry point (not yet implemented)
├── requirements.txt             # ⏳ Python dependencies (not yet implemented)
├── README.md                    # This file
├── Dockerfile                   # Docker configuration
├── compose.yaml                 # Docker comppose.yaml file
├── README.Docker.md             # Docker README.md file with usage instructions
└── .gitignore                   # Git ignore rules
```

**Legend:** ✅ = Implemented and tested | ⏳ = Planned, not yet implemented | 📝 = New in this version

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

#### Phase 3: Simulation Engine
- `Simulation` — Orchestrates step-by-step simulation
  - Single-stage defender allocation (strategy applied once)
  - LRA* agent movement: agents replan one step at a time against current grid occupancy
  - Defenders move before attackers each turn (per paper's turn-based framing)
  - Collision-free movement: agents avoid occupied cells and obstacles
  - Target resolution: tracks captured and protected targets
  - Full history recording: snapshots captured at every step (including step 0)
  - **Methods:** `step()`, `run()`, `_check_finished()`
  - **Test Coverage:** Integration tests with all three strategies

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

---

### ⏳ Not Yet Implemented (Frontend & Integration)

#### Phase 4: Tkinter GUI (Next Priority)
- `SimulationWindow` — Main application window
  - File dialog for scenario selection
  - Strategy selection dropdown (Random, Greedy, Bottleneck)
  - Simulation execution trigger
  - Play/pause/step forward/step backward controls
  - Current step display

- `GridCanvas` — Custom canvas widget for visualization
  - Side-by-side grid rendering (two strategies simultaneously)
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

#### Phase 5: Scenario Management (Planned)
- `ScenarioLoader` — Parse and validate input
  - JSON format: `{ "width": int, "height": int, "obstacles": [[x, y], ...], "attackers": [{x, y, target}, ...], "defenders": [{x, y}, ...], "targets": [[x, y], ...] }`
  - CSV format: One row per entity type (grid dimensions, obstacles, agents, targets)
  - Validation: grid dimensions positive, agent counts non-negative, all positions within bounds
  - Error messages for malformed input

- Predefined benchmark scenarios from the research paper (if available)

#### Phase 6: Result Export (Planned)
- Export simulation history to JSON
- Export statistics summary to text/CSV
- Screenshot/video rendering of playback

---

## Development Roadmap

### Completed (Phase 1-3)
- [x] Core grid, agent, pathfinding
- [x] Three allocation strategies with unit tests
- [x] Simulation engine with full history tracking
- [x] Statistics calculator

### Next (Immediate)
- [x] Deterministic map tests for BottleneckStrategy (structure defined, ready to implement)
- [ ] Address professor feedback on centroid heuristic (analysis provided, optional experiment planned)
- [x] Update README to reflect actual implementation

### Short Term (1-2 Weeks)
- [ ] Implement Tkinter GUI components
- [ ] Create scenario loader (JSON/CSV parsing)
- [ ] Integration tests: GUI + simulation engine

### Medium Term (2-4 Weeks)
- [ ] Refine visualization (smooth scrolling, zoom, grid highlighting)
- [ ] Add predefined benchmark scenarios
- [ ] Performance profiling on large grids (100+ steps)

### Final (4-5 Weeks)
- [ ] End-to-end testing (all features)
- [ ] Edge case handling (invalid scenarios, very long simulations, etc.)
- [ ] Documentation cleanup
- [ ] Package for submission

---

## Technology Stack

- **Backend**: Python 3.9+ (standard library only — no external dependencies)
- **Frontend**: Tkinter (included with Python standard library)
- **Testing**: Python unittest
- **Version Control**: Git
- **Optional**: Docker for containerized development

---

## Running the Project

### Current State (Backend Only)

**Run core tests:**
```bash
python -m unittest discover -s tests
```

### Future (Complete Application)

```bash
python main.py
```
Then use the GUI to:
1. Upload a scenario file (JSON/CSV)
2. Select two allocation strategies
3. Click "Run Simulation"
4. Use play/pause/step controls to explore the results

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
- Uses **4-connectivity** for obstacle grouping
- Uses **4-connectivity** for agent movement (only orthogonal moves), matching the paper's grid model
- **Centroid heuristic:** When multiple vertices tie for maximum path frequency, picks the one closest to the centroid of available defenders. This is a reasonable interpretation of the paper's "approximate location of defenders," but alternatives (median position, closest to any defender) have not been empirically compared.
- **Tie-breaking in gap detection:** BFS returns the shortest path between obstacle components; when multiple cells are equidistant, chooses the one closest to the frequency hotspot `w` for consistency and determinism.

---

## Progress Tracking

| Component | Status | Tests | Notes |
|-----------|--------|-------|-------|
| Grid | ✅ Complete | ✅ 15+ passing | Full feature set |
| Agent | ✅ Complete | ✅ Passing | Basic movement, target assignment |
| PathFinder (A*) | ✅ Complete | ✅ 10 passing | Production-ready |
| AllocationStrategy (base) | ✅ Complete | — | Interface defined |
| RandomStrategy | ✅ Complete | ✅ Passing | Deterministic with seed |
| GreedyStrategy | ✅ Complete | ✅ Passing | Correct distance-based assignment |
| BottleneckStrategy | ✅ Complete | ✅ 10+ passing | Methods tested; end-to-end (new) |
| Simulation Engine | ✅ Complete | ✅ Passing | Full pipeline working |
| Statistics Calculator | ✅ Complete | ✅ Passing | All metrics functional |
| Deterministic Map Tests | 📝 New | 3 | Structure defined, examples ready |
| Tkinter GUI | ⏳ Planned | — | Phase 4 |
| Scenario Loader | ⏳ Planned | — | Phase 5 |
| Result Export | ⏳ Planned | — | Phase 6 |

---

*Last updated: September 2026 — Backend complete, feedback integrated, roadmap clarified*