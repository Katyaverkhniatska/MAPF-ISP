"""
Area Protection System - Complete Implementation
Based on "Area Protection in Adversarial Path-Finding Scenarios"
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk
from collections import deque
import heapq
from typing import List, Tuple, Optional, Set, Dict, TypeAlias
from enum import Enum
import random

# Type aliases for better readability
Position: TypeAlias = Tuple[int, int]
Path: TypeAlias = List[Position]


class CellType(Enum):
    """Grid cell types"""
    EMPTY = 0
    OBSTACLE = 1
    ATTACKER_START = 2
    DEFENDER_START = 3
    TARGET = 4


class Agent:
    """Base class for agents (attackers and defenders)"""
    def __init__(self, agent_id: int, position: Position, team: str):
        self.id = agent_id
        self.position = position
        self.team = team  # 'attacker' or 'defender'
        self.target: Optional[Position] = None
        self.reached_target = False
        
    def set_target(self, target: Position):
        """Assign a target position to this agent"""
        self.target = target
        
    def move(self, new_position: Position):
        """Move agent to a new position"""
        self.position = new_position
            
    def is_at_target(self) -> bool:
        """Check if agent has reached its target"""
        return self.position == self.target


class Grid:
    """Grid environment for area protection"""
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.grid = np.zeros((height, width), dtype=int)
        self.obstacles = set()
        
    def add_obstacle(self, x: int, y: int):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y, x] = CellType.OBSTACLE.value
            self.obstacles.add((x, y))
            
    def remove_obstacle(self, x: int, y: int):
        if (x, y) in self.obstacles:
            self.grid[y, x] = CellType.EMPTY.value
            self.obstacles.remove((x, y))
            
    def is_valid(self, x: int, y: int) -> bool:
        """Check if position is valid and not an obstacle"""
        return (0 <= x < self.width and 
                0 <= y < self.height and 
                (x, y) not in self.obstacles)
    
    def get_neighbors(self, x: int, y: int) -> List[Position]:
        """Get valid 4-connected neighbors"""
        neighbors = []
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if self.is_valid(nx, ny):
                neighbors.append((nx, ny))
        return neighbors


class PathFinder:
    """A* pathfinding implementation"""
    
    @staticmethod
    def heuristic(a: Position, b: Position) -> float:
        """Manhattan distance heuristic"""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    
    @staticmethod
    def find_path(grid: Grid, start: Position, goal: Position, 
                  occupied: Set[Position] = None) -> Path:
        """A* pathfinding that avoids occupied cells"""
        if occupied is None:
            occupied = set()
            
        if start == goal:
            return [start]
        
        # Priority queue: (f_score, counter, position, path)
        counter = 0
        frontier = [(0, counter, start, [start])]
        visited = {start}
        
        while frontier:
            _, _, current, path = heapq.heappop(frontier)
            
            if current == goal:
                return path
            
            for neighbor in grid.get_neighbors(current[0], current[1]):
                if neighbor not in visited and neighbor not in occupied:
                    visited.add(neighbor)
                    new_path = path + [neighbor]
                    g_score = len(new_path) - 1
                    h_score = PathFinder.heuristic(neighbor, goal)
                    f_score = g_score + h_score
                    counter += 1
                    heapq.heappush(frontier, (f_score, counter, neighbor, new_path))
        
        return []  # No path found


class AllocationStrategy:
    """Base class for target allocation strategies"""
    
    @staticmethod
    def allocate(grid: Grid, defenders: List[Agent], targets: List[Position], 
                 attackers: List[Agent] = None) -> Dict[int, Position]:
        """Allocate targets to defenders. Returns dict {defender_id: target}"""
        raise NotImplementedError


class RandomAllocation(AllocationStrategy):
    """Random target allocation strategy"""
    
    @staticmethod
    def allocate(grid: Grid, defenders: List[Agent], targets: List[Position], 
                 attackers: List[Agent] = None) -> Dict[int, Position]:
        allocation = {}
        available_targets = targets.copy()
        random.shuffle(available_targets)
        
        for i, defender in enumerate(defenders):
            if i < len(available_targets):
                allocation[defender.id] = available_targets[i]
        
        return allocation


class GreedyAllocation(AllocationStrategy):
    """Greedy allocation - assign defenders to closest targets"""
    
    @staticmethod
    def allocate(grid: Grid, defenders: List[Agent], targets: List[Position], 
                 attackers: List[Agent] = None) -> Dict[int, Position]:
        allocation = {}
        available_targets = targets.copy()
        
        for defender in defenders:
            if not available_targets:
                break
                
            # Find closest target
            min_dist = float('inf')
            closest_target = None
            
            for target in available_targets:
                dist = abs(defender.position[0] - target[0]) + abs(defender.position[1] - target[1])
                if dist < min_dist:
                    min_dist = dist
                    closest_target = target
            
            if closest_target:
                allocation[defender.id] = closest_target
                available_targets.remove(closest_target)
        
        return allocation

#TODO: Find a bug -- the algorithm seems to find the bottleneck positions correctly, but attackers still win by finding the second best paths.
class BottleneckAllocation(AllocationStrategy):
    """Bottleneck simulation allocation strategy
    
    Implements iterative bottleneck detection from the paper:
    1. Simulate attacker paths
    2. Find most frequent positions (bottleneck)
    3. Mark as forbidden (simulating defender blocking it)
    4. Re-simulate paths avoiding forbidden positions
    5. Find next bottleneck
    6. Repeat until all defenders allocated
    
    This prevents attackers from simply routing around defenders.
    """
    
    @staticmethod
    def allocate(grid: Grid, defenders: List[Agent], targets: List[Position], 
                 attackers: List[Agent] = None, debug: bool = False) -> Dict[int, Position]:
        if not attackers:
            return RandomAllocation.allocate(grid, defenders, targets)
        
        allocation = {}
        forbidden_positions: Set[Position] = set()
        allocated_defenders = 0
        iteration = 0

        # Assign each attacker to a target (1-to-1 mapping)
        attacker_targets = {}
        for i, attacker in enumerate(attackers):
            if i < len(targets):
                attacker_targets[attacker.id] = targets[i]

        if debug:
            print(f"\nBottleneck Detection (Iterative)")
            print(f"Attackers: {len(attackers)}, Defenders: {len(defenders)}, Targets: {len(targets)}")
        
        # Iteratively find bottlenecks
        while allocated_defenders < len(defenders):
            iteration += 1
            
            # Simulate attacker paths with current forbidden positions
            path_frequency: Dict[Position, int] = {}
        
            for attacker in attackers:
                if attacker.id in attacker_targets:
                    target = attacker_targets[attacker.id]
                    # Find path avoiding forbidden positions
                    path = PathFinder.find_path(grid, attacker.position, target, 
                                               forbidden_positions)
                    
                    if path:
                        # Count frequency of each position in path
                        # Skip start and end positions
                        for pos in path[1:-1]:
                            path_frequency[pos] = path_frequency.get(pos, 0) + 1
            
            if not path_frequency:
                # No more bottlenecks found, assign remaining defenders to targets
                if debug:
                    print(f"  Iteration {iteration}: No more bottlenecks, assigning to targets")
                
                remaining_defenders = [d for d in defenders if d.id not in allocation]
                remaining_targets = [t for t in targets if t not in allocation.values()]
                
                for defender in remaining_defenders:
                    if remaining_targets:
                        closest_target = min(remaining_targets, 
                                            key=lambda t: abs(defender.position[0] - t[0]) + 
                                                        abs(defender.position[1] - t[1]))
                        allocation[defender.id] = closest_target
                        remaining_targets.remove(closest_target)
                break
            
            # Find position with highest frequency (bottleneck)
            bottleneck_pos = max(path_frequency.items(), key=lambda x: x[1])[0]
            frequency = path_frequency[bottleneck_pos]
            
            if debug:
                print(f"  Iteration {iteration}: Found bottleneck at {bottleneck_pos} "
                      f"(frequency: {frequency})")
            
            # Check if this bottleneck is actually valuable
            # (affects at least 2 attackers and has high frequency)
            if frequency >= 2:
                # Assign next available defender to this bottleneck
                for defender in defenders:
                    if defender.id not in allocation:
                        allocation[defender.id] = bottleneck_pos
                        allocated_defenders += 1
                        # Mark as forbidden for next iteration
                        forbidden_positions.add(bottleneck_pos)
                        
                        if debug:
                            print(f"    -> Defender {defender.id} assigned to {bottleneck_pos}")
                        break
            else:
                # Low-value bottleneck, assign remaining defenders to targets
                if debug:
                    print(f"  Iteration {iteration}: Bottleneck has low value (freq={frequency}), "
                          f"assigning remaining to targets")
                
                remaining_defenders = [d for d in defenders if d.id not in allocation]
                remaining_targets = [t for t in targets if t not in allocation.values()]
                
                for defender in remaining_defenders:
                    if remaining_targets:
                        closest_target = min(remaining_targets, 
                                            key=lambda t: abs(defender.position[0] - t[0]) + 
                                                        abs(defender.position[1] - t[1]))
                        allocation[defender.id] = closest_target
                        remaining_targets.remove(closest_target)
                break
        
        if debug:
            print(f"✓ Allocation complete: {len(allocation)} defenders assigned\n")
        
        return allocation


class Simulation:
    """Main simulation engine"""
    
    def __init__(self, grid: Grid):
        self.grid = grid
        self.attackers: List[Agent] = []
        self.defenders: List[Agent] = []
        self.targets: List[Position] = []
        self.time_step = 0
        self.max_steps = 150
        self.strategy = GreedyAllocation()
        self.running = False
        
    def add_attacker(self, position: Position) -> Agent:
        agent = Agent(len(self.attackers), position, 'attacker')
        self.attackers.append(agent)
        return agent
    
    def add_defender(self, position: Position) -> Agent:
        agent = Agent(len(self.defenders), position, 'defender')
        self.defenders.append(agent)
        return agent
    
    def add_target(self, position: Position):
        self.targets.append(position)
        
    def set_strategy(self, strategy: AllocationStrategy):
        self.strategy = strategy
        
    def initialize(self):
        """Initialize simulation - assign targets"""
        # Assign each attacker to a unique target
        for i, attacker in enumerate(self.attackers):
            if i < len(self.targets):
                attacker.set_target(self.targets[i])
        
        # Allocate defenders using selected strategy
        allocation = self.strategy.allocate(self.grid, self.defenders, 
                                           self.targets, self.attackers)
        
        for defender in self.defenders:
            if defender.id in allocation:
                defender.set_target(allocation[defender.id])
        
        self.time_step = 0
        self.initial_positions_attackers = {a.id: a.position for a in self.attackers}
        self.initial_positions_defenders = {d.id: d.position for d in self.defenders}
        
    def get_occupied_positions(self) -> Set[Position]:
        """Get all positions currently occupied by agents"""
        occupied = set()
        for agent in self.attackers + self.defenders:
            occupied.add(agent.position)
        return occupied
    
    def step(self) -> bool:
        """Execute one time step. Returns True if simulation should continue"""
        if self.time_step >= self.max_steps:
            return False
        
        occupied = self.get_occupied_positions()

        # Move defenders
        for defender in self.defenders:
            if not defender.reached_target and defender.target:
                occupied_others = occupied - {defender.position}
                path = PathFinder.find_path(self.grid, defender.position, 
                                           defender.target, occupied_others)
                
                if len(path) > 1:
                    next_pos = path[1]
                    if next_pos not in occupied_others:
                        occupied.remove(defender.position)
                        defender.move(next_pos)
                        occupied.add(next_pos)
                        
                        if defender.is_at_target():
                            defender.reached_target = True
        
        # Move attackers
        for attacker in self.attackers:
            if not attacker.reached_target and attacker.target:
                # Find path avoiding current occupied positions (excluding self)
                occupied_others = occupied - {attacker.position}
                path = PathFinder.find_path(self.grid, attacker.position, 
                                           attacker.target, occupied_others)
                
                if len(path) > 1:
                    next_pos = path[1]
                    # Check if position will be free
                    if next_pos not in occupied_others:
                        occupied.remove(attacker.position)
                        attacker.move(next_pos)
                        occupied.add(next_pos)
                        
                        if attacker.is_at_target():
                            attacker.reached_target = True
        
        self.time_step += 1
        return True
    
    def get_statistics(self) -> Dict:
        """Get current simulation statistics
        
        CRITICAL: Count based on TARGET states, not agent states!
        - A target is CAPTURED if an attacker occupies it
        - A target is PROTECTED if a defender occupies it
        - A target can be CONTESTED if both are nearby (not implemented)
        - A target can be EMPTY if neither occupies it
        """
        # Get agent positions for quick lookup
        attacker_positions = {a.position for a in self.attackers}
        defender_positions = {d.position for d in self.defenders}
        
        # Count targets by state
        targets_captured = 0
        targets_protected = 0
        targets_empty = 0
        
        for target in self.targets:
            if target in attacker_positions:
                targets_captured += 1
            elif target in defender_positions:
                targets_protected += 1
            else:
                targets_empty += 1
        
        # Additional useful stats
        attackers_at_their_target = sum(1 for a in self.attackers if a.reached_target)
        defenders_at_their_target = sum(1 for d in self.defenders if d.reached_target)
        
        return {
            'time_step': self.time_step,
            'targets_captured': targets_captured,        # Attackers occupying targets
            'targets_protected': targets_protected,      # Defenders occupying targets
            'targets_empty': targets_empty,              # No one on target
            'total_targets': len(self.targets),
            'total_attackers': len(self.attackers),
            'total_defenders': len(self.defenders),
            'attackers_reached_goal': attackers_at_their_target,  # For debugging
            'defenders_reached_goal': defenders_at_their_target,  # For debugging
        }
    
    def reset(self):
        """Reset simulation to initial state"""
        self.attackers.clear()
        self.defenders.clear()
        self.targets.clear()
        self.time_step = 0
        self.running = False


if __name__ == "__main__":
    """
    Quick test mode - run this file directly to test core logic without GUI
    Usage: python area_protection_system.py
    """
    print("=" * 60)
    print("AREA PROTECTION SYSTEM - Quick Test")
    print("=" * 60)
    
    # Create scenario
    grid = Grid(20, 20)
    sim = Simulation(grid)
    
    # Add a vertical wall with a gap (bottleneck)
    print("\nSetting up test scenario...")
    for i in range(5, 15):
        if i != 10:  # Leave gap at row 10
            grid.add_obstacle(10, i)
    
    # Add attackers on left side
    sim.add_attacker((5, 5))
    sim.add_attacker((5, 15))
    print(f"  Attackers: 2")
    
    # Add defender in the middle (at the gap)
    sim.add_defender((15, 10))
    print(f"  Defenders: 1")
    
    # Add target on right side
    sim.add_target((18, 10))
    print(f"  Targets: 1")
    
    # Initialize with greedy strategy
    print(f"\nInitializing simulation with Greedy strategy...")
    sim.set_strategy(GreedyAllocation())
    sim.initialize()
    
    # Run simulation
    print(f"\nRunning simulation:\n")
    print(f"{'Step':<6} {'Captured':<10} {'Protected':<10} {'Empty':<10}")
    print("-" * 40)
    
    for _ in range(30):
        sim.step()
        stats = sim.get_statistics()
        print(f"{stats['time_step']:<6} {stats['targets_captured']:<10} "
              f"{stats['targets_protected']:<10} {stats['targets_empty']:<10}")
        
        # Stop if all agents reached their goals
        if stats['targets_captured'] + stats['targets_protected'] == stats['total_targets']:
            break
    
    # Final results
    print("\n" + "=" * 60)
    print("FINAL RESULTS:")
    final_stats = sim.get_statistics()
    print(f"  Time steps: {final_stats['time_step']}")
    print(f"  Targets captured: {final_stats['targets_captured']}")
    print(f"  Targets protected: {final_stats['targets_protected']}")
    print(f"  Targets empty: {final_stats['targets_empty']}")
    
    success_rate = (final_stats['targets_protected'] / final_stats['total_targets']) * 100
    print(f"  Defense success rate: {success_rate:.1f}%")
    print("=" * 60)
    
    # Verify statistics are consistent
    total = (final_stats['targets_captured'] + 
             final_stats['targets_protected'] + 
             final_stats['targets_empty'])
    assert total == final_stats['total_targets'], "Statistics error!"
    print("✓ Statistics verified - all numbers add up correctly!")
