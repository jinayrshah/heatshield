from datetime import datetime, timezone

import pytest

from heatshield.forecast import CITIES, ForecastError, compute_hourly_wbgt
from heatshield.solar import cos_zenith

MUMBAI = CITIES["mumbai"]


def _payload(times, **overrides):
    n = len(times)
    hourly = {
        "time": times,
        "temperature_2m": [32.0] * n,
        "relative_humidity_2m": [70.0] * n,
        "surface_pressure": [1006.0] * n,
        "wind_speed_10m": [3.0] * n,
        "shortwave_radiation": [0.0] * n,
        "direct_radiation": [0.0] * n,
    }
    hourly.update(overrides)
    return {"hourly": hourly}


def test_converts_to_local_time():
    rows = compute_hourly_wbgt(_payload(["2026-05-01T06:00"]), MUMBAI)
    assert rows[0].time_local.hour == 11  # IST = UTC+5:30
    assert rows[0].time_local.minute == 30


def test_midday_sun_raises_wbgt():
    # 07:00 UTC is ~12:30 IST: sun high over Mumbai.
    payload = _payload(
        ["2026-05-01T07:00", "2026-05-01T19:00"],
        shortwave_radiation=[900.0, 0.0],
        direct_radiation=[700.0, 0.0],
    )
    day, night = compute_hourly_wbgt(payload, MUMBAI)
    assert day.wbgt_c > night.wbgt_c + 2


def test_skips_hours_with_missing_values():
    payload = _payload(["2026-05-01T06:00", "2026-05-01T07:00"], temperature_2m=[None, 31.0])
    rows = compute_hourly_wbgt(payload, MUMBAI)
    assert len(rows) == 1


def test_malformed_payload_raises():
    with pytest.raises(ForecastError):
        compute_hourly_wbgt({"nothing": True}, MUMBAI)


def test_sun_position_noon_vs_midnight():
    noon_ist = datetime(2026, 5, 1, 7, 0, tzinfo=timezone.utc)
    midnight_ist = datetime(2026, 5, 1, 18, 30, tzinfo=timezone.utc)
    assert cos_zenith(noon_ist, MUMBAI.lat, MUMBAI.lon) > 0.9
    assert cos_zenith(midnight_ist, MUMBAI.lat, MUMBAI.lon) < 0


def test_sun_position_requires_timezone():
    with pytest.raises(ValueError):
        cos_zenith(datetime(2026, 5, 1, 7, 0), MUMBAI.lat, MUMBAI.lon)
