"""The hourly alert job.

Runs once an hour. For every active user it works out the user's local time
and sends, at most once each per day:

* the morning alert, from 06:00 (and up to 09:59, so a run that was missed at
  06:00 still delivers);
* a peak reminder when the current hour is HIGH or EXTREME inside the user's
  working hours (one per level, so an escalation to EXTREME is sent too);
* a warm-night alert at 20:00 or 21:00.

Every run is recorded as a heartbeat. If a run fails, the operator is told on
Telegram when OPERATOR_TELEGRAM_CHAT_ID is set, because a silent failure on a
hot day is the worst outcome.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from heatshield.forecast import ForecastError

from .config import Settings
from .db import JobRun, User
from .messaging import Channel, DeliveryError, TelegramChannel, dispatch, render_morning, render_peak, render_warm_night
from .service import current_row, day_summaries, hour_rows
from .weather import ForecastStore

log = logging.getLogger("heatshield.jobs")

MORNING_HOURS = range(6, 10)
WARM_NIGHT_HOURS = (20, 21)


def user_view(user: User, store: ForecastStore, settings: Settings, now: datetime):
    """Forecast rows and day summaries for one user, with their own limits."""
    fc = store.get(user.cell_lat, user.cell_lon)
    today = now.astimezone(ZoneInfo(fc.tz)).date()
    rows = hour_rows(fc.hours, user.workload, user.acclimatised_on(today))
    days = day_summaries(rows, settings.warm_night_c)
    return fc, today, rows, days


def process_user(
    session: Session, channels: list[Channel], store: ForecastStore, settings: Settings, user: User, now: datetime
) -> int:
    fc, today, rows, days = user_view(user, store, settings, now)
    local = now.astimezone(ZoneInfo(fc.tz))
    day = next((d for d in days if d["date"] == today.isoformat()), None)
    if day is None:
        return 0
    stale_note = "\nBased on an earlier forecast: the latest update could not be fetched." if fc.stale else ""
    sent = 0

    if user.morning_alerts and local.hour in MORNING_HOURS:
        title, body = render_morning(user, day, rows)
        sent += bool(dispatch(session, channels, user, "morning", today, "", day["level"], title, body + stale_note))

    row = current_row(rows, now)
    if (
        user.peak_reminders
        and row is not None
        and row["level"] in ("high", "extreme")
        and user.work_start <= local.hour < user.work_end
    ):
        title, body = render_peak(user, row)
        sent += bool(dispatch(session, channels, user, "peak", today, row["level"], row["level"], title, body + stale_note))

    if user.warm_night_alerts and local.hour in WARM_NIGHT_HOURS and day["warm_night"]:
        title, body = render_warm_night(user, day)
        sent += bool(dispatch(session, channels, user, "warm_night", today, "", "caution", title, body + stale_note))
    return sent


def run_tick(
    session_factory: sessionmaker[Session],
    channels: list[Channel],
    store: ForecastStore,
    settings: Settings,
    now: datetime | None = None,
) -> dict:
    now = now or datetime.now(timezone.utc)
    sent = failed_users = 0
    error = ""
    with session_factory() as session:
        users = list(session.scalars(select(User).where(User.paused.is_(False))))
        try:
            # One forecast call for all active cells, then per-user reads hit the cache.
            if users:
                store.get_many([(u.cell_lat, u.cell_lon) for u in users])
        except ForecastError as exc:
            error = f"forecast unavailable: {exc}"
        if not error:
            for user in users:
                try:
                    sent += process_user(session, channels, store, settings, user, now)
                except Exception as exc:  # one bad user must not stop the others
                    session.rollback()
                    failed_users += 1
                    error = f"{failed_users} user(s) failed, last: {type(exc).__name__}: {exc}"
                    log.exception("alert processing failed for user %s", user.id)
        result = {"ok": not error, "users": len(users), "sent": sent, "error": error}
        session.add(JobRun(job="tick", started_at=now, ok=not error, detail=str(result)))
        session.commit()
    if error:
        notify_operator(channels, settings, f"HeatShield alert job problem: {error}")
    return result


def notify_operator(channels: list[Channel], settings: Settings, text: str) -> None:
    if not settings.operator_chat_id:
        return
    for channel in channels:
        if isinstance(channel, TelegramChannel):
            try:
                channel.send_to_chat(settings.operator_chat_id, text)
            except DeliveryError:
                log.error("could not notify the operator")
