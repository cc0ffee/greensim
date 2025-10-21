import requests
import pandas as pd
import numpy as np
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")

def get_weather(location: dict, start_date: str, end_date: str, timezone: str = "auto") -> pd.DataFrame:
    lat, lon = location["lat"], location["lon"]

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,shortwave_radiation,relativehumidity_2m"
        f"&start_date={start_date}&end_date={end_date}"
        f"&timezone={timezone}"
    )

    logging.info(f"Fetching weather data: {url}")

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()

        if "hourly" not in data or "time" not in data["hourly"]:
            raise ValueError("Invalid data format from API")

        df = pd.DataFrame({
            "datetime": pd.to_datetime(data["hourly"]["time"]),
            "Tout": data["hourly"]["temperature_2m"],
            "G": data["hourly"]["shortwave_radiation"],
            "RH": np.array(data["hourly"].get("relativehumidity_2m", [50]*len(data["hourly"]["time"]))) / 100.0
        })

        logging.info(f"Retrieved {len(df)} hourly entries.")
        return df

    except Exception as e:
        logging.error(f"Failed to fetch weather data: {e}")
        return pd.DataFrame(columns=["datetime", "Tout", "G", "RH"])
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")

def get_weather(location: dict, start_date: str, end_date: str, timezone: str = "auto") -> pd.DataFrame:
    lat, lon = location["lat"], location["lon"]

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,shortwave_radiation,relativehumidity_2m"
        f"&start_date={start_date}&end_date={end_date}"
        f"&timezone={timezone}"
    )

    logging.info(f"Fetching weather data: {url}")

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()

        if "hourly" not in data or "time" not in data["hourly"]:
            raise ValueError("Invalid data format from API")

        df = pd.DataFrame({
            "datetime": pd.to_datetime(data["hourly"]["time"]),
            "Tout": data["hourly"]["temperature_2m"],
            "G": data["hourly"]["shortwave_radiation"],
            "RH": np.array(data["hourly"].get("relativehumidity_2m", [50]*len(data["hourly"]["time"]))) / 100.0
        })

        logging.info(f"Retrieved {len(df)} hourly entries.")
        return df

    except Exception as e:
        logging.error(f"Failed to fetch weather data: {e}")
        return pd.DataFrame(columns=["datetime", "Tout", "G", "RH"])
