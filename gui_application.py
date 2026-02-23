"""
Area Protection System - Interactive GUI Application
Desktop application for setting up and visualizing area protection scenarios
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle, Circle
import numpy as np
from area_protection_system import (
    Grid, Simulation, Agent, RandomAllocation, 
    GreedyAllocation, BottleneckAllocation
)


class AreaProtectionGUI:
    """Main GUI application"""
    
    def __init__(self, master):
        self.master = master
        self.master.title("Area Protection System - Interactive Simulation")
        self.master.geometry("1400x800")
        
        # Initialize simulation components
        self.grid_width = 30
        self.grid_height = 30
        self.grid = Grid(self.grid_width, self.grid_height)
        self.simulation = Simulation(self.grid)
        
        # GUI state
        self.mode = tk.StringVar(value="obstacle")  # obstacle, attacker, defender, target
        self.is_running = False
        self.animation_speed = 200  # ms
        
        # Create UI
        self.create_ui()
        self.draw_grid()
        
    def create_ui(self):
        """Create the user interface"""
        
        # Main container
        main_container = ttk.Frame(self.master)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Controls
        left_panel = ttk.Frame(main_container, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # Right panel - Visualization
        right_panel = ttk.Frame(main_container)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # === LEFT PANEL CONTROLS ===
        
        # Title
        ttk.Label(left_panel, text="Area Protection System", 
                 font=("Arial", 14, "bold")).pack(pady=10)
        
        # Mode Selection
        mode_frame = ttk.LabelFrame(left_panel, text="Editing Mode", padding=10)
        mode_frame.pack(fill=tk.X, pady=5)
        
        ttk.Radiobutton(mode_frame, text="🧱 Place Obstacles", 
                       variable=self.mode, value="obstacle").pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="🔴 Place Attackers", 
                       variable=self.mode, value="attacker").pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="🔵 Place Defenders", 
                       variable=self.mode, value="defender").pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="🎯 Place Targets", 
                       variable=self.mode, value="target").pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="🗑️ Erase", 
                       variable=self.mode, value="erase").pack(anchor=tk.W)
        
        # Strategy Selection
        strategy_frame = ttk.LabelFrame(left_panel, text="Defense Strategy", padding=10)
        strategy_frame.pack(fill=tk.X, pady=5)
        
        self.strategy_var = tk.StringVar(value="greedy")
        ttk.Radiobutton(strategy_frame, text="Random Allocation", 
                       variable=self.strategy_var, value="random").pack(anchor=tk.W)
        ttk.Radiobutton(strategy_frame, text="Greedy Allocation", 
                       variable=self.strategy_var, value="greedy").pack(anchor=tk.W)
        ttk.Radiobutton(strategy_frame, text="Bottleneck Simulation", 
                       variable=self.strategy_var, value="bottleneck").pack(anchor=tk.W)
        
        # Simulation Controls
        sim_frame = ttk.LabelFrame(left_panel, text="Simulation Controls", padding=10)
        sim_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(sim_frame, text="▶️ Start Simulation", 
                  command=self.start_simulation).pack(fill=tk.X, pady=2)
        ttk.Button(sim_frame, text="⏸️ Pause", 
                  command=self.pause_simulation).pack(fill=tk.X, pady=2)
        ttk.Button(sim_frame, text="⏭️ Step Forward", 
                  command=self.step_simulation).pack(fill=tk.X, pady=2)
        ttk.Button(sim_frame, text="🔄 Reset Simulation", 
                  command=self.reset_simulation).pack(fill=tk.X, pady=2)
        ttk.Button(sim_frame, text="🗑️ Clear All", 
                  command=self.clear_all).pack(fill=tk.X, pady=2)
        
        # Speed Control
        speed_frame = ttk.Frame(sim_frame)
        speed_frame.pack(fill=tk.X, pady=5)
        ttk.Label(speed_frame, text="Speed:").pack(side=tk.LEFT)
        speed_scale = ttk.Scale(speed_frame, from_=50, to=500, orient=tk.HORIZONTAL,
                               command=lambda v: setattr(self, 'animation_speed', int(float(v))))
        speed_scale.set(200)
        speed_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Statistics Display
        stats_frame = ttk.LabelFrame(left_panel, text="Statistics", padding=10)
        stats_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.stats_text = tk.Text(stats_frame, height=15, width=35, state='disabled')
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        # === RIGHT PANEL - VISUALIZATION ===
        
        # Create matplotlib figure
        self.fig, self.ax = plt.subplots(figsize=(10, 10))
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_panel)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Connect mouse events
        self.canvas.mpl_connect('button_press_event', self.on_canvas_click)
        
    def draw_grid(self):
        """Draw the grid and all elements"""
        self.ax.clear()
        self.ax.set_xlim(-0.5, self.grid_width - 0.5)
        self.ax.set_ylim(-0.5, self.grid_height - 0.5)
        self.ax.set_aspect('equal')
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xticks(range(self.grid_width))
        self.ax.set_yticks(range(self.grid_height))
        
        # Draw obstacles
        for x, y in self.grid.obstacles:
            rect = Rectangle((x-0.4, y-0.4), 0.8, 0.8, 
                           facecolor='black', edgecolor='black')
            self.ax.add_patch(rect)
        
        # Draw targets
        for x, y in self.simulation.targets:
            circle = Circle((x, y), 0.3, facecolor='gold', 
                          edgecolor='orange', linewidth=2, alpha=0.75)
            self.ax.add_patch(circle)
                    
        # Draw attackers
        for attacker in self.simulation.attackers:
            x, y = attacker.position
            circle = Circle((x, y), 0.35, facecolor='red', 
                          edgecolor='darkred', linewidth=2)
            self.ax.add_patch(circle)
            
            # Draw path if exists
            if attacker.target and not attacker.reached_target:
                tx, ty = attacker.target
                self.ax.plot([x, tx], [y, ty], 'r--', alpha=0.3, linewidth=1)
        
        # Draw defenders
        for defender in self.simulation.defenders:
            x, y = defender.position
            circle = Circle((x, y), 0.35, facecolor='blue', 
                          edgecolor='darkblue', linewidth=2)
            self.ax.add_patch(circle)
            
            # Draw path if exists
            if defender.target and not defender.reached_target:
                tx, ty = defender.target
                self.ax.plot([x, tx], [y, ty], 'b--', alpha=0.3, linewidth=1)
        
        # Add legend
        self.ax.plot([], [], 'ro', markersize=10, label=f'Attackers ({len(self.simulation.attackers)})')
        self.ax.plot([], [], 'bo', markersize=10, label=f'Defenders ({len(self.simulation.defenders)})')
        self.ax.plot([], [], 'o', color='gold', markersize=10, label=f'Targets ({len(self.simulation.targets)})')
        self.ax.plot([], [], 's', color='black', markersize=10, label='Obstacles')
        self.ax.legend(loc='upper left', bbox_to_anchor=(-0.4, 1.15), ncol=4, fontsize='small')
        self.canvas.draw()
        self.update_statistics()
        
    def on_canvas_click(self, event):
        """Handle canvas click events"""
        if event.inaxes != self.ax or self.is_running:
            return
        
        # Convert to grid coordinates
        x = int(round(event.xdata))
        y = int(round(event.ydata))
        
        if not (0 <= x < self.grid_width and 0 <= y < self.grid_height):
            return
        
        mode = self.mode.get()
        
        if mode == "obstacle":
            if (x, y) not in self.grid.obstacles:
                self.grid.add_obstacle(x, y)
        
        elif mode == "attacker":
            # Check if position is free
            if self.is_position_free(x, y):
                self.simulation.add_attacker((x, y))
        
        elif mode == "defender":
            if self.is_position_free(x, y):
                self.simulation.add_defender((x, y))
        
        elif mode == "target":
            if self.is_position_free(x, y):
                self.simulation.add_target((x, y))
        
        elif mode == "erase":
            # Remove whatever is at this position
            self.grid.remove_obstacle(x, y)
            
            # Remove agents
            self.simulation.attackers = [a for a in self.simulation.attackers 
                                        if a.position != (x, y)]
            self.simulation.defenders = [d for d in self.simulation.defenders 
                                        if d.position != (x, y)]
            # Remove targets
            if (x, y) in self.simulation.targets:
                self.simulation.targets.remove((x, y))
        
        self.draw_grid()
    
    def is_position_free(self, x, y):
        """Check if position is free for placing agents/targets"""
        if (x, y) in self.grid.obstacles:
            return False
        
        for agent in self.simulation.attackers + self.simulation.defenders:
            if agent.position == (x, y):
                return False
        
        return True
    
    def start_simulation(self):
        """Start the simulation"""
        if len(self.simulation.attackers) == 0:
            messagebox.showwarning("No Attackers", "Please add at least one attacker!")
            return
        
        if len(self.simulation.targets) == 0:
            messagebox.showwarning("No Targets", "Please add at least one target!")
            return
        
        # Set strategy
        strategy_map = {
            'random': RandomAllocation(),
            'greedy': GreedyAllocation(),
            'bottleneck': BottleneckAllocation()
        }
        self.simulation.set_strategy(strategy_map[self.strategy_var.get()])
        
        # Initialize simulation
        self.simulation.initialize()
        self.is_running = True
        self.draw_grid()
        self.run_animation()
    
    def pause_simulation(self):
        """Pause the simulation"""
        self.is_running = False
    
    def step_simulation(self):
        """Execute one simulation step"""
        if self.simulation.time_step == 0:
            # Initialize if not started
            strategy_map = {
                'random': RandomAllocation(),
                'greedy': GreedyAllocation(),
                'bottleneck': BottleneckAllocation()
            }
            self.simulation.set_strategy(strategy_map[self.strategy_var.get()])
            self.simulation.initialize()
        
        self.simulation.step()
        self.draw_grid()
    
    def run_animation(self):
        """Run simulation animation"""
        if self.is_running:
            continue_sim = self.simulation.step()
            self.draw_grid()
            
            if continue_sim:
                self.master.after(self.animation_speed, self.run_animation)
            else:
                self.is_running = False
                stats = self.simulation.get_statistics()
                messagebox.showinfo("Simulation Complete", 
                                   f"Simulation finished!\n\n"
                                   f"Total targets: {stats['total_targets']}\n"
                                   f"Targets captured by attackers: {stats['targets_captured']}\n"
                                   f"Targets protected by defenders: {stats['targets_protected']}\n"
                                   f"Targets empty: {stats['targets_empty']}\n\n"
                                   f"Defense success rate: {(stats['targets_protected']/max(1, stats['total_targets'])*100):.1f}%")
    
    def reset_simulation(self):
        """Reset simulation to initial positions"""
        self.is_running = False
        
        # Store initial positions
        attacker_positions = self.simulation.initial_positions_attackers.values()
        defender_positions = self.simulation.initial_positions_defenders.values()
        targets = self.simulation.targets.copy()
        
        # Reset simulation
        self.simulation.attackers.clear()
        self.simulation.defenders.clear()
        self.simulation.targets.clear()
        self.simulation.time_step = 0
        
        # Recreate agents
        for pos in attacker_positions:
            self.simulation.add_attacker(pos)
        for pos in defender_positions:
            self.simulation.add_defender(pos)
        self.simulation.targets = targets
        
        self.draw_grid()
    
    def clear_all(self):
        """Clear everything"""
        self.is_running = False
        self.grid.obstacles.clear()
        self.grid.grid = np.zeros((self.grid_height, self.grid_width), dtype=int)
        self.simulation.reset()
        self.draw_grid()
    
    def update_statistics(self):
        """Update statistics display"""
        stats = self.simulation.get_statistics()
        
        # Calculate success rate
        if stats['total_targets'] > 0:
            success_rate = (stats['targets_protected'] / stats['total_targets']) * 100
        else:
            success_rate = 0.0
        
        stats_text = f"""
╔══════════════════════════════╗
║     SIMULATION STATISTICS    ║
╚══════════════════════════════╝

⏱️  Time Step: {stats['time_step']} / {self.simulation.max_steps}

🔴 ATTACKERS:
   Total: {stats['total_attackers']}
   Reached their goal: {stats['attackers_reached_goal']}
   
🔵 DEFENDERS:
   Total: {stats['total_defenders']}
   Reached their position: {stats['defenders_reached_goal']}

🎯 TARGET STATUS:
   Total: {stats['total_targets']}
   ❌ Captured (attacker on it): {stats['targets_captured']}
   ✅ Protected (defender on it): {stats['targets_protected']}
   ⚪ Empty (no one on it): {stats['targets_empty']}

📊 DEFENSE EFFECTIVENESS:
   Success Rate: {success_rate:.2f}%
   
🧠 Strategy: {self.strategy_var.get().title()}
        """
        
        self.stats_text.config(state='normal')
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, stats_text)
        self.stats_text.config(state='disabled')


def main():
    """Main entry point"""
    root = tk.Tk()
    _ = AreaProtectionGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
