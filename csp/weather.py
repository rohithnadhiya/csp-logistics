"""
Weather module: fetch weather from OpenWeather API and compute slowdown factor.
"""

import os
import requests
from typing import Optional

OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5/weather"
TIMEOUT = 8


def _factor_from_weather(data):
    weather_ids = [w["id"] for w in data.get("weather", [])]
    wind_speed   = data.get("wind", {}).get("speed", 0)
    rain_1h      = data.get("rain", {}).get("1h", 0)
    factor = 1.0
    for wid in weather_ids:
        if wid < 300:
            factor = max(factor, 1.8)
        elif wid < 400:
            factor = max(factor, 1.15)
        elif wid < 600:
            factor = max(factor, 1.35)
        elif wid < 700:
            factor = max(factor, 1.6)
        elif wid < 800:
            factor = max(factor, 1.25)
        elif wid == 800:
            factor = max(factor, 1.0)
        else:
            factor = max(factor, 1.05)
    if wind_speed > 15:
        factor += 0.1
    if wind_speed > 25:
        factor += 0.15
    if rain_1h > 10:
        factor += 0.1
    return round(min(factor, 2.0), 3)


def get_weather(lat: float, lng: float, api_key: Optional[str] = None):
    key = api_key or os.environ.get("OPENWEATHER_API_KEY", "")
    if key:
        try:
            resp = requests.get(
                OPENWEATHER_BASE,
                params={"lat": lat, "lon": lng, "appid": key, "units": "metric"},
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            factor = _factor_from_weather(data)
            return {
                "factor": factor,
                "description": data["weather"][0]["description"].capitalize(),
                "temp_c": round(data["main"]["temp"], 1),
                "wind_ms": round(data.get("wind", {}).get("speed", 0), 1),
                "rain_1h": round(data.get("rain", {}).get("1h", 0), 1),
                "source": "api",
            }
        except Exception:
            pass

    # Deterministic simulation from coordinates
    seed = (lat * 31.7 + lng * 17.3) % 10
    if seed < 3:
        return {"factor": 1.0,  "description": "Clear sky",     "temp_c": 32.0, "wind_ms": 3.0,  "rain_1h": 0.0,  "source": "simulated"}
    elif seed < 5:
        return {"factor": 1.1,  "description": "Partly cloudy", "temp_c": 29.0, "wind_ms": 6.0,  "rain_1h": 0.0,  "source": "simulated"}
    elif seed < 7:
        return {"factor": 1.25, "description": "Light rain",    "temp_c": 26.0, "wind_ms": 9.0,  "rain_1h": 2.5,  "source": "simulated"}
    elif seed < 9:
        return {"factor": 1.4,  "description": "Moderate rain", "temp_c": 24.0, "wind_ms": 12.0, "rain_1h": 8.0,  "source": "simulated"}
    else:
        return {"factor": 1.65, "description": "Heavy storm",   "temp_c": 21.0, "wind_ms": 20.0, "rain_1h": 18.0, "source": "simulated"}
