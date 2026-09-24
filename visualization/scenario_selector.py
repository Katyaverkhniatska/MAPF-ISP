import tkinter as tk
from tkinter import ttk

class ScenarioSelector(ttk.Frame):
    """Scenario + strategy dropdowns and Load & Run button."""

    SCENARIOS = {
        "Empty 7x7 (2v2)":              "empty_7x7",
        "Bottleneck Passage (2v3)":     "bottleneck_passage",
        "Complex Obstacles (2v3) A":    "complex_obstacles_a",
        "Complex Obstacles (2v3) B":    "complex_obstacles_b"
    }

    def __init__(self, parent, on_load, on_browse, **kwargs):
        super().__init__(parent, **kwargs)
        self._on_load = on_load

        self.scenarios = dict(self.SCENARIOS)   # per-instance copy

        ttk.Button(self, text="Load scenario from a file",
                command=on_browse).pack(side=tk.LEFT, padx=(5, 12))

        ttk.Label(self, text="Scenario:").pack(side=tk.LEFT, padx=5)
        self.scenario_var = tk.StringVar(value=list(self.SCENARIOS)[0])
        self.scenario_box = ttk.Combobox(self, textvariable=self.scenario_var,
                                     values=list(self.scenarios), state="readonly",
                                     width=26)
        self.scenario_box.pack(side=tk.LEFT, padx=4)

        ttk.Label(self, text="Strategy:").pack(side=tk.LEFT, padx=8)
        self.strategy_var = tk.StringVar(value="Random")
        ttk.Combobox(self, textvariable=self.strategy_var,
                     values=["Random", "Greedy", "Bottleneck"],
                     state="readonly", width=14).pack(side=tk.LEFT, padx=4)

        ttk.Button(self, text="Load & Run",
                   command=self._handle_load).pack(side=tk.LEFT, padx=12)

    def add_scenario(self, name: str, key: str):
        """Register a new entry and select it."""
        self.scenarios[name] = key
        self.scenario_box.config(values=list(self.scenarios))
        self.scenario_var.set(name)

    def _handle_load(self):
        key = self.scenarios[self.scenario_var.get()]
        self._on_load(key, self.strategy_var.get())
