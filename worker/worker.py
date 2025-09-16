import argparse
import json
import pandas as pd
from simulation.model import simulate_greenhouse
from simulation.weather import get_weather

def run_from_config(config_path: str):
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

def run_from_redis():
        r = redis.Redis(host="redis", port=6379, db=0)
    print("Worker listening on Redis queue...")

    while True:
        _, job = r.blpop("simulation_jobs")
        params = json.loads(job)

        start_date = params.get("start_date") or datetime.utcnow().strftime("%Y-%m-%d")
        end_date = params.get("end_date") or (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")

        location = {
            "lat": params.get("lat", 39.9),
            "lon": params.get("lon", 116.4),
        }

        weather_df = get_weather(location, start_date, end_date)
        results = simulate_greenhouse(weather_df, params)

        result_json = results.to_dict(orient="records")

        r.rpush("simulation_results", json.dumps({
            "params": params,
            "results": result_json
        }))

        print("Job complete:", params)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Run once with a config JSON")
    parser.add_argument("--redis", action="store_true", help="Run as a Redis worker")
    args = parser.parse_args()
    if args.config:
        run_from_config(args.config)
    elif args.redis:
        run_from_redis()
    else:
        print("Please provide either --config <file> or --redis")