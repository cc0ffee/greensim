import time

# Really basic for testing

def run_simulation(params):
    print("Running simulation...")
    time.sleep(1)
    return {"status": "finished", "params": params}

if __name__ == "__main__":
    params = {"thermal_mass": 1200, "area": 100}
    result = run_simulation(params)
    print("Simulation result:", result)