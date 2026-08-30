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
│   ├── agent.py                 # Agent class (position, type, movement)
│   ├── agent_type.py            # AgentType enum (ATTACKER, DEFENDER)
│   ├── grid.py                  # Grid class (environment, obstacles, pathfinding queries)
│   └── grid_availability.py     # GridAvailability enum (PASSABLE, OBSTACLE, TAKEN)
│
├── allocation_strategies/
│   ├── allocation_strategy.py   # Base AllocationStrategy class
│   ├── random_strategy.py       # Random allocation
│   ├── greedy_strategy.py       # Greedy allocation
│   └── bottleneck_strategy.py   # Bottleneck simulation allocation
│
├── simulation_engine/
│   ├── simulation.py            # Main Simulation orchestrator (to be implemented)
│   ├── step_snapshot.py         # State snapshot data class (to be implemented)
│   └── statistics_calculator.py # Metrics derivation (to be implemented)
│
├── visualization/
│   └── simulation_window.py     # Tkinter GUI main window (to be implemented)
│
├── pathfinding/
│   ├── a_star.py                # A* algorithm implementation
│   └── path_finder.py           # PathFinder class wrapper
│
├── tests.py                     # Unit tests for core components
├── main.py                      # Application entry point (to be implemented)
├── requirements.txt             # Python dependencies
├── README.md                    # This file
└── .gitignore                   # Git ignore rules
```

---

## Features Implemented

### ✅ Phase 1: Core Components (In Progress)
 
- **Grid System** — 2D grid with obstacle tracking, passability queries, and neighbor lookups
  - Bounds checking on all operations
  - `GridAvailability` enum for cell states (PASSABLE, OBSTACLE, TAKEN)
  - Methods: `is_passable()`, `get_neighbors()`, `mark_obstacles()`, `mark_taken()`, `get_grid_state()`
- **Agent System** — Foundation for attackers and defenders
  - `Agent` class with position tracking and movement methods
  - `AgentType` enum to distinguish ATTACKER from DEFENDER
  - Methods: `move()`, `move_to()`
- **Pathfinding (A\* Algorithm)** — Collision-aware route planning
  - Complete A* implementation with Manhattan distance heuristic
  - Handles obstacles and grid boundaries
  - Error handling: raises `ValueError` for invalid/unreachable positions
  - Comprehensive test suite with 10 test cases (all passing)
  - Methods: `find_path(start, goal)` –> returns path as list of coordinates or None

### ✅ Testing Infrastructure
- Unit tests for Grid class (bounds checking, obstacles, passability)
- Unit tests for PathFinder (straight paths, obstacle avoidance, edge cases, unreachable goals)
- Unit tests for RandomStrategy, GreedyStrategy, and BottleneckStrategy
- All tests passing

### ✅ Phase 2: Allocation Strategies
 
- `AllocationStrategy` — Abstract base class defining the interface all strategies implement
- `RandomStrategy` — Assigns each defender to a random attacker target
- `GreedyStrategy` — Assigns each defender to its closest available target
- `BottleneckStrategy` — Simulates attacker paths to find high-traffic vertices, searches their
  vicinity for gaps between obstacle groups, and blocks those gaps with defenders; falls back to
  random assignment for any leftover defenders. Based on the "Bottleneck Simulation Allocation"
  method (section 4.3 of the reference paper, Ivanová & Surynek 2017).

---
 
## What's Next

### Immediate (This Week)
1. **Extend Agent Class** — Add target assignment, (health state), and `compute_next_move()` method
2. **Create Step Snapshot Data Class** — Holds grid state + statistics for each simulation step
3. Build Simulation class — orchestrates agent movement, strategy application, snapshot collection

### Short Term (Next 1-2 Weeks)
4. More testing on Bottleneck strategy
5. Implement Statistics Calculator — derives metrics from snapshots
6. Build scenario loader for JSON/CSV input validation

### Medium Term (Weeks 3-4)
9. Develop Tkinter GUI:
   - GridCanvas for side-by-side grid visualization
   - ControlPanel for play/pause/step controls
   - StatisticsPanel for real-time metrics display
10. Integrate simulation engine with GUI

### Final (Week 5)
11. End-to-end testing and edge case handling
12. Performance optimization if needed
13. Documentation and code cleanup

---

## Technology Stack

- **Backend**: Python 3.9+ (standard library only)
- **Frontend**: Tkinter (included with Python)
- **Testing**: Python unittest
- **Version Control**: Git

---

## Running the Project

### Current State
The core components are functional. You can test individual pieces:

```bash
# Run tests
python tests.py

