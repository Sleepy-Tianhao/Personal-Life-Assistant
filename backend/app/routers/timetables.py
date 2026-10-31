from datetime import date, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import CourseSession, Timetable
from app.schemas.timetable import (
    CourseSessionRead,
    DashboardDay,
    TimetableDashboard,
    TimetableDetail,
    TimetableImportResult,
    TimetableSummary,
    TimetableUpdate,
)
from app.timetable_parser import TimetableParseError, parse_timetable_html

router = APIRouter(prefix="/timetables", tags=["Timetable"])

MAX_TIMETABLE_BYTES = 2 * 1024 * 1024
ALLOWED_SUFFIXES = {".html", ".htm"}
ALLOWED_CONTENT_TYPES = {"text/html", "application/xhtml+xml"}
WEEKDAY_NAMES = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)


def _get_timetable_or_404(db: Session, timetable_id: int) -> Timetable:
    timetable = db.get(Timetable, timetable_id)
    if timetable is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Timetable not found"
        )
    return timetable


def _get_active_timetable_or_404(db: Session) -> Timetable:
    timetable = db.scalar(
        select(Timetable)
        .where(Timetable.active.is_(True))
        .order_by(Timetable.created_at.desc(), Timetable.id.desc())
    )
    if timetable is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active timetable. Import or activate one first.",
        )
    return timetable


@router.get("", response_model=list[TimetableSummary])
def list_timetables(
    db: Annotated[Session, Depends(get_db)],
) -> list[TimetableSummary]:
    timetables = db.scalars(
        select(Timetable).order_by(
            Timetable.active.desc(), Timetable.created_at.desc(), Timetable.id.desc()
        )
    ).all()
    return [TimetableSummary.model_validate(timetable) for timetable in timetables]


@router.post(
    "/import", response_model=TimetableImportResult, status_code=status.HTTP_201_CREATED
)
async def import_timetable(
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(description="导出的 HTML 课表文件")],
    name: Annotated[str | None, Form(max_length=200)] = None,
    semester_start_date: Annotated[date | None, Form()] = None,
    set_active: Annotated[bool, Form()] = True,
) -> TimetableImportResult:
    source_filename = Path(file.filename or "").name
    suffix = Path(source_filename).suffix.lower()
    content_type = (file.content_type or "").split(";", 1)[0].lower()
    if not source_filename or (
        suffix not in ALLOWED_SUFFIXES and content_type not in ALLOWED_CONTENT_TYPES
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="仅支持上传 .html 或 .htm 格式的课表文件",
        )

    content = await file.read(MAX_TIMETABLE_BYTES + 1)
    await file.close()
    if len(content) > MAX_TIMETABLE_BYTES:
        raise HTTPException(status_code=413, detail="课表文件不能超过 2 MB")
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="课表文件为空",
        )

    try:
        parsed = parse_timetable_html(content)
    except TimetableParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    display_name = (name or Path(source_filename).stem).strip()
    if not display_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="课表名称不能为空",
        )

    if set_active:
        db.execute(update(Timetable).values(active=False))

    timetable = Timetable(
        name=display_name[:200],
        source_filename=source_filename[:255],
        semester_start_date=semester_start_date,
        active=set_active,
    )
    for course in parsed.sessions:
        timetable.sessions.append(
            CourseSession(
                weekday=course.weekday,
                start_time=course.start_time,
                end_time=course.end_time,
                course_code=course.course_code,
                course_name=course.course_name,
                teacher=course.teacher,
                location=course.location,
                week_start=course.week_start,
                week_end=course.week_end,
            )
        )

    db.add(timetable)
    db.commit()
    db.refresh(timetable)

    return TimetableImportResult(
        timetable=TimetableDetail.model_validate(timetable),
        warnings=parsed.warnings,
    )


@router.get("/active", response_model=TimetableDetail)
def get_active_timetable(
    db: Annotated[Session, Depends(get_db)],
) -> TimetableDetail:
    return TimetableDetail.model_validate(_get_active_timetable_or_404(db))


@router.get("/dashboard", response_model=TimetableDashboard)
def get_dashboard(
    db: Annotated[Session, Depends(get_db)],
    date_: Annotated[
        date | None, Query(alias="date", description="看板日期，默认今天")
    ] = None,
    timetable_id: Annotated[
        int | None, Query(ge=1, description="不传则使用当前激活课表")
    ] = None,
) -> TimetableDashboard:
    target_date = date_ or date.today()
    timetable = (
        _get_timetable_or_404(db, timetable_id)
        if timetable_id is not None
        else _get_active_timetable_or_404(db)
    )

    week_start_date = target_date - timedelta(days=target_date.weekday())
    week_end_date = week_start_date + timedelta(days=6)

    current_week: int | None = None
    if timetable.semester_start_date is not None:
        current_week = max(
            0, (target_date - timetable.semester_start_date).days // 7 + 1
        )

    courses_by_day: dict[int, list[CourseSessionRead]] = {
        weekday: [] for weekday in range(1, 8)
    }
    for course in timetable.sessions:
        if current_week is not None:
            if current_week < 1:
                continue
            if course.week_start is not None and current_week < course.week_start:
                continue
            if course.week_end is not None and current_week > course.week_end:
                continue
        courses_by_day[course.weekday].append(CourseSessionRead.model_validate(course))

    days = [
        DashboardDay(
            weekday=weekday,
            weekday_name=WEEKDAY_NAMES[weekday - 1],
            date=week_start_date + timedelta(days=weekday - 1),
            courses=courses_by_day[weekday],
        )
        for weekday in range(1, 8)
    ]

    return TimetableDashboard(
        timetable=TimetableSummary.model_validate(timetable),
        date=target_date,
        week_start_date=week_start_date,
        week_end_date=week_end_date,
        current_week=current_week,
        days=days,
    )


@router.get("/{timetable_id}", response_model=TimetableDetail)
def get_timetable(
    timetable_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> TimetableDetail:
    return TimetableDetail.model_validate(_get_timetable_or_404(db, timetable_id))


@router.patch("/{timetable_id}", response_model=TimetableDetail)
def update_timetable(
    timetable_id: int,
    payload: TimetableUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> TimetableDetail:
    timetable = _get_timetable_or_404(db, timetable_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(timetable, field, value)

    db.commit()
    db.refresh(timetable)
    return TimetableDetail.model_validate(timetable)


@router.post("/{timetable_id}/activate", response_model=TimetableDetail)
def activate_timetable(
    timetable_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> TimetableDetail:
    timetable = _get_timetable_or_404(db, timetable_id)
    db.execute(update(Timetable).values(active=False))
    timetable.active = True
    db.commit()
    db.refresh(timetable)
    return TimetableDetail.model_validate(timetable)


@router.delete("/{timetable_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_timetable(
    timetable_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    timetable = _get_timetable_or_404(db, timetable_id)
    db.delete(timetable)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
