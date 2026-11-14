from datetime import datetime

import pytest

from backend.weather import ForecastStore, SampleProvider, cell_of
from heatshield.forecast import ForecastError
from tests.conftest import IST, KURLA


class FlakyProvider:
    name = "flaky"

    def __init__(self):
        self.inner = SampleProvider()
        self.fail = False
        self.calls: list[list] = []

    def fetch(self, cells):
        self.calls.append(list(cells))
        if self.fail:
            raise ForecastError("down")
        return self.inner.fetch(cells)


def test_cell_rounds_to_about_one_km():
    assert cell_of(19.08763, 72.88671) == (19.09, 72.89)


def test_sample_forecast_starts_today_in_local_time():
    fc = ForecastStore(SampleProvider()).get(*KURLA)
    assert fc.tz == "Asia/Kolkata"
    assert fc.hours[0].time_local.date() == datetime.now(IST).date()
    assert fc.hours[0].time_local.hour == 0
    assert len(fc.hours) == 7 * 24
    assert all(10 < h.wbgt_c < 45 for h in fc.hours)


def test_points_in_one_cell_share_one_fetch_and_cache():
    provider = FlakyProvider()
    store = ForecastStore(provider)
    store.get_many([(19.0871, 72.8869), (19.0912, 72.8851), (18.92, 72.83)])
    store.get(19.09, 72.89)
    assert provider.calls == [[(18.92, 72.83), (19.09, 72.89)]]


def test_failed_refresh_serves_previous_forecast_marked_stale():
    provider = FlakyProvider()
    store = ForecastStore(provider, ttl_s=0)
    fresh = store.get(*KURLA)
    assert not fresh.stale
    provider.fail = True
    stale = store.get(*KURLA)
    assert stale.stale and stale.hours == fresh.hours
    # While the provider is down the old forecast is reused without hammering it.
    store.get(*KURLA)
    assert len(provider.calls) == 2


def test_failure_with_nothing_cached_raises():
    provider = FlakyProvider()
    provider.fail = True
    with pytest.raises(ForecastError):
        ForecastStore(provider).get(*KURLA)
