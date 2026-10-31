from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Transaction
from app.schemas.common import Page
from app.schemas.ledger import (
    LedgerGroup,
    LedgerSummary,
    TransactionCreate,
    TransactionRead,
    TransactionType,
    TransactionUpdate,
)
from app.utils import normalize_utc, utcnow

router = APIRouter(prefix="/ledger", tags=["Ledger"])


def _get_transaction_or_404(db: Session, transaction_id: int) -> Transaction:
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )
    return transaction


def _transaction_conditions(
    transaction_type: TransactionType | None,
    category: str | None,
    start_at: datetime | None,
    end_at: datetime | None,
    search: str | None,
) -> list:
    conditions = []
    if transaction_type is not None:
        conditions.append(Transaction.type == transaction_type)
    if category is not None:
        conditions.append(Transaction.category == category)
    if start_at is not None:
        conditions.append(Transaction.occurred_at >= start_at)
    if end_at is not None:
        # Half-open range: [start_at, end_at), convenient for month boundaries.
        conditions.append(Transaction.occurred_at < end_at)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(Transaction.category.ilike(pattern), Transaction.note.ilike(pattern))
        )
    return conditions


@router.get("/transactions", response_model=Page[TransactionRead])
def list_transactions(
    db: Annotated[Session, Depends(get_db)],
    transaction_type: Annotated[
        TransactionType | None,
        Query(alias="type", description="Filter by income or expense"),
    ] = None,
    category: Annotated[str | None, Query(max_length=50)] = None,
    start_at: Annotated[datetime | None, Query()] = None,
    end_at: Annotated[
        datetime | None, Query(description="Exclusive upper bound")
    ] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    sort_by: Annotated[
        Literal["occurred_at", "amount_cents", "created_at"], Query()
    ] = "occurred_at",
    sort_order: Annotated[Literal["asc", "desc"], Query()] = "desc",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[TransactionRead]:
    start_at = normalize_utc(start_at) if start_at is not None else None
    end_at = normalize_utc(end_at) if end_at is not None else None
    if start_at is not None and end_at is not None and start_at >= end_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_at must be earlier than end_at",
        )

    conditions = _transaction_conditions(
        transaction_type, category, start_at, end_at, search
    )

    total = db.scalar(select(func.count(Transaction.id)).where(*conditions)) or 0

    sort_column = getattr(Transaction, sort_by)
    order = sort_column.asc() if sort_order == "asc" else sort_column.desc()
    items = db.scalars(
        select(Transaction)
        .where(*conditions)
        .order_by(order, Transaction.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    return Page[TransactionRead](
        items=[TransactionRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/summary", response_model=LedgerSummary)
def ledger_summary(
    db: Annotated[Session, Depends(get_db)],
    transaction_type: Annotated[TransactionType | None, Query(alias="type")] = None,
    category: Annotated[str | None, Query(max_length=50)] = None,
    start_at: Annotated[datetime | None, Query()] = None,
    end_at: Annotated[
        datetime | None, Query(description="Exclusive upper bound")
    ] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    group_by: Annotated[Literal["category", "type"] | None, Query()] = None,
) -> LedgerSummary:
    start_at = normalize_utc(start_at) if start_at is not None else None
    end_at = normalize_utc(end_at) if end_at is not None else None
    if start_at is not None and end_at is not None and start_at >= end_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_at must be earlier than end_at",
        )

    conditions = _transaction_conditions(
        transaction_type, category, start_at, end_at, search
    )

    income_cents = int(
        db.scalar(
            select(func.coalesce(func.sum(Transaction.amount_cents), 0)).where(
                *conditions, Transaction.type == "income"
            )
        )
        or 0
    )
    expense_cents = int(
        db.scalar(
            select(func.coalesce(func.sum(Transaction.amount_cents), 0)).where(
                *conditions, Transaction.type == "expense"
            )
        )
        or 0
    )
    transaction_count = int(
        db.scalar(select(func.count(Transaction.id)).where(*conditions)) or 0
    )

    groups: list[LedgerGroup] = []
    if group_by is not None:
        rows = db.execute(
            select(
                Transaction.category,
                Transaction.type,
                func.sum(Transaction.amount_cents),
                func.count(Transaction.id),
            )
            .where(*conditions)
            .group_by(Transaction.category, Transaction.type)
        ).all()

        aggregated: dict[str, dict[str, int]] = {}
        for category_name, tx_type, amount, count in rows:
            key = category_name if group_by == "category" else tx_type
            bucket = aggregated.setdefault(
                key, {"income_cents": 0, "expense_cents": 0, "count": 0}
            )
            bucket[f"{tx_type}_cents"] += int(amount or 0)
            bucket["count"] += int(count or 0)

        for key, bucket in aggregated.items():
            groups.append(
                LedgerGroup(
                    key=key,
                    income_cents=bucket["income_cents"],
                    expense_cents=bucket["expense_cents"],
                    balance_cents=bucket["income_cents"] - bucket["expense_cents"],
                    count=bucket["count"],
                )
            )
        groups.sort(
            key=lambda group: group.income_cents + group.expense_cents, reverse=True
        )

    return LedgerSummary(
        start_at=normalize_utc(start_at) if start_at is not None else None,
        end_at=normalize_utc(end_at) if end_at is not None else None,
        income_cents=income_cents,
        expense_cents=expense_cents,
        balance_cents=income_cents - expense_cents,
        transaction_count=transaction_count,
        groups=groups,
    )


@router.post(
    "/transactions", response_model=TransactionRead, status_code=status.HTTP_201_CREATED
)
def create_transaction(
    payload: TransactionCreate,
    db: Annotated[Session, Depends(get_db)],
) -> TransactionRead:
    values = payload.model_dump()
    if values["occurred_at"] is None:
        values["occurred_at"] = utcnow()

    transaction = Transaction(**values)
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return TransactionRead.model_validate(transaction)


@router.get("/transactions/{transaction_id}", response_model=TransactionRead)
def get_transaction(
    transaction_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> TransactionRead:
    return TransactionRead.model_validate(_get_transaction_or_404(db, transaction_id))


@router.patch("/transactions/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> TransactionRead:
    transaction = _get_transaction_or_404(db, transaction_id)
    values = payload.model_dump(exclude_unset=True)
    for field, value in values.items():
        setattr(transaction, field, value)

    db.commit()
    db.refresh(transaction)
    return TransactionRead.model_validate(transaction)


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    transaction = _get_transaction_or_404(db, transaction_id)
    db.delete(transaction)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
