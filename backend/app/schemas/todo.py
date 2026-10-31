from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.schemas.common import APIModel
from app.utils import normalize_utc

TodoStatus = Literal["pending", "in_progress", "completed"]
TodoPriority = Literal["low", "medium", "high"]


class TodoCreate(APIModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: TodoStatus = "pending"
    priority: TodoPriority = "medium"
    due_at: datetime | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("title must not be blank")
        return value.strip()

    @field_validator("due_at")
    @classmethod
    def normalize_due_at(cls, value: datetime | None) -> datetime | None:
        return normalize_utc(value) if value is not None else None


class TodoUpdate(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: TodoStatus | None = None
    priority: TodoPriority | None = None
    due_at: datetime | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("title must not be blank")
        return value.strip() if value is not None else None

    @field_validator("due_at")
    @classmethod
    def normalize_due_at(cls, value: datetime | None) -> datetime | None:
        return normalize_utc(value) if value is not None else None

    @model_validator(mode="after")
    def reject_null_for_required_fields(self) -> "TodoUpdate":
        for field in ("title", "status", "priority"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class TodoRead(APIModel):
    id: int
    title: str
    description: str | None
    status: TodoStatus
    priority: TodoPriority
    due_at: datetime | None
    completed_at: datetime | None
    is_overdue: bool
    created_at: datetime
    updated_at: datetime
