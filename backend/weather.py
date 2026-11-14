"""Forecast access for any location, with a per-cell cache.

Locations are rounded to a ~1 km cell (2 decimal places) before anything is
fetched or stored, so one Open-Meteo call serves everyone in that cell and the
service never needs a user's exact coordinates.

Open-Meteo is asked for unix timestamps (always UTC, so solar geometry is
unambiguous) together with `timezone=auto`, which returns the IANA timezone of
the location for local-day grouping.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

import requests

from heatshield.forecast import HOURLY_VARS, OPEN_METEO_URL, City, ForecastError, HourlyWBGT, compute_hourly_wbgt

DATA_DIR = Path(__file__).parent / "data"
FORECAST_DAYS = 7
MAX_POINTS_PER_CALL = 50

Cell = tuple[float, float]


def cell_of(lat: float, lon: float) -> Cell:
    return (round(lat, 2), round(lon, 2))


@dataclass(frozen=True)
class LocationForecast:
    lat: float
    lon: float
    tz: str
    hours: list[HourlyWBGT]
    fetched_at: datetime
    source: str  # "open-meteo" or "sample"
    stale: bool = False  # True when a refresh failed and an older forecast is served


class Provider(Protocol):
    name: str

    def fetch(self, cells: list[Cell]) -> list[dict]:
        """Return one Open-Meteo style payload (unix times, `timezone`) per cell."""


class OpenMeteoProvider:
    name = "open-meteo"

    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    def fetch(self, cells: list[Cell]) -> list[dict]:
        out: list[dict] = []
        for i in range(0, len(cells), MAX_POINTS_PER_CALL):
            chunk = cells[i : i + MAX_POINTS_PER_CALL]
            params = {
                "latitude": ",".join(str(c[0]) for c in chunk),
                "longitude": ",".join(str(c[1]) for c in chunk),
                "hourly": ",".join(HOURLY_VARS),
                "wind_speed_unit": "ms",
                "timezone": "auto",
                "timeformat": "unixtime",
                "forecast_days": FORECAST_DAYS,
            }
            try:
                resp = requests.get(OPEN_METEO_URL, params=params, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
            except (requests.RequestException, ValueError) as exc:
                raise ForecastError(f"Open-Meteo request failed: {exc}") from exc
            payloads = data if isinstance(data, list) else [data]
            if len(payloads) != len(chunk):
                raise ForecastError(f"Open-Meteo returned {len(payloads)} locations for {len(chunk)} requested")
            out.extend(payloads)
        return out


class SampleProvider:
    """Offline sample: a real Open-Meteo forecast for Mumbai recorded on 2026-11-14.

    Times are shifted so the recording starts today. It is for demos and
    development without internet only; the API marks every response as sample
    data and the web app shows a banner.
    """

    name = "sample"

    def __init__(self, path: Path = DATA_DIR / "sample_forecast_mumbai.json"):
        self._recorded: list[dict] = json.loads(path.read_text())

    def fetch(self, cells: list[Cell]) -> list[dict]:
        out = []
        for lat, lon in cells:
            rec = min(self._recorded, key=lambda r: (r["latitude"] - lat) ** 2 + (r["longitude"] - lon) ** 2)
            tz = ZoneInfo(rec["timezone"])
            first = datetime.fromtimestamp(rec["hourly"]["time"][0], tz)
            shift_days = (datetime.now(tz).date() - first.date()).days
            hourly = dict(rec["hourly"])
            hourly["time"] = [t + shift_days * 86400 for t in rec["hourly"]["time"]]
            out.append({**rec, "hourly": hourly})
        return out


def _to_hours(payload: dict, cell: Cell) -> tuple[str, list[HourlyWBGT]]:
    try:
        tz = payload["timezone"]
        hourly = dict(payload["hourly"])
        hourly["time"] = [
            datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M") for t in hourly["time"]
        ]
        ZoneInfo(tz)
    except (KeyError, TypeError, ValueError) as exc:
        raise ForecastError(f"unexpected forecast payload: {exc}") from exc
    city = City(name=f"{cell[0]},{cell[1]}", lat=cell[0], lon=cell[1], tz=tz)
    hours = compute_hourly_wbgt({"hourly": hourly}, city)
    if not hours:
        raise ForecastError("forecast contained no usable hours")
    return tz, hours


class ForecastStore:
    """In-memory forecast cache keyed by cell.

    If a refresh fails and an older forecast for the cell is still held, that
    forecast is returned with `stale=True` so callers can say so, rather than
    failing on a hot day.
    """

    def __init__(self, provider: Provider, ttl_s: int = 3600, max_stale_s: int = 36 * 3600):
        self.provider = provider
        self.ttl_s = ttl_s
        self.max_stale_s = max_stale_s
        self.retry_s = 300  # after a failed refresh, serve the old forecast this long before retrying
        self._cache: dict[Cell, tuple[float, LocationForecast]] = {}
        self._retry_at: dict[Cell, float] = {}
        self._lock = threading.Lock()

    def get(self, lat: float, lon: float) -> LocationForecast:
        return self.get_many([(lat, lon)])[0]

    def get_many(self, points: list[tuple[float, float]]) -> list[LocationForecast]:
        cells = [cell_of(lat, lon) for lat, lon in points]
        with self._lock:
            now = time.monotonic()
            missing = sorted(
                {
                    c
                    for c in cells
                    if c not in self._cache
                    or (now - self._cache[c][0] > self.ttl_s and now >= self._retry_at.get(c, 0.0))
                }
            )
            if missing:
                try:
                    payloads = self.provider.fetch(missing)
                    fetched_at = datetime.now(timezone.utc)
                    for cell, payload in zip(missing, payloads):
                        tz, hours = _to_hours(payload, cell)
                        self._cache[cell] = (
                            now,
                            LocationForecast(cell[0], cell[1], tz, hours, fetched_at, self.provider.name),
                        )
                        self._retry_at.pop(cell, None)
                except ForecastError:
                    usable = all(
                        c in self._cache and now - self._cache[c][0] <= self.max_stale_s for c in missing
                    )
                    if not usable:
                        raise
                    for c in missing:
                        ts, fc = self._cache[c]
                        self._cache[c] = (
                            ts,
                            LocationForecast(fc.lat, fc.lon, fc.tz, fc.hours, fc.fetched_at, fc.source, True),
                        )
                        self._retry_at[c] = now + self.retry_s
            return [self._cache[c][1] for c in cells]

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._retry_at.clear()

