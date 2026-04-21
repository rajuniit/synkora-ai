"""
Open-Meteo Tools — free weather data, no API key required.

Open-Meteo (https://open-meteo.com) is a free, open-source weather API with
no authentication required. It provides current conditions and hourly forecasts
using the same demand_modifier interface as the OpenWeather tools, so agents
can use either provider interchangeably.

Wind speeds from Open-Meteo are in km/h and are converted to m/s internally
so the shared demand rules apply consistently across both providers.
"""

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.open-meteo.com/v1/forecast"

_WMO_DESCRIPTIONS: dict[int, str] = {
    0: "clear sky",
    1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "icy fog",
    51: "light drizzle", 53: "moderate drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "moderate rain", 65: "heavy rain",
    71: "light snow", 73: "moderate snow", 75: "heavy snow",
    77: "snow grains",
    80: "light rain showers", 81: "moderate rain showers", 82: "heavy rain showers",
    85: "light snow showers", 86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with hail", 99: "heavy thunderstorm with hail",
}

_DEFAULT_DEMAND_RULES: list[dict[str, Any]] = [
    {"precip_pct_gte": 80, "modifier": 0.30},
    {"precip_pct_gte": 60, "modifier": 0.50},
    {"temp_c_lte": 0,      "modifier": 0.45},
    {"temp_c_lte": 5,      "modifier": 0.60},
    {"temp_c_gte": 38,     "modifier": 0.65},
    {"temp_c_gte": 33,     "modifier": 0.80},
    {"wind_mps_gte": 12,   "modifier": 0.75},
    {"temp_c_between": [15, 27], "precip_pct_lt": 20, "modifier": 1.25},
    {"temp_c_between": [10, 32], "modifier": 1.0},
]


def _wmo_description(code: int | None) -> str:
    return _WMO_DESCRIPTIONS.get(code or 0, "unknown")


def _compute_demand_modifier(
    temp: float,
    precip_pct: float,
    wind_mps: float,
    rules: list[dict[str, Any]],
) -> float:
    """Evaluate demand modifier rules. wind_mps must be in m/s."""
    for rule in rules:
        if "precip_pct_gte" in rule and precip_pct >= rule["precip_pct_gte"]:
            return float(rule["modifier"])
        if "temp_c_lte" in rule and temp <= rule["temp_c_lte"]:
            return float(rule["modifier"])
        if "temp_c_gte" in rule and temp >= rule["temp_c_gte"]:
            return float(rule["modifier"])
        if "wind_mps_gte" in rule and wind_mps >= rule["wind_mps_gte"]:
            return float(rule["modifier"])
        if "temp_c_between" in rule:
            lo, hi = rule["temp_c_between"]
            if lo <= temp <= hi:
                if "precip_pct_lt" in rule and precip_pct >= rule["precip_pct_lt"]:
                    continue
                return float(rule["modifier"])
    return 1.0


