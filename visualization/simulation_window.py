"""
SimulationWindow - Main Tkinter GUI for MAPF-ISP Visualization
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from typing import Optional, List, Dict
from pathlib import Path

from core_components.agent import Agent
from core_components.agent_type import AgentType
from core_components.grid import Grid, Vertex
from simulation_engine.simulation import Simulation
from simulation_engine.step_snapshot import StepSnapshot
from simulation_engine.statistics_calculator import StatisticsCalculator
from simulation_engine.batch_runner import BatchRunner, STRATEGY_FACTORIES
from simulation_engine.batch_aggregator import aggregate
from visualization.grid_canvas import GridCanvas
from visualization.scenario_selector import ScenarioSelector
from visualization.statistics_panel import StatisticsPanel
from visualization.control_panel import ControlPanel
from visualization.batch_results_window import BatchResultsWindow
from scenario_management.scenario_loader import ScenarioLoader, ScenarioValidationError, ScenarioTemplate


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
        self.loaded_files: Dict[str, Path] = {}

        self._build_ui()

    # -------------------- UI --------------------

    def _build_ui(self):
        # -------------------- top bar --------------------
        self.scenario_selector = ScenarioSelector(self, on_load=self._load_scenario, on_browse=self._browse_file)
        self.scenario_selector.pack(fill=tk.X, padx=6, pady=6)

        # -------------------- batch/comparison mode --------------------
        compare_bar = ttk.Frame(self)
        compare_bar.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(
            compare_bar, text="Compare strategies from file…",
            command=self._browse_compare_file,
        ).pack(side=tk.LEFT, padx=5)

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
    def _parse_file(self, path: Path):
        suffix = path.suffix.lower()
        if suffix == ".json":
            return ScenarioLoader.from_json(path)
        if suffix == ".csv":
            return ScenarioLoader.from_csv(path)
        raise ScenarioValidationError(
            f"Unsupported file type '{path.suffix}'. Use .json or .csv.")

    def _browse_file(self):
        chosen = filedialog.askopenfilename(
            title="Load scenario from a file",
            filetypes=[("Scenario files", "*.json *.csv"),
                    ("JSON", "*.json"), ("CSV", "*.csv")])
        if not chosen:
            return                       # dialog cancelled
        path = Path(chosen)
        try:
            self._parse_file(path)       # validate now; result is discarded
        except (ScenarioValidationError, OSError, UnicodeDecodeError) as exc:
            messagebox.showerror("Invalid scenario file", str(exc))
            return

        name, n = path.stem, 2
        while name in self.scenario_selector.scenarios:
            name = f"{path.stem} ({n})"
            n += 1
        key = f"file:{name}"
        self.loaded_files[key] = path
        self.scenario_selector.add_scenario(name, key)

    def _load_scenario(self, scenario_key: str, strategy_name: str):
        """Build scenario, run simulation, reset display to step 0."""
        # Stop any ongoing playback first
        self._pause()

        try:
            if scenario_key in self.loaded_files:
                sc = self._parse_file(self.loaded_files[scenario_key])
                grid, attackers, defenders, targets = sc.grid, sc.attackers, sc.defenders, sc.targets
            else:
                grid, attackers, defenders, targets = self._build_scenario(scenario_key)
                # Round-robin target assignment only applies to the
                # hardcoded built-in scenarios. File-loaded scenarios
                # already have their targets assigned by ScenarioLoader
                # (including its own round-robin fallback for attackers
                # with no explicit target) -- reassigning here would
                # silently overwrite whatever the file actually specified.
                for i, attacker in enumerate(attackers):
                    attacker.set_target(targets[i % len(targets)])

            strategy = STRATEGY_FACTORIES[strategy_name]()

            sim = Simulation(grid, defenders, attackers, targets, strategy, max_steps=50)
            sim.run()

            self.history    = sim.history
            self.calculator = StatisticsCalculator(self.history)

            self.grid_canvas.set_grid(grid)
            self.current_step = 0
            self._refresh_display()

        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load scenario:\n{exc}")

    # -------------------- BATCH / COMPARISON MODE --------------------

    def _parse_template_file(self, path: Path) -> ScenarioTemplate:
        suffix = path.suffix.lower()
        if suffix == ".json":
            return ScenarioLoader.template_from_json(path)
        if suffix == ".csv":
            return ScenarioLoader.template_from_csv(path)
        raise ScenarioValidationError(
            f"Unsupported file type '{path.suffix}'. Use .json or .csv.")

    def _browse_compare_file(self):
        chosen = filedialog.askopenfilename(
            title="Compare strategies from a template file",
            filetypes=[("Scenario template files", "*.json *.csv"),
                       ("JSON", "*.json"), ("CSV", "*.csv")])
        if not chosen:
            return  # dialog cancelled
        path = Path(chosen)

        try:
            template = self._parse_template_file(path)
        except (ScenarioValidationError, OSError, UnicodeDecodeError) as exc:
            messagebox.showerror("Invalid template file", str(exc))
            return

        iterations = simpledialog.askinteger(
            "Batch iterations", "Number of iterations per strategy:",
            initialvalue=50, minvalue=1, parent=self,
        )
        if iterations is None:
            return  # cancelled

        strategy_names = list(STRATEGY_FACTORIES.keys())

        try:
            result = self._run_batch_with_progress(template, strategy_names, iterations)
        except ScenarioValidationError as exc:
            # e.g. predefined_targets=true with the wrong number of
            # targets -- BatchRunner validates this up front, before any
            # iteration runs, so we land here without wasting any time.
            messagebox.showerror("Invalid template", str(exc))
            return
        except Exception as exc:
            messagebox.showerror("Error", f"Batch run failed:\n{exc}")
            return

        summary = aggregate(result)
        BatchResultsWindow(self, summary, template_label=path.name)

    def _run_batch_with_progress(self, template: ScenarioTemplate,
                                  strategy_names: List[str], iterations: int):
        """
        Runs BatchRunner on the main thread -- there's no worker thread
        yet, so this call blocks the GUI for the duration of the batch.
        A small modal progress window is refreshed after every iteration
        via BatchRunner's on_progress callback, so the window at least
        shows visible progress instead of appearing frozen. For a large
        iteration count or large grids, moving this to a background
        thread would be the next improvement.
        """
        progress_win = tk.Toplevel(self)
        progress_win.title("Running comparison…")
        progress_win.transient(self)
        progress_win.grab_set()
        progress_win.resizable(False, False)

        label = ttk.Label(progress_win, text=f"0 / {iterations} iterations")
        label.pack(padx=20, pady=(15, 5))
        bar = ttk.Progressbar(progress_win, mode="determinate",
                               maximum=iterations, length=280)
        bar.pack(padx=20, pady=(0, 15))

        def on_progress(done: int, total: int):
            bar["value"] = done
            label.config(text=f"{done} / {total} iterations")
            progress_win.update_idletasks()

        try:
            runner = BatchRunner(template, strategy_names, iterations)  # validates the template fast
            return runner.run(on_progress=on_progress)
        finally:
            progress_win.destroy()

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
        if self.history and self.current_step < len(self.history) - 1:
            self.current_step += 1
            self._refresh_display()

    def _step_back(self):
        self._pause()
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
        def make_attacker(x, y, grid: Grid):
            """Build an attacker and also marks the attacker's position as taken in the grid."""
            attacker = Agent(x, y, AgentType.ATTACKER)
            grid.mark_taken(attacker.get_position())
            return attacker

        def make_defender(x, y):
            """Build a defender."""
            defender = Agent(x, y, AgentType.DEFENDER)
            return defender
        
        """Returns (Grid, attackers, defenders, targets)."""
        if key == "empty_7x7":
            grid = Grid(7, 7, obstacles=[])
            attackers = [make_attacker(0, 3, grid), make_attacker(0, 4, grid)]
            defenders = [make_defender(6, 3), make_defender(6, 4)]
            targets   = [(3, 3), (3, 4)]

        elif key == "bottleneck_passage":
            grid = Grid(10, 10, obstacles=[(5, 0), (5, 1), (5, 2), (6, 5), (6, 6), (6, 7), (6, 8), (6, 9)])
            attackers = [make_attacker(0, 4, grid), make_attacker(0, 6, grid)]
            defenders = [make_defender(1, 4),
                         make_defender(1, 5),
                         make_defender(1, 6)]
            targets   = [(9, 4), (9, 7)]

        elif key == "complex_obstacles_a":  # complex_obstacles
            obstacles = [(2,1), (2,2), (2,3), (2,6), (4,0), (4,1), (4,2), (5, 6),
                         (5,7), (6,2), (6,3), (6,4)]
            grid = Grid(10, 8, obstacles=obstacles)
            attackers = [make_attacker(0, 2, grid), make_attacker(0, 4, grid)]
            defenders = [make_defender(3, 1),
                         make_defender(3, 3),
                         make_defender(3, 5)]
            targets   = [(9, 1), (9, 4)]

        else:
            obstacles = [(2,1), (2,2), (2,3), (2,6), (4,0), (4,1), (4,2), (5, 6),
                            (5,7), (6,2), (6,3), (6,4)]
            grid = Grid(10, 8, obstacles=obstacles)
            attackers = [make_attacker(0, 2, grid), make_attacker(0, 4, grid)]
            defenders = [make_defender(1, 1),
                            make_defender(1, 3),
                            make_defender(1, 5)]
            targets   = [(9, 1), (9, 4)]

        return grid, attackers, defenders, targets