"""HeatShield API. Run with:  uvicorn backend.main:app --reload"""

from __future__ import annotations

import hashlib
import logging
import re
import secrets
import threading
import time
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

import requests
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from heatshield import __version__
from heatshield.forecast import ForecastError

from . import wards
from .config import Settings, get_settings
from .content import EMERGENCY_NUMBERS, SYMPTOM_FLOW
from .db import Alert, Counter, JobRun, User, make_session_factory
from .jobs import run_tick, user_view
from .messaging import build_channels, dispatch, render_morning
from .service import LEVEL_INFO, WORKLOAD_INFO, WORKLOADS, current_row, day_summaries, hour_rows, plan_windows
from .weather import ForecastStore, LocationForecast, OpenMeteoProvider, SampleProvider, cell_of

log = logging.getLogger("heatshield.api")
WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

Workload = Literal["light", "moderate", "heavy", "very_heavy"]
Lat = Annotated[float, Query(ge=-90, le=90)]
Lon = Annotated[float, Query(ge=-180, le=180)]


class State:
    """Everything the routes share; built once in create_app so tests can swap parts."""

    def __init__(self, settings: Settings, store: ForecastStore | None = None):
        self.settings = settings
        self.store = store or ForecastStore(
            SampleProvider() if settings.sample_data else OpenMeteoProvider(), ttl_s=settings.cache_ttl_s
        )
        self.sessions = make_session_factory(settings.database_url)
        self.channels = build_channels(settings)
        self.scheduler = None
        self._ttl_cache: dict[str, tuple[float, object]] = {}
        self._ttl_lock = threading.Lock()

    def cached(self, key: str, ttl_s: float, make):
        with self._ttl_lock:
            hit = self._ttl_cache.get(key)
            if hit and time.monotonic() - hit[0] < ttl_s:
                return hit[1]
        value = make()
        with self._ttl_lock:
            if len(self._ttl_cache) > 2000:
                self._ttl_cache.clear()
            self._ttl_cache[key] = (time.monotonic(), value)
        return value


