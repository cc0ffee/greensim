import argparse
import json
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from simulation.model import simulate_greenhouse
from simulation.weather import get_weather

def run_simulation(config_path: str):
    # Load config
    with open(config_path, "r") as f:
        config = json.load(f)

    location = config.get("location", {"lat": 39.9, "lon": 116.4})
    start_date = config.get("start_date", "2025-10-01")
    end_date = config.get("end_date", "2025-10-02")
    params = config.get("parameters", {})

    print(f"[{datetime.now().isoformat()}] Running local simulation...")
    print(f"Location: {location}")
    print(f"Dates: {start_date} → {end_date}")

    # Get weather and run simulation
    weather_df = get_weather(location, start_date, end_date)
    result_df = simulate_greenhouse(weather_df, params)

    print(f"Simulation complete — {len(result_df)} hours simulated.")
    print(f"Internal T range: {result_df['Tin'].min():.2f}–{result_df['Tin'].max():.2f} °C")

    # Save CSV
    out_csv = f"worker/results/{config.get('name', 'test_run')}_results.csv"
    result_df.to_csv(out_csv, index=False)
    print(f"Results saved to {out_csv}")

    # --- Plot internal temperatures ---
    plt.figure(figsize=(12,6))
    plt.plot(result_df['datetime'], result_df['Tin'], label='Air (Tin)', color='tab:red')
    plt.plot(result_df['datetime'], result_df['T_mass'], label='Thermal Mass (T_mass)', color='tab:orange')
    plt.plot(result_df['datetime'], result_df['Tout'], label='Air (Tout)', color='tab:green')
    plt.xlabel("Datetime")
    plt.ylabel("Temperature (°C)")
    plt.title("Greenhouse Internal Temperatures")
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run greenhouse simulation offline (no Redis)")
    parser.add_argument("--config", default="configs/default.json", help="Path to JSON config file")
    args = parser.parse_args()

    run_simulation(args.config)
