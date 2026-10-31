from __future__ import annotations

from datetime import UTC, date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    TypeDecorator,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils import normalize_utc, utcnow


class UTCDateTime(TypeDecorator):
    """Store naive UTC in SQLite and always return timezone-aware UTC."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        return normalize_utc(value).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, onupdate=utcnow, nullable=False
    )


class Todo(TimestampMixin, Base):
    __tablename__ = "todos"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed')", name="ck_todos_status"
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high')", name="ck_todos_priority"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )
    priority: Mapped[str] = mapped_column(
        String(20), default="medium", nullable=False, index=True
    )
    due_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    @property
    def is_overdue(self) -> bool:
        return (
            self.due_at is not None
            and self.status != "completed"
            and normalize_utc(self.due_at) < utcnow()
        )


class Transaction(TimestampMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("type IN ('income', 'expense')", name="ck_transactions_type"),
        CheckConstraint("amount_cents > 0", name="ck_transactions_amount_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, nullable=False, index=True
    )


class Schedule(TimestampMixin, Base):
    __tablename__ = "schedules"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ck_schedules_time_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    start_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, index=True
    )
    end_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, index=True)
    all_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DiaryEntry(TimestampMixin, Base):
    __tablename__ = "diary_entries"
    __table_args__ = (
        CheckConstraint("length(trim(content)) > 0", name="ck_diary_content_non_empty"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_date: Mapped[date] = mapped_column(
        Date, unique=True, nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    mood: Mapped[str | None] = mapped_column(String(20), nullable=True)
    weather: Mapped[str | None] = mapped_column(String(20), nullable=True)


class Timetable(TimestampMixin, Base):
    __tablename__ = "timetables"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    semester_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )

    sessions: Mapped[list[CourseSession]] = relationship(
        back_populates="timetable",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="[CourseSession.weekday, CourseSession.start_time]",
    )

    @property
    def session_count(self) -> int:
        return len(self.sessions)


class CourseSession(Base):
    __tablename__ = "course_sessions"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 1 AND 7", name="ck_course_sessions_weekday"),
        CheckConstraint("end_time > start_time", name="ck_course_sessions_time_order"),
        CheckConstraint(
            "week_start IS NULL OR week_end IS NULL OR week_end >= week_start",
            name="ck_course_sessions_week_order",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    timetable_id: Mapped[int] = mapped_column(
        ForeignKey("timetables.id", ondelete="CASCADE"), nullable=False, index=True
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    course_code: Mapped[str] = mapped_column(String(50), nullable=False)
    course_name: Mapped[str] = mapped_column(String(200), nullable=False)
    teacher: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    week_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    week_end: Mapped[int | None] = mapped_column(Integer, nullable=True)

    timetable: Mapped[Timetable] = relationship(back_populates="sessions")
