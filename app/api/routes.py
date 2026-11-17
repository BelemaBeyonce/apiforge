from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Path, Query, Response
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Evaluation, Task, TaskAccess, User
from app.schemas import (
    EvaluationPage,
    EvaluationRead,
    StrictModel,
    Submission,
    TaskInput,
    TaskPage,
    TaskRead,
    TaskUpdate,
)
from app.security import current_user
from app.services.tasks import (
    archive_task,
    require_evaluation,
    require_task,
    save_task,
    submit,
    visibility,
)

router = APIRouter()
Actor = Annotated[User, Depends(current_user)]
DB = Annotated[Session, Depends(get_db)]
PositiveId = Annotated[int, Path(ge=1)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get("/health", tags=["operations"])
def health(db: DB):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.post("/tasks", response_model=TaskRead, status_code=201, tags=["tasks"])
def create_task(data: TaskInput, db: DB, actor: Actor):
    return save_task(db, data, actor)


@router.get("/tasks", response_model=TaskPage, tags=["tasks"])
def list_tasks(
    db: DB,
    actor: Actor,
    include_archived: bool = False,
    limit: Limit = 20,
    offset: Offset = 0,
    language: Annotated[str | None, Query(max_length=40)] = None,
    difficulty: Literal["easy", "medium", "hard"] | None = None,
):
    filters = [visibility(actor)]
    if not include_archived:
        filters.append(Task.archived_at.is_(None))
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
def get_task(task_id: PositiveId, db: DB, actor: Actor, include_archived: bool = False):
    return require_task(db, task_id, actor, archived=include_archived)


@router.put("/tasks/{task_id}", response_model=TaskRead, tags=["tasks"])
def replace_task(task_id: PositiveId, data: TaskUpdate, db: DB, actor: Actor):
    return save_task(
        db,
        TaskInput(**data.model_dump(exclude={"expected_revision"})),
        actor,
        require_task(db, task_id, actor, write=True),
        data.expected_revision,
    )


@router.delete("/tasks/{task_id}", status_code=204, tags=["tasks"])
def delete_task(
    task_id: PositiveId,
    db: DB,
    actor: Actor,
    revision: Annotated[int, Header(alias="If-Match", ge=1)],
):
    archive_task(db, task_id, actor, revision)
    return Response(status_code=204)


@router.post(
    "/tasks/{task_id}/evaluations",
    response_model=EvaluationRead,
    status_code=201,
    tags=["evaluations"],
)
def create_evaluation(task_id: PositiveId, data: Submission, db: DB, actor: Actor):
    return submit(db, task_id, data.response, actor)


@router.get("/tasks/{task_id}/evaluations", response_model=EvaluationPage, tags=["evaluations"])
def list_evaluations(
    task_id: PositiveId, db: DB, actor: Actor, limit: Limit = 20, offset: Offset = 0
):
    require_task(db, task_id, actor, archived=True)
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
def get_evaluation(evaluation_id: PositiveId, db: DB, actor: Actor):
    return require_evaluation(db, evaluation_id, actor)


class AccessInput(StrictModel):
    permission: Literal["reader", "editor"]


@router.put("/tasks/{task_id}/access/{user_id}", tags=["access"])
def grant_access(task_id: PositiveId, user_id: int, data: AccessInput, db: DB, actor: Actor):
    from fastapi import HTTPException

    task = require_task(db, task_id, actor, write=True)
    if actor.role != "admin" and task.owner_id != actor.id:
        raise HTTPException(403, "Only the owner or admin may grant access")
    if db.get(User, user_id) is None:
        raise HTTPException(404, "User not found")
    access = db.scalar(
        select(TaskAccess).where(TaskAccess.task_id == task_id, TaskAccess.user_id == user_id)
    )
    if access is None:
        access = TaskAccess(task_id=task_id, user_id=user_id, permission=data.permission)
        db.add(access)
    access.permission = data.permission
    db.commit()
    return {"user_id": user_id, "permission": access.permission}


@router.delete("/tasks/{task_id}/access/{user_id}", status_code=204, tags=["access"])
def revoke_access(task_id: PositiveId, user_id: int, db: DB, actor: Actor):
    from fastapi import HTTPException

    task = require_task(db, task_id, actor, write=True)
    if actor.role != "admin" and task.owner_id != actor.id:
        raise HTTPException(403, "Only the owner or admin may revoke access")
    access = db.scalar(
        select(TaskAccess).where(TaskAccess.task_id == task_id, TaskAccess.user_id == user_id)
    )
    if access is not None:
        db.delete(access)
        db.commit()
    return Response(status_code=204)


@router.get("/evaluations/{evaluation_id}/compare/{other_id}", tags=["evaluations"])
def compare_evaluations(evaluation_id: PositiveId, other_id: int, db: DB, actor: Actor):
    left = require_evaluation(db, evaluation_id, actor)
    right = require_evaluation(db, other_id, actor)
    return {
        "left_id": left.id,
        "right_id": right.id,
        "left_score": left.score,
        "right_score": right.score,
        "score_delta": round(right.score - left.score, 2),
        "same_task": left.task_id == right.task_id,
        "same_rubric": left.task_snapshot == right.task_snapshot,
        "same_engine": left.engine_version == right.engine_version,
        "left_feedback": left.feedback,
        "right_feedback": right.feedback,
        "warning": "Scores across different rubrics or engines are not directly comparable",
    }