async def internal_get_openmeteo_forecast(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    lat: float = 0.0,
    lng: float = 0.0,
    hours_ahead: int = 24,
) -> dict[str, Any]:
    """
    Get hourly weather forecast for any location using Open-Meteo (free, no API key).

    Returns per-hour temperature, precipitation probability, wind speed, and a
    demand_modifier that reflects how weather conditions affect outdoor activity.
    Identical output format to the OpenWeather forecast tool.

    Args:
        lat: Latitude
        lng: Longitude
        hours_ahead: Number of hours to forecast (1–48)

    Returns:
        hours: list of hourly forecasts with demand_modifier
        overall_modifier: mean modifier over the window
        summary: human-readable weather summary
    """
    try:
        hours_ahead = max(1, min(int(hours_ahead), 48))

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(BASE_URL, params={
                "latitude": lat,
                "longitude": lng,
                "hourly": "temperature_2m,precipitation_probability,windspeed_10m,relativehumidity_2m,weathercode",
                "current_weather": "true",
                "forecast_days": 2,
                "timezone": "UTC",
            })

        if not resp.is_success:
            return {"success": False, "error": f"Open-Meteo error {resp.status_code}"}

        data = resp.json()
        hourly = data.get("hourly", {})
        times        = hourly.get("time", [])
        temps        = hourly.get("temperature_2m", [])
        precip_probs = hourly.get("precipitation_probability", [])
        windspeeds   = hourly.get("windspeed_10m", [])
        humidities   = hourly.get("relativehumidity_2m", [])
        weathercodes = hourly.get("weathercode", [])

        # Find the index for current hour and slice forward
        now_str = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:00")
        start_idx = next((i for i, t in enumerate(times) if t >= now_str), 0)
        end_idx = start_idx + hours_ahead

        result_hours = []
        modifiers = []

        for i in range(start_idx, min(end_idx, len(times))):
            temp        = float(temps[i]) if i < len(temps) else 15.0
            precip_pct  = float(precip_probs[i]) if i < len(precip_probs) else 0.0
            wind_kmh    = float(windspeeds[i]) if i < len(windspeeds) else 0.0
            wind_mps    = wind_kmh / 3.6
            humidity    = int(humidities[i]) if i < len(humidities) else 0
            code        = int(weathercodes[i]) if i < len(weathercodes) else 0

            modifier = _compute_demand_modifier(temp, precip_pct, wind_mps, _DEFAULT_DEMAND_RULES)
            modifiers.append(modifier)

            result_hours.append({
                "dt_iso": times[i] + ":00+00:00",
                "temp": round(temp, 1),
                "feels_like": None,
                "precip_pct": int(precip_pct),
                "wind_speed": round(wind_mps, 1),
                "humidity": humidity,
                "description": _wmo_description(code),
                "demand_modifier": round(modifier, 2),
            })

        overall = round(sum(modifiers) / len(modifiers), 2) if modifiers else 1.0

        if overall >= 1.15:
            summary = f"Favorable conditions — estimated demand +{round((overall - 1) * 100)}%"
        elif overall <= 0.65:
            summary = f"Poor conditions — estimated demand -{round((1 - overall) * 100)}%"
        else:
            summary = "Neutral conditions — no significant demand impact expected"

        return {
            "success": True,
            "provider": "open-meteo",
            "lat": lat,
            "lng": lng,
            "units": "metric",
            "hours_ahead": len(result_hours),
            "hours": result_hours,
            "overall_modifier": overall,
            "summary": summary,
        }

    except Exception as e:
        logger.error(f"internal_get_openmeteo_forecast failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_get_openmeteo_current(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    lat: float = 0.0,
    lng: float = 0.0,
) -> dict[str, Any]:
    """
    Get current weather conditions for any location using Open-Meteo (free, no API key).

    Returns temperature, description, wind speed, humidity, and a demand_modifier.
    Identical output format to the OpenWeather current weather tool.

    Args:
        lat: Latitude
        lng: Longitude

    Returns:
        temp, description, wind_speed, humidity, demand_modifier
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(BASE_URL, params={
                "latitude": lat,
                "longitude": lng,
                "current_weather": "true",
                "hourly": "precipitation_probability,relativehumidity_2m",
                "forecast_days": 1,
                "timezone": "UTC",
            })

        if not resp.is_success:
            return {"success": False, "error": f"Open-Meteo error {resp.status_code}"}

        data = resp.json()
        cw = data.get("current_weather", {})

        temp     = float(cw.get("temperature", 0))
        wind_kmh = float(cw.get("windspeed", 0))
        wind_mps = round(wind_kmh / 3.6, 1)
        code     = int(cw.get("weathercode", 0))

        # Get current hour's precip probability and humidity
        hourly   = data.get("hourly", {})
        times    = hourly.get("time", [])
        now_str  = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:00")
        idx      = next((i for i, t in enumerate(times) if t >= now_str), 0)
        precip_probs = hourly.get("precipitation_probability", [])
        humidities   = hourly.get("relativehumidity_2m", [])
        precip_pct   = float(precip_probs[idx]) if idx < len(precip_probs) else 0.0
        humidity     = int(humidities[idx]) if idx < len(humidities) else 0

        modifier = _compute_demand_modifier(temp, precip_pct, wind_mps, _DEFAULT_DEMAND_RULES)

        return {
            "success": True,
            "provider": "open-meteo",
            "lat": lat,
            "lng": lng,
            "temp": round(temp, 1),
            "feels_like": None,
            "description": _wmo_description(code),
            "wind_speed": wind_mps,
            "humidity": humidity,
            "rain_mm_1h": None,
            "units": "metric",
            "demand_modifier": round(modifier, 2),
        }

    except Exception as e:
        logger.error(f"internal_get_openmeteo_current failed: {e}")
        return {"success": False, "error": str(e)}