# Test pathfinding interactively
python path_finder.py  # (if you add a __main__ block)
```

### Future: Complete Application
```bash
python main.py
```

---

## Development Notes

### Code Quality
- All classes have docstrings
- Error handling with meaningful exceptions (e.g., `ValueError` for invalid positions)
- Modular design: each class has a single responsibility
- Future strategies can be added by implementing `AllocationStrategy` interface

### Testing Philosophy
- Unit tests for each component
- Edge cases tested: boundaries, no path, start == goal, obstacles at start/goal
- Tests are clear and self-documenting
- Allocation strategy tests mock internal simulation/search steps where needed to keep
  behavior deterministic (pathfinding tie-breaks and set-iteration order are not
  guaranteed to be stable across runs)

### BottleneckStrategy notes (mostly for myself)
- Agent movement stays 4-connected throughout, matching the paper's grid model
  (section 2). Obstacle grouping in `_connected_components`/`touches_other_component`
  uses 8-connectivity, per the paper's footnote that two cells are "in distance 1"
  if they share at least one point — these are two intentionally different
  connectivity rules for two different purposes, not an inconsistency.
- **Resolved during testing:** the BFS in `_shortest_gap_between_components` used to
  return whichever candidate gap vertex was dequeued first, which is arbitrary when
  several vertices are equidistant from the obstacle groups (an 8-connectivity touch
  check can tie a "directly between the obstacles" vertex with a diagonal neighbor).
  Ties are now broken by proximity to `w` (the frequency hotspot that triggered the
  vicinity search), which is deterministic and consistent with the paper's own
  reasoning for using proximity as a selection criterion.
- The paper's optional refinement — re-simulating with a found bottleneck excluded to
  rule out "false" bottlenecks in indented/blind-alley maps — is not yet implemented.

### Known TODOs
- Full error handling for edge cases in `Simulation` class (coming in Phase 3)
- GUI optimization for large grids (Phase 4)
- Performance profiling for 100+ step simulations (Phase 5)
- Optional false-bottleneck filtering for `BottleneckStrategy` (see notes above)
---

## Progress Tracking

| Component | Status | Tests | Notes |
|-----------|--------|-------|-------|
| Grid | ✅ Complete | ✅ Passing | Fully functional with bounds checking |
| Agent | ✅ Complete | ✅ Passing | Basic structure; will extend with health state |
| PathFinder (A*) | ✅ Complete | ✅ All 10 passing | Production-ready |
| AllocationStrategy (base) | ✅ Complete | — | Interface implemented |
| RandomStrategy | ✅ Complete | ✅ Passing | |
| GreedyStrategy | ✅ Complete | ✅ Passing | |
| BottleneckStrategy | ✅ Complete | ✅ Passing | Tie-break fix applied (see Development Notes) |
| Simulation Engine | ⏳ Planned | — | Depends on strategies |
| Tkinter GUI | ⏳ Planned | — | Phase 4 |
| Scenario Loader | ⏳ Planned | — | Phase 3 |
| Statistics Calculator | ⏳ Planned | — | Phase 3 |

---
 
*Last updated: [31.08.26] — Phase 2 (Allocation Strategies) complete*