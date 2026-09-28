import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional, Tuple

from simulation_engine.batch_aggregator import BatchSummary, StrategySummary


# ----------------------------------------------------------------------
# Row definitions: (metric_key, display_label), in display order.
# ----------------------------------------------------------------------
METRIC_ROWS: List[Tuple[str, str]] = [
    ("success_rate", "Success Rate"),
    ("targets_protected", "Targets Protected (mean)"),
    ("targets_captured", "Targets Captured (mean)"),
    ("avg_attacker_time", "Avg Attacker Time"),
    ("avg_defender_time", "Avg Defender Time"),
    ("defender_efficiency", "Defender Efficiency"),
    ("total_steps", "Total Steps (mean)"),
    ("win_count", "Wins"),
    ("runs_completed", "Runs Completed"),
    ("runs_failed", "Runs Failed"),
]

# Metrics with a clear "better" direction, used for marking the best cell
# in a row. Metrics left out (attacker/defender time, total steps, run
# counts) are informational only -- e.g. a higher average attacker time
# could mean defenders delayed attackers more, or could just mean slower
# pathing; there's no unambiguous "better" direction to mark.
_RAW_VALUE = {
    "success_rate":        lambda s: s.success_rate_mean,
    "targets_protected":   lambda s: s.targets_protected_mean,
    "targets_captured":    lambda s: s.targets_captured_mean,
    "defender_efficiency": lambda s: s.defender_efficiency_mean,
    "win_count":           lambda s: s.win_count,
}
_HIGHER_IS_BETTER = {
    "success_rate": True,
    "targets_protected": True,
    "targets_captured": False,   # fewer captured targets is better defense
    "defender_efficiency": True,
    "win_count": True,
}


def best_strategy_for_metric(metric_key: str, summary: BatchSummary) -> List[str]:
    """
    Names of the strategy/strategies with the best value for this metric.
    Ties return every tied strategy. Metrics with no defined direction
    (see _RAW_VALUE above) return an empty list -- callers should treat
    that as "don't mark anything for this row".
    """
    if metric_key not in _RAW_VALUE or not summary.strategies:
        return []
    getter = _RAW_VALUE[metric_key]
    higher_is_better = _HIGHER_IS_BETTER[metric_key]
    values: Dict[str, float] = {name: getter(s) for name, s in summary.strategies.items()}
    best_val = max(values.values()) if higher_is_better else min(values.values())
    return [name for name, v in values.items() if v == best_val]


def format_cell(metric_key: str, summary: StrategySummary,
                 iterations_used_for_win_count: int, is_best: bool = False) -> str:
    """Renders one (metric, strategy) cell as display text."""
    if metric_key == "success_rate":
        text = f"{summary.success_rate_mean * 100:.1f}% (±{summary.success_rate_std * 100:.1f})"
    elif metric_key == "targets_protected":
        text = f"{summary.targets_protected_mean:.2f}"
    elif metric_key == "targets_captured":
        text = f"{summary.targets_captured_mean:.2f}"
    elif metric_key == "avg_attacker_time":
        text = ("—" if summary.avg_attacker_time_mean is None else
                f"{summary.avg_attacker_time_mean:.1f} "
                f"({summary.avg_attacker_time_count}/{summary.runs_completed})")
    elif metric_key == "avg_defender_time":
        text = ("—" if summary.avg_defender_time_mean is None else
                f"{summary.avg_defender_time_mean:.1f} "
                f"({summary.avg_defender_time_count}/{summary.runs_completed})")
    elif metric_key == "defender_efficiency":
        text = f"{summary.defender_efficiency_mean:.2f}"
    elif metric_key == "total_steps":
        text = f"{summary.total_steps_mean:.1f}"
    elif metric_key == "win_count":
        text = f"{summary.win_count} / {iterations_used_for_win_count}"
    elif metric_key == "runs_completed":
        text = str(summary.runs_completed)
    elif metric_key == "runs_failed":
        text = str(summary.runs_failed)
    else:
        raise ValueError(f"Unknown metric key: {metric_key}")

    return f"\u2605 {text}" if is_best else text  # \u2605 = ★


def format_header(summary: BatchSummary, template_label: str = "",
                   seed: Optional[int] = None) -> str:
    """Multi-line header text shown above the table."""
    lines = []
    if template_label:
        lines.append(f"Template: {template_label}")
    lines.append(
        f"Iterations requested: {summary.requested_iterations}, "
        f"completed: {summary.iterations_completed}"
    )
    if summary.generation_failures:
        lines.append(f"Layout-generation failures (skipped): {summary.generation_failures}")
    lines.append(f"Iterations used for win comparison: {summary.iterations_used_for_win_count}")
    if seed is not None:
        lines.append(f"Seed: {seed}")
    return "\n".join(lines)


def build_rows(summary: BatchSummary) -> List[List[str]]:
    """
    Builds every row's cell values (metric label + one formatted cell per
    strategy, with a star on the best cell) in METRIC_ROWS order. Exposed
    separately from the Treeview so the exact table content can be
    unit-tested without Tkinter.
    """
    strategy_names = list(summary.strategies.keys())
    rows: List[List[str]] = []
    for metric_key, label in METRIC_ROWS:
        best_names = set(best_strategy_for_metric(metric_key, summary))
        row = [label]
        for name in strategy_names:
            is_best = name in best_names
            row.append(format_cell(
                metric_key, summary.strategies[name],
                summary.iterations_used_for_win_count, is_best,
            ))
        rows.append(row)
    return rows


# ----------------------------------------------------------------------
# The actual widget. Thin by design -- see module docstring.
# ----------------------------------------------------------------------
class BatchResultsWindow(tk.Toplevel):
    """
    Pop-up comparison table: one column per strategy, one row per metric,
    with the best value in each (defined) row marked with a star.
    Both scrollbars are present since more strategies/metrics can exceed
    the visible area in either direction.
    """

    def __init__(self, parent, summary: BatchSummary,
                 template_label: str = "", seed: Optional[int] = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.title("Strategy Comparison Results")
        self.summary = summary

        header = ttk.Label(
            self, text=format_header(summary, template_label, seed),
            justify=tk.LEFT,
        )
        header.pack(anchor="w", padx=10, pady=(10, 4))

        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        strategy_names = list(summary.strategies.keys())
        columns = ["metric"] + strategy_names

        tree = ttk.Treeview(
            table_frame, columns=columns, show="headings",
            height=len(METRIC_ROWS),
        )
        tree.heading("metric", text="Metric")
        tree.column("metric", width=190, anchor="w", stretch=False)
        for name in strategy_names:
            tree.heading(name, text=name)
            tree.column(name, width=150, anchor="center", stretch=False)

        for row_values in build_rows(summary):
            tree.insert("", tk.END, values=row_values)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        ttk.Button(self, text="Close", command=self.destroy).pack(pady=(0, 10))