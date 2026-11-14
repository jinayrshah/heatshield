"""Database models. SQLite by default; set DATABASE_URL for Postgres."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker
from sqlalchemy.pool import StaticPool


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    name: Mapped[str] = mapped_column(String(80), default="")
    # Location is stored as a ~1 km cell, never as exact coordinates.
    area_label: Mapped[str] = mapped_column(String(160), default="")
    cell_lat: Mapped[float] = mapped_column(Float)
    cell_lon: Mapped[float] = mapped_column(Float)
    tz: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    workload: Mapped[str] = mapped_column(String(16), default="heavy")
    work_start: Mapped[int] = mapped_column(Integer, default=8)  # local hour, inclusive
    work_end: Mapped[int] = mapped_column(Integer, default=18)  # local hour, exclusive
    # Unacclimatised (stricter limits) up to and including this local date.
    new_to_heat_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    morning_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    peak_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    warm_night_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    telegram_link_code: Mapped[str] = mapped_column(String(32), default="", index=True)
    telegram_chat_id: Mapped[str] = mapped_column(String(32), default="")
    whatsapp_number: Mapped[str] = mapped_column(String(20), default="")

    alerts: Mapped[list["Alert"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def acclimatised_on(self, day: date) -> bool:
        return self.new_to_heat_until is None or day > self.new_to_heat_until


class Alert(Base):
    __tablename__ = "alerts"
    # One alert of each kind per user per local day and slot: makes sending idempotent.
    __table_args__ = (UniqueConstraint("user_id", "kind", "local_date", "slot"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # morning | peak | warm_night | test
    local_date: Mapped[date] = mapped_column(Date)
    slot: Mapped[str] = mapped_column(String(32), default="")
    level: Mapped[str] = mapped_column(String(16), default="safe")
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    deliveries: Mapped[dict] = mapped_column(JSON, default=dict)  # channel -> "sent" | "failed: ..."
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="alerts")


class Counter(Base):
    """Anonymous running totals for the public statistics page.

    Kept separately from alerts so the totals survive when a user deletes
    their data.
    """

    __tablename__ = "counters"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, default=0)


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job: Mapped[str] = mapped_column(String(32), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    detail: Mapped[str] = mapped_column(Text, default="")


def make_engine(url: str):
    if url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool
        return create_engine(url, **kwargs)
    return create_engine(url, pool_pre_ping=True)


def make_session_factory(url: str) -> sessionmaker[Session]:
    engine = make_engine(url)
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


def bump(session: Session, key: str, by: int = 1) -> None:
    row = session.get(Counter, key)
    if row is None:
        session.add(Counter(key=key, value=by))
    else:
        row.value += by
