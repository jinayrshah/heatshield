"""Alert job, message text and delivery channels."""

from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import select

from backend import messaging
from backend.db import Alert, Counter, JobRun, User, make_session_factory
from backend.jobs import run_tick
from backend.messaging import DeliveryError, TelegramChannel, WebChannel, WhatsAppChannel, link_telegram
from backend.weather import cell_of
from heatshield.forecast import ForecastError
from tests.conftest import KURLA, local_today


class RecordingChannel:
    def __init__(self, name="telegram", fail=False):
        self.name, self.fail, self.sent = name, fail, []

    def ready_for(self, user):
        return True

    def send(self, user, title, body):
        if self.fail:
            raise DeliveryError("provider down")
        self.sent.append((user.id, title, body))


@pytest.fixture
def sessions():
    return make_session_factory("sqlite:///:memory:")


def add_user(sessions, **kw) -> int:
    lat, lon = cell_of(*KURLA)
    defaults = dict(token_hash=str(kw.pop("n", 1)), cell_lat=lat, cell_lon=lon, area_label="Kurla", work_start=8, work_end=18)
    with sessions() as s:
        user = User(**{**defaults, **kw})
        s.add(user)
        s.commit()
        return user.id


def kinds(sessions) -> list[str]:
    with sessions() as s:
        return sorted(a.kind for a in s.scalars(select(Alert)))


def test_morning_alert_is_sent_once_even_if_the_job_runs_again(sessions, store, settings):
    add_user(sessions)
    tg = RecordingChannel()
    channels = [WebChannel(), tg]
    first = run_tick(sessions, channels, store, settings, now=local_today(6))
    again = run_tick(sessions, channels, store, settings, now=local_today(6, 30))
    assert first["ok"] and first["sent"] == 1 and again["sent"] == 0
    assert kinds(sessions) == ["morning"]
    assert len(tg.sent) == 1
    title, body = tg.sent[0][1:]
    assert title.startswith("Today's heat risk: ")
    assert "Kurla, heavy work." in body and "108" in body


def test_morning_alert_catches_up_after_a_missed_run_but_not_before_six(sessions, store, settings):
    add_user(sessions)
    assert run_tick(sessions, [WebChannel()], store, settings, now=local_today(5))["sent"] == 0
    assert run_tick(sessions, [WebChannel()], store, settings, now=local_today(9))["sent"] == 1


def test_paused_users_get_nothing(sessions, store, settings):
    add_user(sessions, paused=True)
    assert run_tick(sessions, [WebChannel()], store, settings, now=local_today(6))["sent"] == 0


def test_peak_reminder_only_inside_working_hours(sessions, store, settings):
    # The recorded day is HIGH for heavy work around midday.
    add_user(sessions, n=1, morning_alerts=False)
    add_user(sessions, n=2, morning_alerts=False, work_start=18, work_end=23)
    tg = RecordingChannel()
    result = run_tick(sessions, [WebChannel(), tg], store, settings, now=local_today(12))
    assert result["sent"] == 1
    assert kinds(sessions) == ["peak"]
    assert "now" in tg.sent[0][1]
    # Same level an hour later: no repeat.
    assert run_tick(sessions, [WebChannel(), tg], store, settings, now=local_today(13))["sent"] == 0


def test_warm_night_alert_depends_on_threshold(sessions, store, settings):
    add_user(sessions, morning_alerts=False, peak_reminders=False)
    assert run_tick(sessions, [WebChannel()], store, settings, now=local_today(20))["sent"] == 0
    warm = replace(settings, warm_night_c=15.0)
    assert run_tick(sessions, [WebChannel()], store, warm, now=local_today(20))["sent"] == 1
    assert kinds(sessions) == ["warm_night"]


