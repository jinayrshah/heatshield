"""Shared fixtures for backend tests. No network: forecasts come from the recorded sample."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from backend.config import get_settings
from backend.weather import ForecastStore, SampleProvider

IST = ZoneInfo("Asia/Kolkata")
KURLA = (19.0876, 72.8867)


@pytest.fixture
def settings():
    return replace(
        get_settings(),
        database_url="sqlite:///:memory:",
        sample_data=True,
        scheduler_enabled=False,
        telegram_bot_token="",
        telegram_bot_username="",
        operator_chat_id="",
        whatsapp_token="",
        whatsapp_phone_id="",
        whatsapp_template="",
    )


@pytest.fixture
def store():
    return ForecastStore(SampleProvider())


def local_today(hour: int, minute: int = 0) -> datetime:
    """Today at the given local (Mumbai) time, as an aware datetime."""
    return datetime.now(IST).replace(hour=hour, minute=minute, second=0, microsecond=0)
