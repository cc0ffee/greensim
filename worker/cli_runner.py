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
    start_date = config.get("start_date", "2025-11-01")
    end_date = config.get("end_date", "2025-11-02")
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
    out_csv = f"results/{config.get('name', 'test_run')}_results.csv"
    result_df.to_csv(out_csv, index=False)
    print(f"Results saved to {out_csv}")

    # --- Load reference data for comparison ---
    reference_df = None
    try:
        import os
        ref_path = os.path.join(os.path.dirname(__file__), 'data', 'reference_greenhouse_temps.csv')
        if os.path.exists(ref_path):
            reference_df = pd.read_csv(ref_path)
            reference_df['datetime'] = pd.to_datetime(reference_df['datetime'])
            # Filter to matching date range
            reference_df = reference_df[
                (reference_df['datetime'] >= pd.to_datetime(start_date)) &
                (reference_df['datetime'] <= pd.to_datetime(end_date))
            ]
            if len(reference_df) > 0:
                print(f"Loaded {len(reference_df)} reference data points for comparison")
    except Exception as e:
        print(f"Could not load reference data: {e}")

    # --- Plot internal temperatures ---
    plt.figure(figsize=(14,7))
    
    # Plot temperature lines
    plt.plot(result_df['datetime'], result_df['Tin'], label='Simulated Air (Tin)', color='tab:red', linewidth=2, alpha=0.8)
    plt.plot(result_df['datetime'], result_df['T_mass'], label='Thermal Mass (T_mass)', color='tab:orange', linewidth=1.5, alpha=0.6)
    plt.plot(result_df['datetime'], result_df['Tout'], label='External (Tout)', color='tab:green', linewidth=1.5, alpha=0.6)
    
    # Plot reference data if available
    if reference_df is not None and len(reference_df) > 0:
        plt.plot(reference_df['datetime'], reference_df['Tin_typical'], 
                label='Reference Typical', color='tab:purple', linewidth=2, 
                linestyle=':', marker='o', markersize=4, alpha=0.7)
        # Show min/max range
        plt.fill_between(reference_df['datetime'], 
                        reference_df['Tin_min'], 
                        reference_df['Tin_max'],
                        alpha=0.15, 
                        color='tab:purple',
                        label='Reference Range (min-max)')
    
    # Add threshold line if setpoint is defined
    setpoint = params.get('setpoint')
    if setpoint is not None:
        plt.axhline(y=setpoint, color='tab:blue', linestyle='--', linewidth=2, 
                   label=f'Threshold ({setpoint}°C)', alpha=0.7)
        
        # Fill area below threshold that needs heating
        # Only fill where Tin is below the setpoint
        below_threshold = result_df['Tin'] < setpoint
        if below_threshold.any():
            plt.fill_between(result_df['datetime'], 
                            result_df['Tin'], 
                            setpoint,
                            where=below_threshold,
                            alpha=0.3, 
                            color='tab:blue',
                            label='Heating Required')
    
    plt.xlabel("Datetime", fontsize=12)
    plt.ylabel("Temperature (°C)", fontsize=12)
    plt.title("Greenhouse Internal Temperatures - Simulation vs Reference", fontsize=14, fontweight='bold')
    plt.legend(loc='best', fontsize=9)
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('results/plot.png', dpi=150)
    print(f"Plot saved to results/plot.png")
    
    # --- Print comparison statistics if reference data available ---
    if reference_df is not None and len(reference_df) > 0:
        # Merge on datetime for comparison
        comparison = pd.merge(
            result_df[['datetime', 'Tin']].rename(columns={'Tin': 'Tin_sim'}), 
            reference_df[['datetime', 'Tin_typical']], 
            on='datetime', 
            how='inner'
        )
        if len(comparison) > 0:
            diff = comparison['Tin_sim'] - comparison['Tin_typical']
            mae = diff.abs().mean()
            rmse = (diff ** 2).mean() ** 0.5
            print(f"\n--- Comparison with Reference Data ---")
            print(f"Mean Absolute Error (MAE): {mae:.2f}°C")
            print(f"Root Mean Square Error (RMSE): {rmse:.2f}°C")
            print(f"Mean Temperature Difference: {diff.mean():.2f}°C")
            print(f"Simulated Range: {comparison['Tin_sim'].min():.1f}–{comparison['Tin_sim'].max():.1f}°C")
            print(f"Reference Range: {comparison['Tin_typical'].min():.1f}–{comparison['Tin_typical'].max():.1f}°C")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run greenhouse simulation offline (no Redis)")
    parser.add_argument("--config", default="configs/default.json", help="Path to JSON config file")
    args = parser.parse_args()

    run_simulation(args.config)
