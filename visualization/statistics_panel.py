import tkinter as tk
from tkinter import ttk

from simulation_engine.step_snapshot import StepSnapshot
from simulation_engine.statistics_calculator import StatisticsCalculator

class StatisticsPanel(ttk.Frame):
    """Display real-time simulation statistics."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        stats_frame = ttk.LabelFrame(self, text="Statistics", padding=10)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create stat labels
        self.stat_labels = {}
        stats = [
            ("targets_captured", "Targets Captured:"),
            ("targets_protected", "Targets Protected:"),
            ("targets_empty", "Targets Empty:"),
            ("success_rate", "Success Rate:"),
            ("avg_attacker_time", "Avg Attacker Time:"),
            ("avg_defender_time", "Avg Defender Time:"),
        ]
        
        for key, label_text in stats:
            frame = ttk.Frame(stats_frame)
            frame.pack(fill=tk.X, pady=3)
            ttk.Label(frame, text=label_text, width=20).pack(side=tk.LEFT)
            self.stat_labels[key] = ttk.Label(
                frame, text="—", font=("Courier", 10)
            )
            self.stat_labels[key].pack(side=tk.LEFT)
    
    def update_stats(self, snapshot: StepSnapshot, calculator: StatisticsCalculator):
        """Update statistics display."""
        self.stat_labels["targets_captured"].config(
            text=str(len(snapshot.captured_targets))
        )
        self.stat_labels["targets_protected"].config(
            text=str(len(snapshot.protected_targets))
        )
        self.stat_labels["targets_empty"].config(
            text=str(len(snapshot.empty_targets))
        )
        
        success_rate = calculator.success_rate()
        self.stat_labels["success_rate"].config(
            text=f"{success_rate * 100:.1f}%" if success_rate is not None else "—"
        )
        
        avg_att_time = calculator.average_attacker_time()
        self.stat_labels["avg_attacker_time"].config(
            text=f"{avg_att_time:.1f}" if avg_att_time is not None else "—"
        )
        
        avg_def_time = calculator.average_defender_time()
        self.stat_labels["avg_defender_time"].config(
            text=f"{avg_def_time:.1f}" if avg_def_time is not None else "—"
        )