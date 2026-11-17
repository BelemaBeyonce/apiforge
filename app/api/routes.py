from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Evaluation, Task
from app.schemas import EvaluationPage, EvaluationRead, Submission, TaskInput, TaskPage, TaskRead
from app.services.tasks import require_task, save_task, submit

router = APIRouter()
DB = Annotated[Session, Depends(get_db)]
PositiveId = Annotated[int, Path(ge=1)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get("/health", tags=["operations"])
def health(db: DB):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.post("/tasks", response_model=TaskRead, status_code=201, tags=["tasks"])
def create_task(data: TaskInput, db: DB):
    return save_task(db, data)


@router.get("/tasks", response_model=TaskPage, tags=["tasks"])
def list_tasks(
    db: DB,
    limit: Limit = 20,
    offset: Offset = 0,
    language: Annotated[str | None, Query(max_length=40)] = None,
    difficulty: Literal["easy", "medium", "hard"] | None = None,
):
    filters = []
    if language is not None:
        filters.append(Task.language == language)
    if difficulty is not None:
        filters.append(Task.difficulty == difficulty)
    total = db.scalar(select(func.count()).select_from(Task).where(*filters))
    items = db.scalars(
        select(Task).where(*filters).order_by(Task.id).limit(limit).offset(offset)
    ).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/tasks/{task_id}", response_model=TaskRead, tags=["tasks"])
def get_task(task_id: PositiveId, db: DB):
    return require_task(db, task_id)


@router.put("/tasks/{task_id}", response_model=TaskRead, tags=["tasks"])
def replace_task(task_id: PositiveId, data: TaskInput, db: DB):
    return save_task(db, data, require_task(db, task_id))


@router.delete("/tasks/{task_id}", status_code=204, tags=["tasks"])
def delete_task(task_id: PositiveId, db: DB):
    db.delete(require_task(db, task_id))
    db.commit()
    return Response(status_code=204)


@router.post(
    "/tasks/{task_id}/evaluations",
    response_model=EvaluationRead,
    status_code=201,
    tags=["evaluations"],
)
def create_evaluation(task_id: PositiveId, data: Submission, db: DB):
    return submit(db, task_id, data.response)


@router.get("/tasks/{task_id}/evaluations", response_model=EvaluationPage, tags=["evaluations"])
def list_evaluations(task_id: PositiveId, db: DB, limit: Limit = 20, offset: Offset = 0):
    require_task(db, task_id)
    total = db.scalar(
        select(func.count()).select_from(Evaluation).where(Evaluation.task_id == task_id)
    )
    items = db.scalars(
        select(Evaluation)
        .where(Evaluation.task_id == task_id)
        .order_by(Evaluation.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationRead, tags=["evaluations"])
def get_evaluation(evaluation_id: PositiveId, db: DB):
    result = db.get(Evaluation, evaluation_id)
    if result is None:
        raise HTTPException(404, "Evaluation not found")
    return result
