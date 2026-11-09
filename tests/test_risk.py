import pytest

from heatshield.risk import RiskLevel, assess, wbgt_limit, work_fraction


def test_niosh_limits():
    # NIOSH 2016 REL for moderate work (300 W) is about 28.2 C WBGT.
    assert wbgt_limit(300) == pytest.approx(28.2, abs=0.1)
    # Unacclimatised workers get a lower limit.
    assert wbgt_limit(300, acclimatised=False) < wbgt_limit(300)


def test_cool_conditions_are_safe_full_hour():
    a = assess(22.0, "heavy")
    assert a.level is RiskLevel.SAFE
    assert a.work_minutes_per_hour == 60


def test_heavier_work_gets_less_work_time():
    light = work_fraction(30.0, "light")
    heavy = work_fraction(30.0, "heavy")
    assert heavy < light


def test_unacclimatised_more_restricted():
    assert work_fraction(29.0, "heavy", acclimatised=False) <= work_fraction(29.0, "heavy")


def test_extreme_means_no_work():
    a = assess(34.0, "heavy")
    assert a.level is RiskLevel.EXTREME
    assert a.work_minutes_per_hour == 0
    assert a.rest_minutes_per_hour == 60


def test_high_risk_gives_partial_work():
    a = assess(28.0, "heavy")  # heavy limit ~26.6 C
    assert a.level is RiskLevel.HIGH
    assert 0 < a.work_minutes_per_hour < 60
    assert a.work_minutes_per_hour % 5 == 0


def test_caution_band_just_below_limit():
    limit = wbgt_limit(415)
    assert assess(limit - 1.0, "heavy").level is RiskLevel.CAUTION


def test_unknown_workload_rejected():
    with pytest.raises(ValueError):
        assess(30.0, "juggling")