def test_failed_delivery_is_recorded_and_other_channels_still_send(sessions, store, settings):
    add_user(sessions)
    run_tick(sessions, [WebChannel(), RecordingChannel("telegram", fail=True)], store, settings, now=local_today(6))
    with sessions() as s:
        alert = s.scalar(select(Alert))
        assert alert.deliveries == {"web": "sent", "telegram": "failed: provider down"}
        counters = {c.key: c.value for c in s.scalars(select(Counter))}
    assert counters == {"sent.web": 1, "failed.telegram": 1, "alerts.morning": 1}


def test_forecast_outage_is_recorded_as_a_failed_run_and_operator_is_told(sessions, settings, monkeypatch):
    class Down:
        def get_many(self, points):
            raise ForecastError("down")

    add_user(sessions)
    told = []
    monkeypatch.setattr(TelegramChannel, "send_to_chat", lambda self, chat, text: told.append((chat, text)))
    ops = replace(settings, operator_chat_id="999")
    result = run_tick(sessions, [WebChannel(), TelegramChannel("t")], Down(), ops, now=local_today(6))
    assert not result["ok"] and "forecast unavailable" in result["error"]
    assert told and told[0][0] == "999"
    with sessions() as s:
        assert s.scalar(select(JobRun)).ok is False


def test_new_to_heat_gets_stricter_schedule_and_a_note(sessions, store, settings):
    today = local_today(6).date()
    add_user(sessions, n=1)
    add_user(sessions, n=2, new_to_heat_until=today + timedelta(days=5))
    tg = RecordingChannel()
    run_tick(sessions, [tg], store, settings, now=local_today(6))
    bodies = {uid: body for uid, _, body in tg.sent}
    assert "stricter limits" not in bodies[1] and "stricter limits" in bodies[2]


def test_telegram_link_code_is_single_use(sessions):
    uid = add_user(sessions, telegram_link_code="abc123")
    with sessions() as s:
        assert link_telegram(s, "wrong", "42") is None
        assert link_telegram(s, "", "42") is None
        assert link_telegram(s, "abc123", "42").id == uid
        assert link_telegram(s, "abc123", "43") is None
        assert s.get(User, uid).telegram_chat_id == "42"


class FakeResponse:
    def __init__(self, status=200, payload=None):
        self.status_code, self._payload = status, payload or {"ok": True}

    def json(self):
        return self._payload


def test_telegram_channel_posts_to_the_bot_api_and_hides_the_token_on_errors(monkeypatch):
    calls = []
    monkeypatch.setattr(messaging.requests, "post", lambda url, **kw: calls.append((url, kw)) or FakeResponse())
    channel = TelegramChannel("SECRET")
    user = User(telegram_chat_id="42")
    assert channel.ready_for(user) and not channel.ready_for(User(telegram_chat_id=""))
    channel.send(user, "Title", "Body")
    assert calls[0][0] == "https://api.telegram.org/botSECRET/sendMessage"
    assert calls[0][1]["json"] == {"chat_id": "42", "text": "Title\n\nBody"}

    def boom(url, **kw):
        raise messaging.requests.ConnectionError(f"failed {url}")

    monkeypatch.setattr(messaging.requests, "post", boom)
    with pytest.raises(DeliveryError) as err:
        channel.send(user, "T", "B")
    assert "SECRET" not in str(err.value)
    monkeypatch.setattr(messaging.requests, "post", lambda url, **kw: FakeResponse(403, {"ok": False}))
    with pytest.raises(DeliveryError):
        channel.send(user, "T", "B")


def test_whatsapp_channel_sends_a_single_line_template_parameter(monkeypatch):
    calls = []
    monkeypatch.setattr(messaging.requests, "post", lambda url, **kw: calls.append((url, kw)) or FakeResponse())
    channel = WhatsAppChannel("tok", "123", "heat_alert")
    channel.send(User(whatsapp_number="+919812345678"), "Title", "line one\nline two")
    url, kw = calls[0]
    assert url.endswith("/123/messages") and kw["headers"]["Authorization"] == "Bearer tok"
    assert kw["json"]["to"] == "919812345678"
    assert kw["json"]["template"]["components"][0]["parameters"][0]["text"] == "Title. line one line two"
    assert not channel.ready_for(User(whatsapp_number=""))
