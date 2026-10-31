from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Todo
from app.schemas.common import Page
from app.schemas.todo import TodoCreate, TodoPriority, TodoRead, TodoStatus, TodoUpdate
from app.utils import normalize_utc, utcnow

router = APIRouter(prefix="/todos", tags=["TodoList"])


def _get_todo_or_404(db: Session, todo_id: int) -> Todo:
    todo = db.get(Todo, todo_id)
    if todo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )
    return todo


@router.get("", response_model=Page[TodoRead])
def list_todos(
    db: Annotated[Session, Depends(get_db)],
    status_filter: Annotated[
        list[TodoStatus] | None,
        Query(alias="status", description="Repeat to filter by multiple statuses"),
    ] = None,
    priority_filter: Annotated[
        list[TodoPriority] | None,
        Query(alias="priority", description="Repeat to filter by multiple priorities"),
    ] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    due_from: Annotated[datetime | None, Query()] = None,
    due_to: Annotated[datetime | None, Query()] = None,
    sort_by: Annotated[
        Literal["created_at", "updated_at", "due_at"], Query()
    ] = "created_at",
    sort_order: Annotated[Literal["asc", "desc"], Query()] = "desc",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[TodoRead]:
    due_from = normalize_utc(due_from) if due_from is not None else None
    due_to = normalize_utc(due_to) if due_to is not None else None
    if due_from is not None and due_to is not None and due_from > due_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="due_from must be earlier than or equal to due_to",
        )

    conditions = []
    if status_filter:
        conditions.append(Todo.status.in_(status_filter))
    if priority_filter:
        conditions.append(Todo.priority.in_(priority_filter))
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(Todo.title.ilike(pattern), Todo.description.ilike(pattern))
        )
    if due_from is not None:
        conditions.append(Todo.due_at >= due_from)
    if due_to is not None:
        conditions.append(Todo.due_at <= due_to)

    total = db.scalar(select(func.count(Todo.id)).where(*conditions)) or 0

    sort_column = getattr(Todo, sort_by)
    order = sort_column.asc() if sort_order == "asc" else sort_column.desc()
    if sort_by == "due_at":
        order = order.nulls_last()

    items = db.scalars(
        select(Todo)
        .where(*conditions)
        .order_by(order, Todo.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    return Page[TodoRead](
        items=[TodoRead.model_validate(todo) for todo in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=TodoRead, status_code=status.HTTP_201_CREATED)
def create_todo(
    payload: TodoCreate,
    db: Annotated[Session, Depends(get_db)],
) -> TodoRead:
    values = payload.model_dump()
    if values["status"] == "completed":
        values["completed_at"] = utcnow()

    todo = Todo(**values)
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return TodoRead.model_validate(todo)


@router.get("/{todo_id}", response_model=TodoRead)
def get_todo(
    todo_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> TodoRead:
    return TodoRead.model_validate(_get_todo_or_404(db, todo_id))


@router.patch("/{todo_id}", response_model=TodoRead)
def update_todo(
    todo_id: int,
    payload: TodoUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> TodoRead:
    todo = _get_todo_or_404(db, todo_id)
    values = payload.model_dump(exclude_unset=True)

    if "status" in values:
        new_status = values["status"]
        if new_status == "completed" and todo.status != "completed":
            values["completed_at"] = utcnow()
        elif new_status != "completed":
            values["completed_at"] = None

    for field, value in values.items():
        setattr(todo, field, value)

    db.commit()
    db.refresh(todo)
    return TodoRead.model_validate(todo)


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(
    todo_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    todo = _get_todo_or_404(db, todo_id)
    db.delete(todo)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
