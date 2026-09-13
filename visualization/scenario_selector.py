import tkinter as tk
from tkinter import ttk

class ScenarioSelector(ttk.Frame):
    """Dropdown to select and run hardcoded scenarios."""
    
    SCENARIOS = {
        "Empty 7x7 (2v2)": "empty_7x7",
        "Bottleneck Passage (2v3)": "bottleneck_passage",
        "Complex Obstacles": "complex_obstacles",
    }
    
    def __init__(self, parent, on_scenario_selected, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.on_scenario_selected = on_scenario_selected
        
        ttk.Label(self, text="Scenario:").pack(side=tk.LEFT, padx=5)
        
        self.scenario_var = tk.StringVar(value=list(self.SCENARIOS.keys())[0])
        scenario_dropdown = ttk.Combobox(
            self,
            textvariable=self.scenario_var,
            values=list(self.SCENARIOS.keys()),
            state="readonly",
            width=25
        )
        scenario_dropdown.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(self, text="Strategy:").pack(side=tk.LEFT, padx=5)
        
        self.strategy_var = tk.StringVar(value="Random")
        strategy_dropdown = ttk.Combobox(
            self,
            textvariable=self.strategy_var,
            values=["Random", "Greedy", "Bottleneck"],
            state="readonly",
            width=15
        )
        strategy_dropdown.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            self, text="Load & Run", command=self._handle_load
        ).pack(side=tk.LEFT, padx=10)
    
    def _handle_load(self):
        scenario_key = self.SCENARIOS[self.scenario_var.get()]
        strategy_name = self.strategy_var.get()
        self.on_scenario_selected(scenario_key, strategy_name)
