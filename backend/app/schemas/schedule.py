from datetime import datetime

from pydantic import Field, field_validator, model_validator

from app.schemas.common import APIModel
from app.utils import normalize_utc


class ScheduleCreate(APIModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=200)
    start_at: datetime
    end_at: datetime
    all_day: bool = False

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("title must not be blank")
        return value.strip()

    @field_validator("start_at", "end_at")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return normalize_utc(value)

    @model_validator(mode="after")
    def end_must_be_after_start(self) -> "ScheduleCreate":
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        return self


class ScheduleUpdate(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=200)
    start_at: datetime | None = None
    end_at: datetime | None = None
    all_day: bool | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("title must not be blank")
        return value.strip() if value is not None else None

    @field_validator("start_at", "end_at")
    @classmethod
    def normalize_time(cls, value: datetime | None) -> datetime | None:
        return normalize_utc(value) if value is not None else None

    @model_validator(mode="after")
    def validate_time_order_when_both_present(self) -> "ScheduleUpdate":
        for field in ("title", "start_at", "end_at", "all_day"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        if (
            "start_at" in self.model_fields_set
            and "end_at" in self.model_fields_set
            and self.start_at is not None
            and self.end_at is not None
            and self.end_at <= self.start_at
        ):
            raise ValueError("end_at must be after start_at")
        return self


class ScheduleRead(APIModel):
    id: int
    title: str
    description: str | None
    location: str | None
    start_at: datetime
    end_at: datetime
    all_day: bool
    created_at: datetime
    updated_at: datetime
