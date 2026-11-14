"""Alert text and delivery channels.

One message is rendered once and handed to every channel the user has
connected. Each channel is a small adapter with the same `send` signature, so a
provider can be swapped or added without touching the alert logic.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol

import requests
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import Settings
from .db import Alert, User, bump
from .service import LEVEL_INFO, WORKLOAD_INFO

DISCLAIMER = "Guidance only, not medical advice. Emergency: call 108 or 112."


def _clock(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%H:%M")


def _end_clock(iso: str) -> str:
    return "midnight" if _clock(iso) == "00:00" else _clock(iso)


def _range_text(ranges: list[dict]) -> str:
    return ", ".join(f"{_clock(r['start'])} to {_end_clock(r['end'])}" for r in ranges)


def render_morning(user: User, day: dict, rows: list[dict]) -> tuple[str, str]:
    level = LEVEL_INFO[day["level"]]
    work = WORKLOAD_INFO[user.workload]["label"].lower()
    title = f"Today's heat risk: {level['label'].upper()}"
    lines = [f"{user.area_label or 'Your area'}, {work} work."]
    lines.append(f"Peak heat stress (WBGT) {day['peak_wbgt_c']:.1f} °C at {_clock(day['peak_time'])}.")
    if day["dangerous"]:
        lines.append(f"Dangerous hours: {_range_text(day['dangerous'])}.")
        in_shift = [
            r
            for r in rows
            if datetime.fromisoformat(r["time"]).date().isoformat() == day["date"]
            and user.work_start <= datetime.fromisoformat(r["time"]).hour < user.work_end
            and r["level"] in ("high", "extreme")
        ]
        if in_shift:
            lines.append("Work and rest in each of those hours:")
            lines += [
                f"  {_clock(r['time'])}  " + (f"{r['work_min']} min work, {r['rest_min']} min rest" if r["work_min"] else "stop work")
                for r in in_shift
            ]
    elif day["caution"]:
        lines.append(f"Close to the limit: {_range_text(day['caution'])}.")
    else:
        lines.append("No dangerous hours expected.")
    lines.append(level["advice"])
    lines.append(level["water"])
    if not user.acclimatised_on(date.fromisoformat(day["date"])):
        lines.append("You are still getting used to the heat, so stricter limits apply.")
    lines.append(DISCLAIMER)
    return title, "\n".join(lines)


def render_peak(user: User, row: dict) -> tuple[str, str]:
    level = LEVEL_INFO[row["level"]]
    title = f"Heat risk is {level['label'].upper()} now"
    plan = f"{row['work_min']} min work, {row['rest_min']} min rest this hour." if row["work_min"] else "Stop this work for now."
    body = "\n".join(
        [
            f"{user.area_label or 'Your area'}: heat stress (WBGT) {row['wbgt_c']:.1f} °C, limit for your work {row['limit_c']:.1f} °C.",
            plan,
            level["advice"],
            level["water"],
            DISCLAIMER,
        ]
    )
    return title, body


def render_warm_night(user: User, day: dict) -> tuple[str, str]:
    title = "Warm night ahead"
    body = "\n".join(
        [
            f"{user.area_label or 'Your area'}: tonight will not drop below {day['night_min_air_c']:.0f} °C.",
            "Your body recovers from the day's heat at night, so a warm night makes tomorrow riskier.",
            "Sleep in the coolest, best ventilated place you can, drink water before bed, and take tomorrow's breaks seriously.",
            DISCLAIMER,
        ]
    )
    return title, body


class Channel(Protocol):
    name: str

    def ready_for(self, user: User) -> bool: ...

    def send(self, user: User, title: str, body: str) -> None:
        """Deliver, or raise DeliveryError."""


class DeliveryError(RuntimeError):
    pass


class WebChannel:
    """The web inbox: the alert row itself is the delivery."""

    name = "web"

    def ready_for(self, user: User) -> bool:
        return True

    def send(self, user: User, title: str, body: str) -> None:
        return None


class TelegramChannel:
    name = "telegram"

    def __init__(self, token: str, timeout: float = 15.0):
        self.token = token
        self.timeout = timeout

    def ready_for(self, user: User) -> bool:
        return bool(self.token and user.telegram_chat_id)

    def send_to_chat(self, chat_id: str, text: str) -> None:
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
                timeout=self.timeout,
            )
            ok = resp.status_code == 200 and resp.json().get("ok")
        except (requests.RequestException, ValueError) as exc:
            # Never include the exception text: the request URL contains the bot token.
            raise DeliveryError(f"telegram request failed ({type(exc).__name__})") from None
        if not ok:
            raise DeliveryError(f"telegram rejected the message (HTTP {resp.status_code})")

    def send(self, user: User, title: str, body: str) -> None:
        self.send_to_chat(user.telegram_chat_id, f"{title}\n\n{body}")


class WhatsAppChannel:
    """WhatsApp Cloud API. Business-initiated messages must use an approved
    template; the template is expected to have one body parameter, which gets a
    one-line summary (parameters cannot contain line breaks)."""

    name = "whatsapp"

    def __init__(self, token: str, phone_id: str, template: str, timeout: float = 15.0):
        self.token, self.phone_id, self.template, self.timeout = token, phone_id, template, timeout

    def ready_for(self, user: User) -> bool:
        return bool(self.token and self.phone_id and self.template and user.whatsapp_number)

    def send(self, user: User, title: str, body: str) -> None:
        summary = " ".join(f"{title}. {body}".split())[:1000]
        payload = {
            "messaging_product": "whatsapp",
            "to": user.whatsapp_number.lstrip("+"),
            "type": "template",
            "template": {
                "name": self.template,
                "language": {"code": "en"},
                "components": [{"type": "body", "parameters": [{"type": "text", "text": summary}]}],
            },
        }
        try:
            resp = requests.post(
                f"https://graph.facebook.com/v21.0/{self.phone_id}/messages",
                json=payload,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise DeliveryError(f"whatsapp request failed ({type(exc).__name__})") from None
        if resp.status_code != 200:
            raise DeliveryError(f"whatsapp rejected the message (HTTP {resp.status_code})")


def build_channels(settings: Settings) -> list[Channel]:
    channels: list[Channel] = [WebChannel()]
    if settings.telegram_ready:
        channels.append(TelegramChannel(settings.telegram_bot_token))
    if settings.whatsapp_ready:
        channels.append(WhatsAppChannel(settings.whatsapp_token, settings.whatsapp_phone_id, settings.whatsapp_template))
    return channels


def dispatch(
    session: Session,
    channels: list[Channel],
    user: User,
    kind: str,
    local_date: date,
    slot: str,
    level: str,
    title: str,
    body: str,
) -> Alert | None:
    """Store an alert and deliver it on every connected channel.

    Returns None if this alert (same user, kind, day and slot) was already
    sent, so a job that runs twice never sends twice.
    """
    exists = session.scalar(
        select(Alert.id).where(
            Alert.user_id == user.id, Alert.kind == kind, Alert.local_date == local_date, Alert.slot == slot
        )
    )
    if exists:
        return None
    alert = Alert(user_id=user.id, kind=kind, local_date=local_date, slot=slot, level=level, title=title, body=body)
    session.add(alert)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        return None

    deliveries: dict[str, str] = {}
    for channel in channels:
        if not channel.ready_for(user):
            continue
        try:
            channel.send(user, title, body)
            deliveries[channel.name] = "sent"
            bump(session, f"sent.{channel.name}")
        except DeliveryError as exc:
            deliveries[channel.name] = f"failed: {exc}"
            bump(session, f"failed.{channel.name}")
    alert.deliveries = deliveries
    bump(session, f"alerts.{kind}")
    session.commit()
    return alert


def link_telegram(session: Session, code: str, chat_id: str) -> User | None:
    """Attach a Telegram chat to the web account that owns `code`.

    Called by the Telegram bot when someone opens t.me/<bot>?start=<code>.
    The code is single-use.
    """
    code = code.strip()
    if not code:
        return None
    user = session.scalar(select(User).where(User.telegram_link_code == code))
    if user is None:
        return None
    user.telegram_chat_id = str(chat_id)
    user.telegram_link_code = ""
    session.commit()
    return user
