from datetime import date, datetime

from pydantic import Field, field_validator, model_validator

from app.schemas.common import APIModel


class DiaryCreate(APIModel):
    entry_date: date
    title: str | None = Field(default=None, max_length=200)
    content: str = Field(min_length=1, max_length=100_000)
    mood: str | None = Field(default=None, max_length=20)
    weather: str | None = Field(default=None, max_length=20)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be blank")
        return value


class DiaryUpdate(APIModel):
    entry_date: date | None = None
    title: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=100_000)
    mood: str | None = Field(default=None, max_length=20)
    weather: str | None = Field(default=None, max_length=20)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("content must not be blank")
        return value

    @model_validator(mode="after")
    def reject_null_for_required_fields(self) -> "DiaryUpdate":
        for field in ("entry_date", "content"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class DiaryRead(APIModel):
    id: int
    entry_date: date
    title: str | None
    content: str
    mood: str | None
    weather: str | None
    created_at: datetime
    updated_at: datetime
