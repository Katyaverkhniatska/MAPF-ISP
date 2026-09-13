"""
SimulationWindow - Main Tkinter GUI for MAPF-ISP Visualization
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List

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
from visualization.scenario_selector import ScenarioSelector
from visualization.statistics_panel import StatisticsPanel
from visualization.control_panel import ControlPanel

# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class SimulationWindow(tk.Tk):
    """Main application window."""

    PLAYBACK_INTERVAL_MS = 500   # milliseconds between auto-steps

    def __init__(self):
        super().__init__()
        self.title("MAPF-ISP Visualization")
        self.resizable(True, True)

        self.history:    List[StepSnapshot]        = []
        self.calculator: Optional[StatisticsCalculator] = None
        self.current_step = 0
        self._playback_job = None          # holds the `after` job id

        self._build_ui()

    # -------------------- UI --------------------

    def _build_ui(self):
        # -------------------- top bar --------------------
        self.scenario_selector = ScenarioSelector(self, on_load=self._load_scenario)
        self.scenario_selector.pack(fill=tk.X, padx=6, pady=6)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # -------------------- centre: scrollable canvas area --------------------
        centre = ttk.Frame(self)
        centre.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # left side: canvas inside a fixed-size container
        self.canvas_frame = ttk.Frame(centre)
        self.canvas_frame.pack(side=tk.LEFT, anchor="nw")

        self.grid_canvas = GridCanvas(self.canvas_frame, Grid(7, 7, []))
        self.grid_canvas.pack()

        # right side: statistics
        self.stats_panel = StatisticsPanel(centre)
        self.stats_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(12, 0))

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # -------------------- bottom: controls --------------------
        self.control_panel = ControlPanel(
            self,
            on_play=self._play,
            on_pause=self._pause,
            on_step_forward=self._step_forward,
            on_step_back=self._step_back,
        )
        self.control_panel.pack(fill=tk.X, padx=6, pady=6)

    # -------------------- LOADING SCENARIOS --------------------

    def _load_scenario(self, scenario_key: str, strategy_name: str):
        """Build scenario, run simulation, reset display to step 0."""
        # Stop any ongoing playback first
        self._pause()

        try:
            grid, attackers, defenders, targets = self._build_scenario(scenario_key)

            # Assign attacker targets (round-robin if more attackers than targets)
            for i, attacker in enumerate(attackers):
                attacker.set_target(targets[i % len(targets)])

            strategy = {
                "Random":     RandomStrategy(),
                "Greedy":     GreedyStrategy(),
                "Bottleneck": BottleneckStrategy(use_true_targets=True),
            }[strategy_name]

            sim = Simulation(grid, defenders, attackers, targets, strategy, max_steps=50)
            sim.run()

            self.history    = sim.history
            self.calculator = StatisticsCalculator(self.history)

            self.grid_canvas.set_grid(grid)
            self.current_step = 0
            self._refresh_display()

        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load scenario:\n{exc}")

    # -------------------- PLAYBACK --------------------

    def _play(self):
        """Start or resume auto-stepping using Tkinter's after()."""
        if not self.history:
            return
        if self._playback_job is not None:
            return                     # already playing
        self._schedule_next_step()

    def _schedule_next_step(self):
        """Schedule one step-forward tick on the main thread."""
        if self.current_step < len(self.history) - 1:
            self._playback_job = self.after(self.PLAYBACK_INTERVAL_MS, self._auto_step)
        else:
            # Reached the end
            self._playback_job = None
            self.control_panel.set_stopped()

    def _auto_step(self):
        """Called by the after() scheduler — advances one step."""
        self._playback_job = None
        if self.current_step < len(self.history) - 1:
            self.current_step += 1
            self._refresh_display()
            self._schedule_next_step()
        else:
            self.control_panel.set_stopped()

    def _pause(self):
        if self._playback_job is not None:
            self.after_cancel(self._playback_job)
            self._playback_job = None
        self.control_panel.set_stopped()

    def _step_forward(self):
        self._pause()
        print("Step forward button clicked")
        if self.history and self.current_step < len(self.history) - 1:
            self.current_step += 1
            self._refresh_display()

    def _step_back(self):
        self._pause()
        print("Step back button clicked")
        if self.history and self.current_step > 0:
            self.current_step -= 1
            self._refresh_display()

    # -------------------- DISPLAY SYNC --------------------

    def _refresh_display(self):
        if not self.history:
            return
        snapshot = self.history[self.current_step]
        self.grid_canvas.update_snapshot(snapshot)
        assert self.calculator is not None, "StatisticsCalculator should be initialized"
        self.stats_panel.update(snapshot, self.calculator)
        self.control_panel.update_step(self.current_step, len(self.history) - 1)

    # -------------------- SCENARIOS --------------------

    def _build_scenario(self, key: str):
        """Returns (Grid, attackers, defenders, targets)."""
        if key == "empty_7x7":
            grid = Grid(7, 7, obstacles=[])
            attackers = [Agent(0, 3, AgentType.ATTACKER), Agent(0, 4, AgentType.ATTACKER)]
            defenders = [Agent(6, 3, AgentType.DEFENDER), Agent(6, 4, AgentType.DEFENDER)]
            targets   = [(3, 3), (3, 4)]

        elif key == "bottleneck_passage":
            grid = Grid(7, 7, obstacles=[(3, 0), (3, 1), (3, 5), (3, 6)])
            attackers = [Agent(0, 2, AgentType.ATTACKER), Agent(0, 4, AgentType.ATTACKER)]
            defenders = [Agent(1, 2, AgentType.DEFENDER),
                         Agent(1, 3, AgentType.DEFENDER),
                         Agent(1, 4, AgentType.DEFENDER)]
            targets   = [(5, 2), (5, 4)]

        else:  # complex_obstacles
            obstacles = [(2,1),(2,2),(2,3),(4,0),(4,1),(4,2),(6,2),(6,3),(6,4)]
            grid = Grid(8, 6, obstacles=obstacles)
            attackers = [Agent(0, 2, AgentType.ATTACKER), Agent(0, 4, AgentType.ATTACKER)]
            defenders = [Agent(1, 1, AgentType.DEFENDER),
                         Agent(1, 3, AgentType.DEFENDER),
                         Agent(1, 5, AgentType.DEFENDER)]
            targets   = [(6, 1), (6, 4)]

        return grid, attackers, defenders, targets