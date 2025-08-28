import argparse
import json
import pandas as pd
from simulation.model import simulate_greenhouse
from simulation.weather import get_weather

def main(config_path: str):
    with open(config_path, "r") as f:
        config = json.load(f)

    location = config["location"]
    start_date = config["start_date"]
    end_date = config["end_date"]
    params = config["parameters"]

    weather_df = get_weather(location, start_date, end_date)

    results = simulate_greenhouse(weather_df, params)

    out_csv = f"results/{config['name']}_results.csv"
    results.to_csv(out_csv, index=False)
    print(f"Simulation complete. Results saved to {out_csv}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/default.json", help="Path to config file")
    args = parser.parse_args()
    main(args.config)