class SignUp(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    area_label: str = Field(default="", max_length=160)
    name: str = Field(default="", max_length=80)
    workload: Workload = "heavy"
    work_start: int = Field(default=8, ge=0, le=23)
    work_end: int = Field(default=18, ge=1, le=24)
    new_to_heat: bool = False
    whatsapp_number: str = Field(default="", max_length=20)

    @field_validator("whatsapp_number")
    @classmethod
    def _phone(cls, v: str) -> str:
        v = re.sub(r"[\s-]", "", v)
        if v and not re.fullmatch(r"\+?[1-9]\d{7,14}", v):
            raise ValueError("enter the number with country code, for example +919812345678")
        return v


class SettingsPatch(BaseModel):
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    area_label: str | None = Field(default=None, max_length=160)
    name: str | None = Field(default=None, max_length=80)
    workload: Workload | None = None
    work_start: int | None = Field(default=None, ge=0, le=23)
    work_end: int | None = Field(default=None, ge=1, le=24)
    new_to_heat: bool | None = None
    paused: bool | None = None
    morning_alerts: bool | None = None
    peak_reminders: bool | None = None
    warm_night_alerts: bool | None = None
    whatsapp_number: str | None = Field(default=None, max_length=20)

    _phone = field_validator("whatsapp_number")(SignUp._phone.__func__)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _meta(fc: LocationForecast) -> dict:
    ward = wards.ward_at(fc.lat, fc.lon)
    return {
        "lat": fc.lat,
        "lon": fc.lon,
        "tz": fc.tz,
        "ward": ward["ward"] if ward else None,
        "ward_areas": ward["areas"] if ward else None,
        "fetched_at": fc.fetched_at.isoformat(),
        "source": fc.source,
        "stale": fc.stale,
    }


def create_app(settings: Settings | None = None, store: ForecastStore | None = None) -> FastAPI:
    settings = settings or get_settings()
    state = State(settings, store)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.scheduler_enabled:
            from apscheduler.schedulers.background import BackgroundScheduler

            scheduler = BackgroundScheduler(timezone="UTC")
            tick = lambda: run_tick(state.sessions, state.channels, state.store, settings)  # noqa: E731
            # Minute 0 and 30 cover both whole-hour and half-hour timezones such as India (UTC+5:30).
            scheduler.add_job(tick, "cron", minute="0,30", id="tick", max_instances=1, coalesce=True)
            scheduler.start()
            state.scheduler = scheduler
        yield
        if state.scheduler:
            state.scheduler.shutdown(wait=False)

    app = FastAPI(
        title="HeatShield API",
        version=__version__,
        description="Heat-stress (WBGT) forecasts, work and rest guidance and alerts. Guidance only, not medical advice.",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.state.hs = state

    def db():
        with state.sessions() as session:
            yield session

    def forecast_for(lat: float, lon: float) -> LocationForecast:
        try:
            return state.store.get(lat, lon)
        except ForecastError as exc:
            log.warning("forecast failed: %s", exc)
            raise HTTPException(503, "The weather forecast could not be fetched. Please try again in a few minutes.")

    def current_user(authorization: Annotated[str, Header()] = "", session: Session = Depends(db)) -> User:
        token = authorization.removeprefix("Bearer ").strip()
        user = session.scalar(select(User).where(User.token_hash == _hash(token))) if token else None
        if user is None:
            raise HTTPException(401, "Sign up or sign in again on this device.")
        return user

    def user_json(user: User) -> dict:
        tz = ZoneInfo(user.tz)
        today = datetime.now(tz).date()
        tg = {"connected": bool(user.telegram_chat_id), "available": settings.telegram_ready, "link": None}
        if settings.telegram_ready and settings.telegram_bot_username and user.telegram_link_code:
            tg["link"] = f"https://t.me/{settings.telegram_bot_username}?start={user.telegram_link_code}"
        return {
            "id": user.id,
            "name": user.name,
            "area_label": user.area_label,
            "lat": user.cell_lat,
            "lon": user.cell_lon,
            "tz": user.tz,
            "workload": user.workload,
            "work_start": user.work_start,
            "work_end": user.work_end,
            "new_to_heat": not user.acclimatised_on(today),
            "new_to_heat_until": user.new_to_heat_until.isoformat() if user.new_to_heat_until else None,
            "paused": user.paused,
            "morning_alerts": user.morning_alerts,
            "peak_reminders": user.peak_reminders,
            "warm_night_alerts": user.warm_night_alerts,
            "telegram": tg,
            "whatsapp": {"number": user.whatsapp_number, "available": settings.whatsapp_ready},
        }

    # ---------------------------------------------------------------- public

    @app.get("/api/meta")
    def meta():
        return {
            "version": __version__,
            "sample_data": settings.sample_data,
            "workloads": [{"id": w, **WORKLOAD_INFO[w]} for w in WORKLOADS],
            "levels": [{"id": k, **v} for k, v in LEVEL_INFO.items()],
            "channels": {"web": True, "telegram": settings.telegram_ready, "whatsapp": settings.whatsapp_ready},
            "warm_night_c": settings.warm_night_c,
        }

    @app.get("/api/forecast")
    def forecast(
        lat: Lat,
        lon: Lon,
        workload: Workload = "heavy",
        acclimatised: bool = True,
        days: Annotated[int, Query(ge=1, le=7)] = 7,
    ):
        fc = forecast_for(lat, lon)
        rows = hour_rows(fc.hours, workload, acclimatised)
        first = datetime.fromisoformat(rows[0]["time"]).date()
        rows = [r for r in rows if (datetime.fromisoformat(r["time"]).date() - first).days < days]
        return {
            "location": _meta(fc),
            "workload": workload,
            "acclimatised": acclimatised,
            "now": current_row(rows),
            "days": day_summaries(rows, settings.warm_night_c)[:days],
            "hours": rows,
        }

    @app.get("/api/plan")
    def plan(
        lat: Lat,
        lon: Lon,
        duration_hours: Annotated[int, Query(ge=1, le=12)],
        workload: Workload = "heavy",
        acclimatised: bool = True,
        day: date | None = None,
        earliest_hour: Annotated[int, Query(ge=0, le=23)] = 6,
        latest_hour: Annotated[int, Query(ge=1, le=24)] = 20,
    ):
        if latest_hour - earliest_hour < duration_hours:
            raise HTTPException(422, "The job is longer than the time window you chose.")
        fc = forecast_for(lat, lon)
        rows = hour_rows(fc.hours, workload, acclimatised)
        now = datetime.now(ZoneInfo(fc.tz))
        day = day or now.date()
        # Never suggest a start time that has already passed.
        rows = [r for r in rows if datetime.fromisoformat(r["time"]) + timedelta(hours=1) > now]
        return {
            "location": _meta(fc),
            "day": day.isoformat(),
            "duration_hours": duration_hours,
            "windows": plan_windows(rows, day, duration_hours, earliest_hour, latest_hour),
        }

    @app.get("/api/city")
    def city(workload: Workload = "heavy", acclimatised: bool = True):
        """Hourly WBGT and risk for every Mumbai ward (48 hours from local midnight)."""
        ward_list = wards.wards()
        try:
            forecasts = state.store.get_many([(w["lat"], w["lon"]) for w in ward_list])
        except ForecastError:
            raise HTTPException(503, "The weather forecast could not be fetched. Please try again in a few minutes.")
        out, times = [], None
        for w, fc in zip(ward_list, forecasts):
            rows = hour_rows(fc.hours, workload, acclimatised)[:48]
            times = times or [r["time"] for r in rows]
            by_time = {r["time"]: r for r in rows}
            series = [by_time.get(t) for t in times]
            out.append(
                {
                    **w,
                    "wbgt_c": [r["wbgt_c"] if r else None for r in series],
                    "level": [r["level"] if r else None for r in series],
                    "work_min": [r["work_min"] if r else None for r in series],
                }
            )
        f0 = forecasts[0]
        return {
            "times": times,
            "wards": out,
            "workload": workload,
            "fetched_at": f0.fetched_at.isoformat(),
            "source": f0.source,
            "stale": any(f.stale for f in forecasts),
            "resolution_note": "The forecast model has a grid of roughly 10 km, so neighbouring wards can share the same values.",
        }

    @app.get("/api/wards.geojson")
    def wards_geojson():
        return JSONResponse(wards.geojson(), headers={"Cache-Control": "public, max-age=86400"})

    @app.get("/api/geocode")
    def geocode(q: Annotated[str, Query(min_length=2, max_length=80)]):
        results = wards.search(q)[:5]

        def remote():
            try:
                resp = requests.get(GEOCODE_URL, params={"name": q, "count": 6, "language": "en", "format": "json"}, timeout=8)
                resp.raise_for_status()
                return resp.json().get("results") or []
            except (requests.RequestException, ValueError):
                return None

        places = state.cached(f"geo:{q.lower()}", 86400, remote)
        if places is None:
            state._ttl_cache.pop(f"geo:{q.lower()}", None)  # do not remember a failure
        for p in places or []:
            parts = [p.get("name"), p.get("admin1"), p.get("country")]
            results.append({"label": ", ".join(x for x in parts if x), "lat": p["latitude"], "lon": p["longitude"]})
        return {"results": results[:8], "remote_ok": places is not None}

    @app.get("/api/water")
    def water(lat: Lat, lon: Lon, radius_m: Annotated[int, Query(ge=200, le=3000)] = 1500):
        """Drinking water, shelters and hospitals near a point, from OpenStreetMap."""
        clat, clon = cell_of(lat, lon)
        query = (
            f"[out:json][timeout:20];("
            f'nwr["amenity"~"^(drinking_water|water_point|shelter|hospital)$"](around:{radius_m},{clat},{clon});'
            f");out center 150;"
        )

        def remote():
            try:
                resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=25, headers={"User-Agent": "HeatShield/0.1"})
                resp.raise_for_status()
                return resp.json().get("elements", [])
            except (requests.RequestException, ValueError):
                return None

        key = f"water:{clat}:{clon}:{radius_m}"
        elements = state.cached(key, 86400, remote)
        if elements is None:
            state._ttl_cache.pop(key, None)
            raise HTTPException(503, "The OpenStreetMap service did not answer. Please try again shortly.")
        points = []
        for el in elements:
            plat = el.get("lat") or (el.get("center") or {}).get("lat")
            plon = el.get("lon") or (el.get("center") or {}).get("lon")
            tags = el.get("tags") or {}
            if plat is None or plon is None:
                continue
            kind = "water" if tags.get("amenity") in ("drinking_water", "water_point") else tags.get("amenity")
            points.append({"kind": kind, "name": tags.get("name", ""), "lat": plat, "lon": plon})
        return {"points": points, "attribution": "© OpenStreetMap contributors"}

    @app.get("/api/safety")
    def safety():
        return {"emergency_numbers": EMERGENCY_NUMBERS, "flow": SYMPTOM_FLOW}

    @app.get("/api/stats")
    def stats(session: Session = Depends(db)):
        counters = {c.key: c.value for c in session.scalars(select(Counter))}
        sent = sum(v for k, v in counters.items() if k.startswith("sent."))
        failed = sum(v for k, v in counters.items() if k.startswith("failed."))
        return {
            "users": session.scalar(select(func.count(User.id))) or 0,
            "active_users": session.scalar(select(func.count(User.id)).where(User.paused.is_(False))) or 0,
            "alerts": {k.removeprefix("alerts."): v for k, v in counters.items() if k.startswith("alerts.")},
            "deliveries": {k.removeprefix("sent."): v for k, v in counters.items() if k.startswith("sent.")},
            "delivery_rate": round(sent / (sent + failed), 3) if sent + failed else None,
        }

    @app.get("/api/health")
    def health(session: Session = Depends(db)):
        last = session.scalar(select(JobRun).where(JobRun.job == "tick").order_by(JobRun.id.desc()).limit(1))
        last_ok = session.scalar(
            select(JobRun).where(JobRun.job == "tick", JobRun.ok.is_(True)).order_by(JobRun.id.desc()).limit(1)
        )

        def aware(dt: datetime) -> datetime:
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

        age_min = (datetime.now(timezone.utc) - aware(last_ok.started_at)).total_seconds() / 60 if last_ok else None
        return {
            "status": "ok",
            "scheduler": bool(state.scheduler),
            "last_run": aware(last.started_at).isoformat() if last else None,
            "last_run_ok": last.ok if last else None,
            "last_run_detail": last.detail if last else None,
            "minutes_since_ok_run": round(age_min, 1) if age_min is not None else None,
            # The job runs every 30 minutes; two missed runs in a row means something is wrong.
            "alert_job_healthy": (age_min is not None and age_min < 75) if state.scheduler else None,
        }

    # ------------------------------------------------------------- accounts

    def apply_location(user: User, lat: float, lon: float, label: str | None) -> None:
        fc = forecast_for(lat, lon)  # validates the place has a forecast and gives its timezone
        user.cell_lat, user.cell_lon, user.tz = fc.lat, fc.lon, fc.tz
        if label is not None:
            user.area_label = label.strip()
        if not user.area_label:
            ward = wards.ward_at(fc.lat, fc.lon)
            user.area_label = f"{ward['areas']} ({ward['ward']} ward)" if ward else f"{fc.lat:.2f}, {fc.lon:.2f}"

    def set_new_to_heat(user: User, new: bool) -> None:
        today = datetime.now(ZoneInfo(user.tz)).date()
        if new and user.acclimatised_on(today):
            user.new_to_heat_until = today + timedelta(days=13)  # 14 days including today
        elif not new:
            user.new_to_heat_until = None

    def check_hours(start: int, end: int) -> None:
        if end <= start:
            raise HTTPException(422, "Work must end after it starts.")

    @app.post("/api/users", status_code=201)
    def sign_up(body: SignUp, session: Session = Depends(db)):
        check_hours(body.work_start, body.work_end)
        token = secrets.token_urlsafe(32)
        user = User(
            token_hash=_hash(token),
            name=body.name.strip(),
            workload=body.workload,
            work_start=body.work_start,
            work_end=body.work_end,
            whatsapp_number=body.whatsapp_number,
            telegram_link_code=secrets.token_urlsafe(12),
            cell_lat=0.0,
            cell_lon=0.0,
        )
        apply_location(user, body.lat, body.lon, body.area_label)
        set_new_to_heat(user, body.new_to_heat)
        session.add(user)
        session.commit()
        return {"token": token, "user": user_json(user)}

    @app.get("/api/me")
    def me(user: User = Depends(current_user)):
        return user_json(user)

    @app.patch("/api/me")
    def update_me(body: SettingsPatch, user: User = Depends(current_user), session: Session = Depends(db)):
        data = body.model_dump(exclude_unset=True)
        if ("lat" in data) != ("lon" in data):
            raise HTTPException(422, "Send lat and lon together.")
        if "lat" in data:
            apply_location(user, data["lat"], data["lon"], data.get("area_label"))
        elif data.get("area_label"):
            user.area_label = data["area_label"].strip()
        for field in ("name", "workload", "work_start", "work_end", "paused", "morning_alerts", "peak_reminders", "warm_night_alerts", "whatsapp_number"):
            if data.get(field) is not None:
                setattr(user, field, data[field])
        check_hours(user.work_start, user.work_end)
        if data.get("new_to_heat") is not None:
            set_new_to_heat(user, data["new_to_heat"])
        session.commit()
        return user_json(user)

    @app.delete("/api/me", status_code=204)
    def delete_me(user: User = Depends(current_user), session: Session = Depends(db)):
        """Delete the account and every alert stored for it."""
        session.delete(user)
        session.commit()

    @app.get("/api/me/today")
    def my_today(user: User = Depends(current_user)):
        try:
            fc, today, rows, days = user_view(user, state.store, settings, datetime.now(timezone.utc))
        except ForecastError:
            raise HTTPException(503, "The weather forecast could not be fetched. Please try again in a few minutes.")
        return {
            "location": _meta(fc),
            "now": current_row(rows),
            "day": next((d for d in days if d["date"] == today.isoformat()), None),
        }

    @app.get("/api/me/alerts")
    def my_alerts(user: User = Depends(current_user), session: Session = Depends(db)):
        alerts = session.scalars(select(Alert).where(Alert.user_id == user.id).order_by(Alert.id.desc()).limit(50))
        return {
            "alerts": [
                {
                    "id": a.id,
                    "kind": a.kind,
                    "level": a.level,
                    "title": a.title,
                    "body": a.body,
                    "created_at": (a.created_at if a.created_at.tzinfo else a.created_at.replace(tzinfo=timezone.utc)).isoformat(),
                    "deliveries": a.deliveries,
                }
                for a in alerts
            ]
        }

    @app.post("/api/me/alerts/preview", status_code=201)
    def preview_alert(user: User = Depends(current_user), session: Session = Depends(db)):
        """Send today's morning alert right now, on every connected channel."""
        try:
            fc, today, rows, days = user_view(user, state.store, settings, datetime.now(timezone.utc))
        except ForecastError:
            raise HTTPException(503, "The weather forecast could not be fetched. Please try again in a few minutes.")
        day = next((d for d in days if d["date"] == today.isoformat()), None)
        if day is None:
            raise HTTPException(503, "No forecast for today yet.")
        title, body = render_morning(user, day, rows)
        slot = datetime.now(timezone.utc).strftime("%H%M%S%f")
        alert = dispatch(session, state.channels, user, "test", today, slot, day["level"], title, body)
        return {"id": alert.id, "deliveries": alert.deliveries}

    # ------------------------------------------------------------- web app

    if WEB_DIST.is_dir():
        app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path.startswith("api/"):
                raise HTTPException(404)
            target = (WEB_DIST / path).resolve()
            if path and target.is_file() and WEB_DIST in target.parents:
                return FileResponse(target)
            return FileResponse(WEB_DIST / "index.html")

    return app


app = create_app()
