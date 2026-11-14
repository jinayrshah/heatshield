"""Turn hourly WBGT into the things people ask for: now, today, plan, outlook."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from heatshield.forecast import HourlyWBGT
from heatshield.risk import METABOLIC_RATE_W, assess

LEVELS = ["safe", "caution", "high", "extreme"]
WORKLOADS = [w for w in METABOLIC_RATE_W if w != "rest"]
DANGEROUS = {"high", "extreme"}

WORKLOAD_INFO = {
    "light": {"label": "Light", "examples": "vending, traffic duty, security, driving"},
    "moderate": {"label": "Moderate", "examples": "delivery riding, cleaning, walking with a load"},
    "heavy": {"label": "Heavy", "examples": "construction, carrying bricks, digging"},
    "very_heavy": {"label": "Very heavy", "examples": "heavy shovelling, loading trucks"},
}

LEVEL_INFO = {
    "safe": {
        "label": "Safe",
        "advice": "Normal work is fine. Keep water within reach.",
        "water": "Drink water regularly through the day.",
    },
    "caution": {
        "label": "Caution",
        "advice": "Close to the limit for this work. Take your breaks in shade and watch for early symptoms.",
        "water": "Drink about a cup (250 ml) every 20 minutes while working.",
    },
    "high": {
        "label": "High",
        "advice": "Over the limit for continuous work. Follow the work and rest minutes, rest in shade, and work in pairs.",
        "water": "Drink a cup (250 ml) every 15 to 20 minutes, even if you are not thirsty. Do not drink more than 1.5 litres in an hour.",
    },
    "extreme": {
        "label": "Extreme",
        "advice": "Too hot for this work. Stop, or move it to a safer hour. If work cannot stop, switch to lighter tasks in shade.",
        "water": "Drink a cup (250 ml) every 15 to 20 minutes, even if you are not thirsty. Do not drink more than 1.5 litres in an hour.",
    },
}


def worst(levels) -> str:
    return max(levels, key=LEVELS.index)


def hour_rows(hours: list[HourlyWBGT], workload: str, acclimatised: bool) -> list[dict]:
    rows = []
    for h in hours:
        a = assess(h.wbgt_c, workload, acclimatised=acclimatised)
        rows.append(
            {
                "time": h.time_local.isoformat(),
                "air_c": round(h.air_c, 1),
                "rh_pct": round(h.rh_pct),
                "wind_ms": h.wind_2m_ms,
                "solar_wm2": round(h.solar_wm2),
                "globe_c": round(h.globe_c, 1),
                "wbgt_c": round(h.wbgt_c, 1),
                "limit_c": a.limit_c,
                "level": a.level.value,
                "work_min": a.work_minutes_per_hour,
                "rest_min": a.rest_minutes_per_hour,
            }
        )
    return rows


def _t(row: dict) -> datetime:
    return datetime.fromisoformat(row["time"])


def current_row(rows: list[dict], now: datetime | None = None) -> dict | None:
    """The forecast hour that contains `now` (None if the forecast does not cover it)."""
    now = now or datetime.now(timezone.utc)
    for row in rows:
        start = _t(row)
        if start <= now < start + timedelta(hours=1):
            return row
    return None


def _ranges(day_rows: list[dict], wanted: set[str]) -> list[dict]:
    """Group consecutive hours whose level is in `wanted` into start/end ranges."""
    out: list[dict] = []
    for row in day_rows:
        if row["level"] not in wanted:
            continue
        start = _t(row)
        end = start + timedelta(hours=1)
        if out and out[-1]["end"] == start.isoformat():
            out[-1]["end"] = end.isoformat()
            out[-1]["level"] = worst([out[-1]["level"], row["level"]])
        else:
            out.append({"start": start.isoformat(), "end": end.isoformat(), "level": row["level"]})
    return out


def day_summaries(rows: list[dict], warm_night_c: float) -> list[dict]:
    by_day: dict[date, list[dict]] = {}
    for row in rows:
        by_day.setdefault(_t(row).date(), []).append(row)

    out = []
    for day in sorted(by_day):
        day_rows = by_day[day]
        peak = max(day_rows, key=lambda r: r["wbgt_c"])
        night = [r for r in day_rows if _t(r).hour >= 22] + [
            r for r in by_day.get(day + timedelta(days=1), []) if _t(r).hour < 6
        ]
        night_min = min((r["air_c"] for r in night), default=None) if len(night) >= 6 else None
        level = worst(r["level"] for r in day_rows)
        out.append(
            {
                "date": day.isoformat(),
                "hours_covered": len(day_rows),
                "level": level,
                "peak_wbgt_c": peak["wbgt_c"],
                "peak_time": peak["time"],
                "max_air_c": max(r["air_c"] for r in day_rows),
                "min_work_min": min(r["work_min"] for r in day_rows),
                "dangerous": _ranges(day_rows, DANGEROUS),
                "caution": _ranges(day_rows, {"caution"}),
                "night_min_air_c": night_min,
                "warm_night": night_min is not None and night_min >= warm_night_c,
                "advice": LEVEL_INFO[level]["advice"],
                "water": LEVEL_INFO[level]["water"],
            }
        )
    return out


def plan_windows(
    rows: list[dict], day: date, duration_h: int, earliest_h: int = 0, latest_h: int = 24, limit: int = 3
) -> list[dict]:
    """Best start times on `day` for a job of `duration_h` consecutive hours.

    Ranked by the worst risk level in the window, then by how many minutes of
    work the window allows, then by the lower peak WBGT. Returned windows do not
    overlap, so the choices are genuinely different times of day.
    """
    day_rows = [r for r in rows if _t(r).date() == day and earliest_h <= _t(r).hour < latest_h]
    candidates = []
    for i in range(len(day_rows) - duration_h + 1):
        win = day_rows[i : i + duration_h]
        if _t(win[-1]) - _t(win[0]) != timedelta(hours=duration_h - 1):
            continue  # a skipped (missing) hour inside the window
        candidates.append(
            {
                "start": win[0]["time"],
                "end": (_t(win[-1]) + timedelta(hours=1)).isoformat(),
                "level": worst(r["level"] for r in win),
                "work_min": sum(r["work_min"] for r in win),
                "total_min": duration_h * 60,
                "peak_wbgt_c": max(r["wbgt_c"] for r in win),
            }
        )
    candidates.sort(key=lambda c: (LEVELS.index(c["level"]), -c["work_min"], c["peak_wbgt_c"], c["start"]))
    picked: list[dict] = []
    for c in candidates:
        if all(c["end"] <= p["start"] or c["start"] >= p["end"] for p in picked):
            picked.append(c)
        if len(picked) == limit:
            break
    return picked
