"""
Demo Script - Programmatic Testing without GUI
Shows how to run simulations programmatically and collect results
"""

from area_protection_system import (
    Grid, Simulation, RandomAllocation, 
    GreedyAllocation, BottleneckAllocation
)
import matplotlib.pyplot as plt
import numpy as np


def create_corridor_scenario():
    """Create a corridor/bottleneck scenario"""
    grid = Grid(30, 30)
    sim = Simulation(grid)
    
    # Create a corridor with obstacles
    for y in range(10, 20):
        if y != 15:  # Leave gap at y = 15
            grid.add_obstacle(15, y)
    
    # Add attackers on left
    for i in range(5):
        sim.add_attacker((5, 10 + i * 2))
    
    # Add defenders (fewer)
    sim.add_defender((15, 15))  # in the gap
    sim.add_defender((20, 15))
    
    # Add targets on right
    for i in range(5):
        sim.add_target((25, 10 + i * 2))
    
    return grid, sim


def create_rooms_scenario():
    """Create a scenario with rooms"""
    grid = Grid(30, 30)
    sim = Simulation(grid)
    
    # Create room walls
    # Vertical walls
    for y in range(5, 25):
        if y not in [10, 15, 20]:  # Doors
            grid.add_obstacle(10, y)
            grid.add_obstacle(20, y)
    
    # Horizontal walls
    for x in range(5, 25):
        if x not in [10, 15, 20]:
            grid.add_obstacle(x, 10)
            grid.add_obstacle(x, 20)
    
    # Add attackers (many)
    for i in range(10):
        x = 6 + (i % 3) * 1
        y = 6 + (i // 3) * 1
        sim.add_attacker((x, y))
    
    # Add defenders (fewer)
    sim.add_defender((15, 10))  # Door guard
    sim.add_defender((20, 15))
    sim.add_defender((15, 20))
    
    # Add targets in protected room
    for i in range(5):
        sim.add_target((22 + i % 2, 22 + i // 2))
    
    return grid, sim


def run_comparison():
    """Compare all three strategies on the same scenario"""
    print("=" * 60)
    print("STRATEGY COMPARISON - Corridor Scenario")
    print("=" * 60)
    
    strategies = {
        'Random': RandomAllocation(),
        'Greedy': GreedyAllocation(),
        'Bottleneck': BottleneckAllocation()
    }
    
    results = {}
    
    for name, strategy in strategies.items():
        # Create fresh scenario
        grid, sim = create_corridor_scenario()
        sim.set_strategy(strategy)

        print(f"\n{'='*60}")
        print(f"Testing: {name} Strategy")
        print('='*60)

        if name == 'Bottleneck':
            # Manually trigger allocation with debug
            sim.initialize()
            # Re-do allocation with debug=True to show what's happening
            allocation = BottleneckAllocation.allocate(
                sim.grid, sim.defenders, sim.targets, sim.attackers, debug=True
            )
        else:
            sim.initialize()
        
       # Run simulation
        step_count = 0
        while sim.step() and step_count < sim.max_steps:
            step_count += 1
        
        stats = sim.get_statistics()
        results[name] = stats
        
        print(f"\n{name} Strategy:")
        print(f"  Time steps: {stats['time_step']}")
        print(f"  Attackers at target: {stats['targets_captured']}/{stats['total_attackers']}")
        print(f"  Defenders at target: {stats['targets_protected']}/{stats['total_defenders']}")
        print(f"  Defense success rate: {(stats['targets_protected']/max(1, len(sim.targets)) * 100):.1f}%")

    print("\n" + "=" * 60)
    best_strategy = max(results.items(), key=lambda x: x[1]['targets_protected'])
    print(f"BEST DEFENSE: {best_strategy[0]} (protected {best_strategy[1]['targets_protected']} targets)")
    print("=" * 60)
    
    return results


def visualize_scenario(grid, sim, title="Scenario"):
    """Visualize a scenario state"""
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Draw grid
    ax.set_xlim(-0.5, grid.width - 0.5)
    ax.set_ylim(-0.5, grid.height - 0.5)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    # Draw obstacles
    for x, y in grid.obstacles:
        ax.add_patch(plt.Rectangle((x-0.4, y-0.4), 0.8, 0.8, 
                                   facecolor='black'))
    
    # Draw targets
    for x, y in sim.targets:
        ax.plot(x, y, 'o', color='gold', markersize=15, 
               markeredgecolor='orange', markeredgewidth=2)
    
    # Draw agents
    for attacker in sim.attackers:
        x, y = attacker.position
        color = 'red' if not attacker.reached_target else 'darkred'
        ax.plot(x, y, 'o', color=color, markersize=12)
    
    for defender in sim.defenders:
        x, y = defender.position
        color = 'blue' if not defender.reached_target else 'darkblue'
        ax.plot(x, y,  's', color=color, markersize=12)
    
    # Legend
    ax.plot([], [], 'ro', markersize=10, label='Attackers')
    ax.plot([], [], 'bs', markersize=10, label='Defenders')
    ax.plot([], [], 'o', color='gold', markersize=10, label='Targets')
    ax.legend()
    
    plt.tight_layout()
    return fig


def detailed_simulation_run():
    """Run a detailed simulation with step-by-step output"""
    print("\n" + "=" * 60)
    print("DETAILED SIMULATION - Bottleneck Strategy")
    print("=" * 60)
    
    grid, sim = create_corridor_scenario()
    sim.set_strategy(BottleneckAllocation())

    print(f"\nSetup:")
    print(f"  Attackers: {len(sim.attackers)}")
    print(f"  Defenders: {len(sim.defenders)}")
    print(f"  Targets: {len(sim.targets)}")
    print(f"  Strategy: Bottleneck Simulation")
    
    # Initialize with debug output
    print(f"\nInitializing...")
    allocation = BottleneckAllocation.allocate(
        sim.grid, sim.defenders, sim.targets, sim.attackers, debug=True
    )

    # Apply allocation
    for defender in sim.defenders:
        if defender.id in allocation:
            defender.set_target(allocation[defender.id])
    
    # Show initial allocations
    print(f"\nDefender Allocations:")
    for defender in sim.defenders:
        print(f"  Defender {defender.id}: { defender.position} → {defender.target}")
    
    # Run simulation with periodic updates
    print(f"\nRunning simulation...")
    print(f"{'Step':<6} {'Attackers at Target':<20} {'Defenders at Target':<20}")
    print("-" * 50)
    
    step = 0
    while sim.step():
        if step % 20 == 0:  # Print every 20 steps
            stats = sim.get_statistics()
            print(f"{step:<6} {stats['targets_captured']:<10} "
                  f"{stats['targets_protected']:<10} {stats['targets_empty']:<10}")
        step += 1
    
    # Final results
    final_stats = sim.get_statistics()
    print("-" * 50)
    print(f"\nFinal Results (Step {final_stats['time_step']}):")
    print(f"  Targets captured: {final_stats['targets_captured']}")
    print(f"  Targets protected: {final_stats['targets_protected']}")
    print(f"  Targets empty: {final_stats['targets_empty']}")
    print(f"  Success rate: {(final_stats['targets_protected']/len(sim.targets)) * 100:.1f}%")
    
    # Visualize final state
    _ = visualize_scenario(grid, sim, "Final State - Bottleneck Strategy")
    plt.show()


def test_different_ratios():
    """Test strategy performance with different attacker:defender ratios"""
    print("\n" + "=" * 60)
    print("RATIO TESTING - Greedy vs Bottleneck")
    print("=" * 60)
    
    ratios = [(5, 5), (10, 5), (20, 5), (30, 5)]
    
    for n_attackers, n_defenders in ratios:
        print(f"\n--- Ratio {n_attackers}:{n_defenders} ---")
        
        for strategy_name, strategy in [('Greedy',GreedyAllocation()), 
                                       ('Bottleneck', BottleneckAllocation())]:
            # Create scenario
            grid = Grid(30, 30)
            sim = Simulation(grid)
            
            # Add corridor
            for y in range(10, 20):
                if y != 15:
                    grid.add_obstacle(15, y)
            
            # Add agents
            for i in range(n_attackers):
                sim.add_attacker((5, 5 + i % 20))
            
            for i in range(n_defenders):
                sim.add_defender((20, 10 + i * 2))
            
            # Add targets
            for i in range(10):
                sim.add_target((25, 10 + i))
            
            # Run
            sim.set_strategy(strategy)
            sim.initialize()
            while sim.step():
                pass
            
            stats = sim.get_statistics()
            success = (1 - stats['targets_captured']/len(sim.targets)) * 100
            
            print(f"  {strategy_name:12} - Success: {success:5.1f}% "
                  f"(Protected: {stats['targets_protected']}, "
                  f"Captured: {stats['targets_captured']}, "
                  f"Empty: {stats['targets_empty']})")


if __name__ == "__main__":
    print("\n🎮 Area Protection System - Demo Script")
    print("This demonstrates programmatic usage without GUI\n")
    
    # Run different tests
    choice = input("Choose test:\n"
                   "1. Quick comparison of all strategies\n"
                   "2. Detailed step-by-step simulation\n"
                   "3. Test different attacker:defender ratios\n"
                   "4. Run all tests\n"
                   "Choice (1-4): ")
    
    if choice == "1":
        run_comparison()
    elif choice == "2":
        detailed_simulation_run()
    elif choice == "3":
        test_different_ratios()
    elif choice == "4":
        run_comparison()
        detailed_simulation_run()
        test_different_ratios()
    else:
        print("Invalid choice. Running quick comparison...")
        run_comparison()
    
    print("\n✅ Demo complete!")
