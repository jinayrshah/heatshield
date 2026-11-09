import pytest

from heatshield.wbgt import outdoor_wbgt

# Reference values from thermofeel 2.x `calculate_wbgt_liljegren` (ECMWF's
# implementation of Liljegren 2008, as used operationally by KNMI), fed the same
# 2 m wind. Columns: air C, RH %, pressure hPa, 2 m wind m/s, solar W/m2,
# direct fraction, cos zenith, expected WBGT C.
REFERENCE = [
    (30, 80, 1008, 2.01, 0, 0.0, 0.0, 27.86),
    (34, 60, 1006, 1.57, 900, 0.8, 0.95, 33.96),
    (38, 40, 1000, 0.79, 1000, 0.85, 0.9, 36.60),
    (32, 75, 1007, 3.34, 600, 0.6, 0.6, 32.25),
    (28, 95, 1009, 0.79, 200, 0.2, 0.3, 29.75),
    (42, 25, 995, 3.14, 950, 0.9, 0.98, 33.23),
    (31, 70, 1008, 0.38, 0, 0.0, 0.0, 27.65),
]


@pytest.mark.parametrize("ta,rh,p,u2,s,fdir,cz,expected", REFERENCE)
def test_matches_reference_implementation(ta, rh, p, u2, s, fdir, cz, expected):
    r = outdoor_wbgt(ta, rh, u2, s, cz, fdir, p)
    assert r.wbgt_c == pytest.approx(expected, abs=0.1)


def test_no_sun_globe_close_to_air():
    r = outdoor_wbgt(30, 60, 2.0)
    assert abs(r.globe_c - 30) < 1.0


def test_sun_heats_the_globe():
    shade = outdoor_wbgt(33, 60, 1.5)
    sun = outdoor_wbgt(33, 60, 1.5, solar_wm2=900, cos_zenith=0.95, direct_fraction=0.8)
    assert sun.globe_c > shade.globe_c + 10
    assert sun.wbgt_c > shade.wbgt_c


def test_humidity_raises_wbgt():
    assert outdoor_wbgt(33, 85, 1.5).wbgt_c > outdoor_wbgt(33, 40, 1.5).wbgt_c


def test_wind_lowers_wbgt_in_sun():
    calm = outdoor_wbgt(35, 50, 0.3, 900, 0.9, 0.8)
    windy = outdoor_wbgt(35, 50, 5.0, 900, 0.9, 0.8)
    assert windy.wbgt_c < calm.wbgt_c


def test_wet_bulb_below_air_when_unsaturated():
    r = outdoor_wbgt(35, 50, 2.0)
    assert r.natural_wet_bulb_c < 35


def test_solar_ignored_when_sun_below_horizon():
    night = outdoor_wbgt(30, 70, 2.0)
    bogus = outdoor_wbgt(30, 70, 2.0, solar_wm2=500, cos_zenith=-0.2, direct_fraction=0.8)
    assert bogus.wbgt_c == night.wbgt_c


@pytest.mark.parametrize("rh", [-1, 101])
def test_rejects_bad_humidity(rh):
    with pytest.raises(ValueError):
        outdoor_wbgt(30, rh, 2.0)


def test_rejects_negative_solar():
    with pytest.raises(ValueError):
        outdoor_wbgt(30, 50, 2.0, solar_wm2=-5)
