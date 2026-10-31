from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import DiaryEntry
from app.schemas.common import Page
from app.schemas.diary import DiaryCreate, DiaryRead, DiaryUpdate

router = APIRouter(prefix="/diary", tags=["Diary"])


def _get_entry_or_404(db: Session, entry_id: int) -> DiaryEntry:
    entry = db.get(DiaryEntry, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Diary entry not found"
        )
    return entry


def _duplicate_date_error(entry_date: date) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"A diary entry already exists for {entry_date.isoformat()}",
    )


@router.get("/entries", response_model=Page[DiaryRead])
def list_entries(
    db: Annotated[Session, Depends(get_db)],
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    mood: Annotated[str | None, Query(max_length=20)] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    sort_by: Annotated[
        Literal["entry_date", "created_at", "updated_at"], Query()
    ] = "entry_date",
    sort_order: Annotated[Literal["asc", "desc"], Query()] = "desc",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[DiaryRead]:
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_date must be earlier than or equal to end_date",
        )

    conditions = []
    if start_date is not None:
        conditions.append(DiaryEntry.entry_date >= start_date)
    if end_date is not None:
        conditions.append(DiaryEntry.entry_date <= end_date)
    if mood is not None and mood.strip():
        conditions.append(DiaryEntry.mood == mood.strip())
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(DiaryEntry.title.ilike(pattern), DiaryEntry.content.ilike(pattern))
        )

    total = db.scalar(select(func.count(DiaryEntry.id)).where(*conditions)) or 0

    sort_column = getattr(DiaryEntry, sort_by)
    order = sort_column.asc() if sort_order == "asc" else sort_column.desc()
    items = db.scalars(
        select(DiaryEntry)
        .where(*conditions)
        .order_by(order, DiaryEntry.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    return Page[DiaryRead](
        items=[DiaryRead.model_validate(entry) for entry in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/entries/by-date/{entry_date}", response_model=DiaryRead)
def get_entry_by_date(
    entry_date: date,
    db: Annotated[Session, Depends(get_db)],
) -> DiaryRead:
    entry = db.scalar(select(DiaryEntry).where(DiaryEntry.entry_date == entry_date))
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No diary entry exists for {entry_date.isoformat()}",
        )
    return DiaryRead.model_validate(entry)


@router.post("/entries", response_model=DiaryRead, status_code=status.HTTP_201_CREATED)
def create_entry(
    payload: DiaryCreate,
    db: Annotated[Session, Depends(get_db)],
) -> DiaryRead:
    existing = db.scalar(
        select(DiaryEntry).where(DiaryEntry.entry_date == payload.entry_date)
    )
    if existing is not None:
        raise _duplicate_date_error(payload.entry_date)

    entry = DiaryEntry(**payload.model_dump())
    db.add(entry)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _duplicate_date_error(payload.entry_date) from exc

    db.refresh(entry)
    return DiaryRead.model_validate(entry)


@router.get("/entries/{entry_id}", response_model=DiaryRead)
def get_entry(
    entry_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> DiaryRead:
    return DiaryRead.model_validate(_get_entry_or_404(db, entry_id))


@router.patch("/entries/{entry_id}", response_model=DiaryRead)
def update_entry(
    entry_id: int,
    payload: DiaryUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> DiaryRead:
    entry = _get_entry_or_404(db, entry_id)
    values = payload.model_dump(exclude_unset=True)

    new_date = values.get("entry_date", entry.entry_date)
    if new_date != entry.entry_date:
        duplicate = db.scalar(
            select(DiaryEntry).where(
                DiaryEntry.entry_date == new_date, DiaryEntry.id != entry.id
            )
        )
        if duplicate is not None:
            raise _duplicate_date_error(new_date)

    for field, value in values.items():
        setattr(entry, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _duplicate_date_error(new_date) from exc

    db.refresh(entry)
    return DiaryRead.model_validate(entry)


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    entry_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    entry = _get_entry_or_404(db, entry_id)
    db.delete(entry)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
