"""Fetch an hourly forecast from Open-Meteo and compute hourly WBGT.

Open-Meteo (https://open-meteo.com) is free for non-commercial use and needs no
API key. Times are requested in UTC so solar geometry is unambiguous, then
converted to the city's local time for display.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

from .solar import cos_zenith
from .wbgt import outdoor_wbgt, wind_10m_to_2m

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "surface_pressure",
    "wind_speed_10m",
    "shortwave_radiation",
    "direct_radiation",
]


@dataclass(frozen=True)
class City:
    name: str
    lat: float
    lon: float
    tz: str


CITIES = {
    "mumbai": City("Mumbai", 19.0760, 72.8777, "Asia/Kolkata"),
}


@dataclass(frozen=True)
class HourlyWBGT:
    time_local: datetime
    air_c: float
    rh_pct: float
    wind_2m_ms: float
    solar_wm2: float
    globe_c: float
    natural_wet_bulb_c: float
    wbgt_c: float


class ForecastError(RuntimeError):
    """Raised when the forecast cannot be fetched or is malformed."""


def fetch_open_meteo(city: City, days: int = 2, timeout: float = 20.0) -> dict:
    params = {
        "latitude": city.lat,
        "longitude": city.lon,
        "hourly": ",".join(HOURLY_VARS),
        "wind_speed_unit": "ms",
        "timezone": "GMT",
        "forecast_days": days,
    }
    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise ForecastError(f"Open-Meteo request failed: {exc}") from exc


def compute_hourly_wbgt(payload: dict, city: City) -> list[HourlyWBGT]:
    """Convert an Open-Meteo hourly payload into WBGT per hour.

    Hours with missing values are skipped rather than guessed.
    """
    try:
        hourly = payload["hourly"]
        times = hourly["time"]
        columns = {v: hourly[v] for v in HOURLY_VARS}
    except (KeyError, TypeError) as exc:
        raise ForecastError(f"unexpected Open-Meteo payload: missing {exc}") from exc

    local_tz = ZoneInfo(city.tz)
    results: list[HourlyWBGT] = []
    for i, t in enumerate(times):
        row = {v: columns[v][i] for v in HOURLY_VARS}
        if any(val is None for val in row.values()):
            continue
        t_utc = datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
        # Open-Meteo radiation is the mean over the PRECEDING hour, so use the
        # sun position at the middle of that hour.
        cza = cos_zenith(t_utc - timedelta(minutes=30), city.lat, city.lon)
        solar = max(row["shortwave_radiation"], 0.0)
        fdir = row["direct_radiation"] / solar if solar > 0 else 0.0
        wind2 = wind_10m_to_2m(row["wind_speed_10m"])
        r = outdoor_wbgt(
            air_c=row["temperature_2m"],
            rh_pct=min(max(row["relative_humidity_2m"], 0.0), 100.0),
            wind_ms=wind2,
            solar_wm2=solar,
            cos_zenith=cza,
            direct_fraction=fdir,
            pressure_hpa=row["surface_pressure"],
        )
        results.append(
            HourlyWBGT(
                time_local=t_utc.astimezone(local_tz),
                air_c=row["temperature_2m"],
                rh_pct=row["relative_humidity_2m"],
                wind_2m_ms=round(wind2, 2),
                solar_wm2=solar,
                globe_c=r.globe_c,
                natural_wet_bulb_c=r.natural_wet_bulb_c,
                wbgt_c=r.wbgt_c,
            )
        )
    return results
