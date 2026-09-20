import sys
from visualization.simulation_window import SimulationWindow


if __name__ == "__main__":
    app = SimulationWindow()

    if "--headless" in sys.argv or "--smoke-test" in sys.argv:
        app.update()
        app.destroy()
        print("GUI smoke test passed.")
    else:
        app.mainloop()