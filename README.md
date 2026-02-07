# MAPF-ISP
Individual Software Project Charles University
Author: Verkhniatska Yekateryna

## Project final structure plan:
```
📦 Area Protection System
├── 🗺️  Core Components
│   ├── Grid/Graph representation
│   ├── Agent system (Attackers & Defenders)
│   ├── Pathfinding (LRA* algorithm)
│   └── Collision/conflict detection
├── 🎯 Allocation Strategies
│   ├── Random allocation
│   ├── Greedy allocation
│   └── Bottleneck simulation
├── ⚙️  Simulation Engine
│   └── Turn-based movement system
└── 📊 Visualization
    ├── Grid renderer
    ├── Agent display
    └── Statistics/metrics
```

## Currently
```area_protection_system.py``` is the core.

Execution:
- run ```python demo_script.py``` to run different tests without GUI to simplify testing and comparing.
- run ```python gui_application.py``` to run the full GUI application