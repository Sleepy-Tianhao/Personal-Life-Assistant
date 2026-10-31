from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Schedule
from app.schemas.common import Page
from app.schemas.schedule import ScheduleCreate, ScheduleRead, ScheduleUpdate
from app.utils import normalize_utc

router = APIRouter(prefix="/schedules", tags=["Schedule"])


def _get_schedule_or_404(db: Session, schedule_id: int) -> Schedule:
    schedule = db.get(Schedule, schedule_id)
    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found"
        )
    return schedule


@router.get("", response_model=Page[ScheduleRead])
def list_schedules(
    db: Annotated[Session, Depends(get_db)],
    range_start: Annotated[
        datetime | None, Query(description="Return events that end after this time")
    ] = None,
    range_end: Annotated[
        datetime | None, Query(description="Return events that start before this time")
    ] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    sort_by: Annotated[
        Literal["start_at", "end_at", "created_at"], Query()
    ] = "start_at",
    sort_order: Annotated[Literal["asc", "desc"], Query()] = "asc",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[ScheduleRead]:
    range_start = normalize_utc(range_start) if range_start is not None else None
    range_end = normalize_utc(range_end) if range_end is not None else None
    if range_start is not None and range_end is not None and range_start >= range_end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="range_start must be earlier than range_end",
        )

    conditions = []
    if range_start is not None:
        conditions.append(Schedule.end_at > range_start)
    if range_end is not None:
        conditions.append(Schedule.start_at < range_end)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                Schedule.title.ilike(pattern),
                Schedule.description.ilike(pattern),
                Schedule.location.ilike(pattern),
            )
        )

    total = db.scalar(select(func.count(Schedule.id)).where(*conditions)) or 0

    sort_column = getattr(Schedule, sort_by)
    order = sort_column.asc() if sort_order == "asc" else sort_column.desc()
    items = db.scalars(
        select(Schedule)
        .where(*conditions)
        .order_by(order, Schedule.id.asc())
        .limit(limit)
        .offset(offset)
    ).all()

    return Page[ScheduleRead](
        items=[ScheduleRead.model_validate(schedule) for schedule in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=ScheduleRead, status_code=status.HTTP_201_CREATED)
def create_schedule(
    payload: ScheduleCreate,
    db: Annotated[Session, Depends(get_db)],
) -> ScheduleRead:
    schedule = Schedule(**payload.model_dump())
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return ScheduleRead.model_validate(schedule)


@router.get("/{schedule_id}", response_model=ScheduleRead)
def get_schedule(
    schedule_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> ScheduleRead:
    return ScheduleRead.model_validate(_get_schedule_or_404(db, schedule_id))


@router.patch("/{schedule_id}", response_model=ScheduleRead)
def update_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> ScheduleRead:
    schedule = _get_schedule_or_404(db, schedule_id)
    values = payload.model_dump(exclude_unset=True)

    new_start = normalize_utc(values.get("start_at", schedule.start_at))
    new_end = normalize_utc(values.get("end_at", schedule.end_at))
    if new_end <= new_start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="end_at must be after start_at",
        )

    for field, value in values.items():
        setattr(schedule, field, value)

    db.commit()
    db.refresh(schedule)
    return ScheduleRead.model_validate(schedule)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    schedule = _get_schedule_or_404(db, schedule_id)
    db.delete(schedule)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
