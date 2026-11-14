"""Settings, read once from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str
    sample_data: bool
    scheduler_enabled: bool
    cache_ttl_s: int
    warm_night_c: float
    telegram_bot_token: str
    telegram_bot_username: str
    operator_chat_id: str
    whatsapp_token: str
    whatsapp_phone_id: str
    whatsapp_template: str

    @property
    def telegram_ready(self) -> bool:
        return bool(self.telegram_bot_token)

    @property
    def whatsapp_ready(self) -> bool:
        return bool(self.whatsapp_token and self.whatsapp_phone_id and self.whatsapp_template)


@lru_cache
def get_settings() -> Settings:
    env = os.environ
    return Settings(
        database_url=env.get("DATABASE_URL", "sqlite:///./heatshield.db"),
        sample_data=_flag("HEATSHIELD_SAMPLE_DATA"),
        scheduler_enabled=_flag("HEATSHIELD_SCHEDULER", True),
        cache_ttl_s=int(env.get("HEATSHIELD_CACHE_TTL_S", "3600")),
        # HeatShield's own communication threshold (not a standard): a night whose
        # coolest hour stays at or above this air temperature gives little recovery.
        warm_night_c=float(env.get("HEATSHIELD_WARM_NIGHT_C", "28")),
        telegram_bot_token=env.get("TELEGRAM_BOT_TOKEN", ""),
        telegram_bot_username=env.get("TELEGRAM_BOT_USERNAME", ""),
        operator_chat_id=env.get("OPERATOR_TELEGRAM_CHAT_ID", ""),
        whatsapp_token=env.get("WHATSAPP_TOKEN", ""),
        whatsapp_phone_id=env.get("WHATSAPP_PHONE_ID", ""),
        whatsapp_template=env.get("WHATSAPP_TEMPLATE", ""),
    )
