from datetime import date, datetime, time

from pydantic import Field, field_validator, model_validator

from app.schemas.common import APIModel


class CourseSessionRead(APIModel):
    id: int
    weekday: int = Field(ge=1, le=7)
    start_time: time
    end_time: time
    course_code: str
    course_name: str
    teacher: str | None
    location: str | None
    week_start: int | None
    week_end: int | None


class TimetableSummary(APIModel):
    id: int
    name: str
    source_filename: str
    semester_start_date: date | None
    active: bool
    session_count: int
    created_at: datetime
    updated_at: datetime


class TimetableDetail(TimetableSummary):
    sessions: list[CourseSessionRead]


class TimetableImportResult(APIModel):
    timetable: TimetableDetail
    warnings: list[str]


class TimetableUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    semester_start_date: date | None = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("name must not be blank")
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def reject_null_name(self) -> "TimetableUpdate":
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        return self


class DashboardDay(APIModel):
    weekday: int = Field(ge=1, le=7)
    weekday_name: str
    date: date
    courses: list[CourseSessionRead]


class TimetableDashboard(APIModel):
    timetable: TimetableSummary
    date: date
    week_start_date: date
    week_end_date: date
    current_week: int | None
    days: list[DashboardDay]
