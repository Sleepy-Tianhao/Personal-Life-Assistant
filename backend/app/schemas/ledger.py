from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.schemas.common import APIModel
from app.utils import normalize_utc

TransactionType = Literal["income", "expense"]


class TransactionCreate(APIModel):
    type: TransactionType
    amount_cents: int = Field(gt=0, le=1_000_000_000_000)
    category: str = Field(min_length=1, max_length=50)
    note: str | None = Field(default=None, max_length=500)
    occurred_at: datetime | None = None

    @field_validator("category")
    @classmethod
    def category_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("category must not be blank")
        return value.strip()

    @field_validator("occurred_at")
    @classmethod
    def normalize_occurred_at(cls, value: datetime | None) -> datetime | None:
        return normalize_utc(value) if value is not None else None


class TransactionUpdate(APIModel):
    type: TransactionType | None = None
    amount_cents: int | None = Field(default=None, gt=0, le=1_000_000_000_000)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    note: str | None = Field(default=None, max_length=500)
    occurred_at: datetime | None = None

    @field_validator("category")
    @classmethod
    def category_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("category must not be blank")
        return value.strip() if value is not None else None

    @field_validator("occurred_at")
    @classmethod
    def normalize_occurred_at(cls, value: datetime | None) -> datetime | None:
        return normalize_utc(value) if value is not None else None

    @model_validator(mode="after")
    def reject_null_for_required_fields(self) -> "TransactionUpdate":
        for field in ("type", "amount_cents", "category", "occurred_at"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class TransactionRead(APIModel):
    id: int
    type: TransactionType
    amount_cents: int
    category: str
    note: str | None
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime


class LedgerGroup(APIModel):
    key: str
    income_cents: int
    expense_cents: int
    balance_cents: int
    count: int


class LedgerSummary(APIModel):
    start_at: datetime | None
    end_at: datetime | None
    income_cents: int
    expense_cents: int
    balance_cents: int
    transaction_count: int
    groups: list[LedgerGroup]
