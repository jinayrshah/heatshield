"""Solar geometry: cosine of the solar zenith angle.

Uses the NOAA general solar position equations (Spencer 1971 Fourier series),
accurate to roughly 0.1 degree — far better than the WBGT model needs.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone


def cos_zenith(when_utc: datetime, lat_deg: float, lon_deg: float) -> float:
    """Return cos(solar zenith angle) at a UTC instant and location.

    Negative values mean the sun is below the horizon.
    """
    if when_utc.tzinfo is None:
        raise ValueError("when_utc must be timezone-aware")
    t = when_utc.astimezone(timezone.utc)
    day_of_year = t.timetuple().tm_yday
    hour = t.hour + t.minute / 60 + t.second / 3600

    g = 2 * math.pi / 365 * (day_of_year - 1 + (hour - 12) / 24)
    eq_time_min = 229.18 * (
        0.000075
        + 0.001868 * math.cos(g)
        - 0.032077 * math.sin(g)
        - 0.014615 * math.cos(2 * g)
        - 0.040849 * math.sin(2 * g)
    )
    decl = (
        0.006918
        - 0.399912 * math.cos(g)
        + 0.070257 * math.sin(g)
        - 0.006758 * math.cos(2 * g)
        + 0.000907 * math.sin(2 * g)
        - 0.002697 * math.cos(3 * g)
        + 0.00148 * math.sin(3 * g)
    )
    true_solar_time_min = hour * 60 + eq_time_min + 4 * lon_deg
    hour_angle = math.radians(true_solar_time_min / 4 - 180)
    lat = math.radians(lat_deg)
    return math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.cos(hour_angle)
