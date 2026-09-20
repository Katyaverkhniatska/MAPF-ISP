import tkinter as tk
from tkinter import ttk

class ScenarioSelector(ttk.Frame):
    """Scenario + strategy dropdowns and Load & Run button."""

    SCENARIOS = {
        "Empty 7x7 (2v2)":       "empty_7x7",
        "Bottleneck Passage (2v3)": "bottleneck_passage",
        "Complex Obstacles (2v3)":  "complex_obstacles",
    }

    def __init__(self, parent, on_load, **kwargs):
        super().__init__(parent, **kwargs)
        self._on_load = on_load

        ttk.Label(self, text="Scenario:").pack(side=tk.LEFT, padx=5)
        self.scenario_var = tk.StringVar(value=list(self.SCENARIOS)[0])
        ttk.Combobox(self, textvariable=self.scenario_var,
                     values=list(self.SCENARIOS), state="readonly",
                     width=26).pack(side=tk.LEFT, padx=4)

        ttk.Label(self, text="Strategy:").pack(side=tk.LEFT, padx=8)
        self.strategy_var = tk.StringVar(value="Random")
        ttk.Combobox(self, textvariable=self.strategy_var,
                     values=["Random", "Greedy", "Bottleneck"],
                     state="readonly", width=14).pack(side=tk.LEFT, padx=4)

        ttk.Button(self, text="Load & Run",
                   command=self._handle_load).pack(side=tk.LEFT, padx=12)

    def _handle_load(self):
        key = self.SCENARIOS[self.scenario_var.get()]
        self._on_load(key, self.strategy_var.get())
