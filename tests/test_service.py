from datetime import date, datetime, timedelta, timezone

from backend.service import current_row, day_summaries, plan_windows

TZ = timezone(timedelta(hours=5, minutes=30))


def row(day: int, hour: int, wbgt: float, level: str, work: int, air: float = 30.0) -> dict:
    return {
        "time": datetime(2026, 5, day, hour, tzinfo=TZ).isoformat(),
        "air_c": air,
        "wbgt_c": wbgt,
        "level": level,
        "work_min": work,
        "rest_min": 60 - work,
    }


def hot_day(day: int, night_air: float = 26.0) -> list[dict]:
    rows = []
    for h in range(24):
        if 11 <= h < 13:
            rows.append(row(day, h, 33.0, "extreme", 0, 36.0))
        elif 9 <= h < 16:
            rows.append(row(day, h, 30.0, "high", 20, 34.0))
        elif h in (8, 16):
            rows.append(row(day, h, 26.0, "caution", 60, 31.0))
        else:
            rows.append(row(day, h, 22.0, "safe", 60, night_air))
    return rows


def test_day_summary_groups_dangerous_hours_into_one_range():
    (day,) = day_summaries(hot_day(1), warm_night_c=28)
    assert day["level"] == "extreme"
    assert day["peak_wbgt_c"] == 33.0
    assert [(r["start"][11:16], r["end"][11:16], r["level"]) for r in day["dangerous"]] == [("09:00", "16:00", "extreme")]
    assert [r["start"][11:16] for r in day["caution"]] == ["08:00", "16:00"]


def test_warm_night_uses_the_night_that_follows_the_day():
    rows = hot_day(1, night_air=26.0) + hot_day(2, night_air=29.0)
    d1, d2 = day_summaries(rows, warm_night_c=28)
    # Night of day 1 = 22:00-24:00 on day 1 (26) and 00:00-06:00 on day 2 (29).
    assert d1["night_min_air_c"] == 26.0 and not d1["warm_night"]
    # Day 2 has only its own two late hours: too few to judge the night.
    assert d2["night_min_air_c"] is None and not d2["warm_night"]
    d1_hot, _ = day_summaries(hot_day(1, night_air=29.0) + hot_day(2, night_air=29.0), warm_night_c=28)
    assert d1_hot["warm_night"]


def test_plan_prefers_safe_windows_and_never_overlaps():
    windows = plan_windows(hot_day(1), date(2026, 5, 1), duration_h=3, earliest_h=6, latest_h=20)
    assert windows[0]["level"] == "safe" and windows[0]["work_min"] == 180
    assert windows[0]["start"][11:16] == "17:00"  # 06:00-08:00 is only two safe hours
    for a in windows:
        for b in windows:
            assert a is b or a["end"] <= b["start"] or b["end"] <= a["start"]


def test_plan_reports_best_available_when_nothing_is_safe():
    windows = plan_windows(hot_day(1), date(2026, 5, 1), duration_h=4, earliest_h=9, latest_h=16)
    assert windows and windows[0]["level"] in ("high", "extreme")
    assert windows[0]["work_min"] < windows[0]["total_min"]


def test_plan_skips_windows_with_a_missing_hour():
    rows = [r for r in hot_day(1) if datetime.fromisoformat(r["time"]).hour != 19]
    windows = plan_windows(rows, date(2026, 5, 1), duration_h=3, earliest_h=17, latest_h=24)
    assert [w["start"][11:16] for w in windows] == ["20:00"]


def test_current_row_is_the_hour_containing_now():
    rows = hot_day(1)
    assert current_row(rows, datetime(2026, 5, 1, 11, 40, tzinfo=TZ))["level"] == "extreme"
    assert current_row(rows, datetime(2026, 5, 3, 11, 40, tzinfo=TZ)) is None
