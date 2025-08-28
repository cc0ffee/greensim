import requests
import pandas as pd

def get_weather(location: dict, start_date: str, end_date: str):
    """
    location: {"lat": float, "lon": float}
    Returns hourly weather with outdoor T and solar GHI
    """
    lat, lon = location["lat"], location["lon"]
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,shortwave_radiation"
    )
    r = requests.get(url)
    data = r.json()

    print(data)

    df = pd.DataFrame({
        "datetime": pd.to_datetime(data["hourly"]["time"]),
        "Tout": data["hourly"]["temperature_2m"],
        "G": data["hourly"]["shortwave_radiation"],
    })
    return df