import tkinter as tk
from tkinter import ttk

from simulation_engine.step_snapshot import StepSnapshot
from simulation_engine.statistics_calculator import StatisticsCalculator

class StatisticsPanel(ttk.Frame):
    """Real-time statistics display."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        frame = ttk.LabelFrame(self, text="Statistics", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.stat_labels = {}
        rows = [
            ("targets_captured",  "Captured:"),
            ("targets_protected", "Protected:"),
            ("targets_empty",     "Empty:"),
            ("success_rate",      "Success Rate:"),
            ("avg_attacker_time", "Avg Attacker Time:"),
            ("avg_defender_time", "Avg Defender Time:"),
        ]
        for key, text in rows:
            row = ttk.Frame(frame)
            row.pack(fill=tk.X, pady=3)
            ttk.Label(row, text=text, width=19).pack(side=tk.LEFT)
            lbl = ttk.Label(row, text="—", font=("Courier", 10))
            lbl.pack(side=tk.LEFT)
            self.stat_labels[key] = lbl

    def update(self, snapshot: StepSnapshot, calc: StatisticsCalculator):
        self.stat_labels["targets_captured"].config(text=str(len(snapshot.captured_targets)))
        self.stat_labels["targets_protected"].config(text=str(len(snapshot.protected_targets)))
        self.stat_labels["targets_empty"].config(text=str(len(snapshot.empty_targets)))

        sr = calc.success_rate()
        self.stat_labels["success_rate"].config(
            text=f"{sr*100:.1f}%" if sr is not None else "—")

        at = calc.average_attacker_time()
        self.stat_labels["avg_attacker_time"].config(
            text=f"{at:.1f}" if at is not None else "—")

        dt = calc.average_defender_time()
        self.stat_labels["avg_defender_time"].config(
            text=f"{dt:.1f}" if dt is not None else "—")