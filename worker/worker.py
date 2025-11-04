import json
import time
import traceback
import pandas as pd
import numpy as np
import redis
from datetime import datetime, timezone
from simulation.model import simulate_greenhouse
from simulation.weather import get_weather
import os

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_ADDR = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

rdb = redis.from_url(REDIS_ADDR, decode_responses=True)
print(f"[{datetime.now(timezone.utc).isoformat()}] Connected to Redis at {REDIS_ADDR}")

RESULT_TTL = int(os.getenv("RESULT_TTL", 86400))  # 24h
QUEUE_NAME = "simulation_jobs"
META_PREFIX = "job_meta:"
RESULT_PREFIX = "job_result:"

def connect_redis():
    return redis.from_url(REDIS_ADDR, decode_responses=True)

def log(msg: str):
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)

def update_job_status(rdb, job_id: str, status: str, error: str = None):
    meta_key = f"{META_PREFIX}{job_id}"
    meta = rdb.get(meta_key)
    if not meta:
        return
    meta_obj = json.loads(meta)
    meta_obj["status"] = status
    meta_obj["updated_at"] = datetime.now(timezone.utc).isoformat()
    if error:
        meta_obj["error"] = error
    rdb.set(meta_key, json.dumps(meta_obj), ex=RESULT_TTL)

def process_job(job: dict, rdb):
    job_id = job["job_id"]
    params = job["params"]
    created_at = job.get("created_at", datetime.now(timezone.utc).isoformat())

    log(f"Processing job {job_id} with params: {params}")

    try:
        update_job_status(rdb, job_id, "running")

        lat, lon = params.get("lat", 39.9), params.get("lon", 116.4)
        start_date = params.get("start_date", "2025-10-01")
        end_date = params.get("end_date", "2025-10-02")

        weather_df = get_weather({"lat": lat, "lon": lon}, start_date, end_date)

        result_df = simulate_greenhouse(weather_df, params)

        summary = {
            "Tin_min": float(result_df["Tin"].min()) if "Tin" in result_df.columns else None,
            "Tin_max": float(result_df["Tin"].max()) if "Tin" in result_df.columns else None,
            "Tin_mean": float(result_df["Tin"].mean()) if "Tin" in result_df.columns else None,
            "Heater_total_J": float(result_df["Q_heater"].sum()) if "Q_heater" in result_df.columns else None,
            "Heat_to_threshold_max_J": float(result_df["Q_to_threshold"].max()) if "Q_to_threshold" in result_df.columns else None,
            "Heat_to_threshold_mean_J": float(result_df["Q_to_threshold"].mean()) if "Q_to_threshold" in result_df.columns else None,
        }

        result_json = {
            "job_id": job_id,
            "created_at": created_at,
            "params": params,
            "summary": summary,
            "data": [
                {**row, "datetime": row["datetime"].isoformat() if isinstance(row["datetime"], pd.Timestamp) else row["datetime"]}
                for row in result_df.to_dict(orient="records")
            ],
        }

        rdb.set(f"{RESULT_PREFIX}{job_id}", json.dumps(result_json), ex=RESULT_TTL)
        update_job_status(rdb, job_id, "done")

        log(f"Job {job_id} complete. {len(result_df)} rows simulated.")

    except Exception as e:
        log(f"Error processing job {job_id}: {e}")
        traceback.print_exc()
        update_job_status(rdb, job_id, "error", str(e))

def main():
    rdb = connect_redis()
    log(f"Connected to Redis at {REDIS_ADDR}")
    log(f"Listening for jobs on queue: {QUEUE_NAME}")

    while True:
        try:
            job_data = rdb.blpop(QUEUE_NAME, timeout=0)
            if not job_data:
                continue
            _, raw = job_data
            job = json.loads(raw)
            process_job(job, rdb)
        except Exception as e:
            log(f"Redis or parsing error: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
