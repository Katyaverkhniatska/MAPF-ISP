"""
SimulationWindow - Main Tkinter GUI for MAPF-ISP Visualization

Displays a single algorithm execution with:
- GridCanvas: Rectangle-based grid rendering
- ControlPanel: Play/Pause/Step/Back controls
- StatisticsPanel: Real-time metrics
- ScenarioSelector: Dropdown for hardcoded test scenarios
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List
import threading

from core_components.agent import Agent
from core_components.agent_type import AgentType
from core_components.grid import Grid, Vertex
from allocation_strategies.random_strategy import RandomStrategy
from allocation_strategies.greedy_strategy import GreedyStrategy
from allocation_strategies.bottleneck_strategy import BottleneckStrategy
from simulation_engine.simulation import Simulation
from simulation_engine.step_snapshot import StepSnapshot
from simulation_engine.statistics_calculator import StatisticsCalculator
from visualization.grid_canvas import GridCanvas
from visualization.control_panel import ControlPanel
from visualization.statistics_panel import StatisticsPanel


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


class SimulationWindow(tk.Tk):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.title("MAPF-ISP Visualization")
        self.geometry("900x800")
        
        self.grid_obj: Optional[Grid] = None
        self.simulation: Optional[Simulation] = None
        self.history: List[StepSnapshot] = []
        self.calculator: Optional[StatisticsCalculator] = None
        self.current_step = 0
        self.playback_thread: Optional[threading.Thread] = None
        self.playing = False
        
        # Layout: top toolbar, canvas, control panel, stats panel
        self._build_ui()
    
    def _build_ui(self):
        """Build the main UI."""
        # Top: Scenario selector
        self.scenario_selector = ScenarioSelector(
            self, on_scenario_selected=self._load_scenario
        )
        self.scenario_selector.pack(fill=tk.X, padx=5, pady=5)
        
        # Center: Grid canvas
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = GridCanvas(canvas_frame, Grid(1, 1, []))
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Bottom: Control panel
        self.control_panel = ControlPanel(
            self,
            on_play=self._play,
            on_pause=self._pause,
            on_step_forward=self._step_forward,
            on_step_back=self._step_back
        )
        self.control_panel.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Right: Statistics panel
        self.stats_panel = StatisticsPanel(self)
        self.stats_panel.pack(fill=tk.BOTH, side=tk.RIGHT, padx=5, pady=5)
    
    def _load_scenario(self, scenario_key: str, strategy_name: str):
        """Load a scenario and run the simulation."""
        try:
            # Reset UI state
            self.playing = False
            self.current_step = 0
            self.control_panel.stop_playback()
            
            # Build scenario
            grid_obj, attackers, defenders, targets = self._build_scenario(scenario_key)
            
            # Set attacker targets
            for i, attacker in enumerate(attackers):
                attacker.set_target(targets[i % len(targets)])
            
            # Create strategy
            if strategy_name == "Random":
                strategy = RandomStrategy()
            elif strategy_name == "Greedy":
                strategy = GreedyStrategy()
            else:  # Bottleneck
                strategy = BottleneckStrategy(use_true_targets=True)
            
            # Run simulation
            self.grid_obj = grid_obj
            self.simulation = Simulation(
                grid_obj, defenders, attackers, targets, strategy, max_steps=50
            )
            self.history = self.simulation.history
            self.calculator = StatisticsCalculator(self.history)
            
            # Update UI
            self.canvas = GridCanvas(self.canvas.master, self.grid_obj)
            self.canvas.pack(fill=tk.BOTH, expand=True)
            self._update_display()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load scenario:\n{str(e)}")
    
    def _build_scenario(self, scenario_key: str):
        """Build a scenario. Returns (grid, attackers, defenders, targets)."""
        if scenario_key == "empty_7x7":
            grid = Grid(7, 7, obstacles=[])
            
            a1 = Agent(0, 3, AgentType.ATTACKER)
            a2 = Agent(0, 4, AgentType.ATTACKER)
            attackers = [a1, a2]
            
            d1 = Agent(6, 3, AgentType.DEFENDER)
            d2 = Agent(6, 4, AgentType.DEFENDER)
            defenders = [d1, d2]
            
            targets = [(3, 3), (3, 4)]
            
        elif scenario_key == "bottleneck_passage":
            obstacles = [(3, 0), (3, 1), (3, 5), (3, 6)]
            grid = Grid(7, 7, obstacles=obstacles)
            
            a1 = Agent(0, 2, AgentType.ATTACKER)
            a2 = Agent(0, 4, AgentType.ATTACKER)
            attackers = [a1, a2]
            
            d1 = Agent(1, 2, AgentType.DEFENDER)
            d2 = Agent(1, 3, AgentType.DEFENDER)
            d3 = Agent(1, 4, AgentType.DEFENDER)
            defenders = [d1, d2, d3]
            
            targets = [(5, 2), (5, 4)]
            
        else:  # complex_obstacles
            obstacles = [
                (2, 1), (2, 2), (2, 3),
                (4, 0), (4, 1), (4, 2),
                (6, 2), (6, 3), (6, 4),
            ]
            grid = Grid(8, 6, obstacles=obstacles)
            
            a1 = Agent(0, 2, AgentType.ATTACKER)
            a2 = Agent(0, 4, AgentType.ATTACKER)
            attackers = [a1, a2]
            
            d1 = Agent(1, 1, AgentType.DEFENDER)
            d2 = Agent(1, 3, AgentType.DEFENDER)
            d3 = Agent(1, 5, AgentType.DEFENDER)
            defenders = [d1, d2, d3]
            
            targets = [(6, 1), (6, 4)]
        
        return grid, attackers, defenders, targets
    
    def _update_display(self):
        """Update canvas and stats for current step."""
        if 0 <= self.current_step < len(self.history):
            snapshot = self.history[self.current_step]
            self.canvas.update_snapshot(snapshot)
            self.stats_panel.update_stats(snapshot, self.calculator)
            self.control_panel.update_step_display(
                self.current_step, len(self.history) - 1
            )
    
    def _play(self):
        """Start continuous playback."""
        self.playing = True
        self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self.playback_thread.start()
    
    def _pause(self):
        """Pause playback."""
        self.playing = False
    
    def _playback_loop(self):
        """Background thread for continuous playback."""
        while self.playing and self.current_step < len(self.history) - 1:
            self.current_step += 1
            self.after(500, self._update_display)  # 500ms per step
            import time
            time.sleep(0.5)
        
        # Reached end
        self.playing = False
        self.after(self.control_panel.stop_playback)
    
    def _step_forward(self):
        """Step to next snapshot."""
        if self.current_step < len(self.history) - 1:
            self.current_step += 1
            self._update_display()
    
    def _step_back(self):
        """Step to previous snapshot."""
        if self.current_step > 0:
            self.current_step -= 1
            self._update_display()


if __name__ == "__main__":
    app = SimulationWindow()
    app.mainloop()