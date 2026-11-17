from fastapi import HTTPException
from sqlalchemy import exists, or_, select, update
from sqlalchemy.orm import Session

from app.models import Evaluation, Task, TaskAccess, User, utcnow
from app.schemas import Criterion, RubricCategory, TaskInput
from app.services.evaluator import ENGINE_VERSION, evaluate


def visibility(user: User):
    if user.role == "admin":
        return True
    return or_(
        Task.owner_id == user.id,
        exists().where(TaskAccess.task_id == Task.id, TaskAccess.user_id == user.id),
    )


def require_task(
    db: Session, task_id: int, actor: User, *, write: bool = False, archived: bool = False
) -> Task:
    task = db.scalar(select(Task).where(Task.id == task_id, visibility(actor)))
    if task is None or (task.archived_at is not None and not archived):
        raise HTTPException(404, "Task not found")
    if write:
        if actor.role not in {"admin", "evaluator"}:
            raise HTTPException(403, "Evaluator role required")
        if actor.role != "admin" and task.owner_id != actor.id:
            permission = db.scalar(
                select(TaskAccess.permission).where(
                    TaskAccess.task_id == task_id, TaskAccess.user_id == actor.id
                )
            )
            if permission != "editor":
                raise HTTPException(403, "Task editor access required")
    return task


def save_task(
    db: Session,
    data: TaskInput,
    actor: User,
    task: Task | None = None,
    expected_revision: int | None = None,
) -> Task:
    if actor.role not in {"admin", "evaluator"}:
        raise HTTPException(403, "Evaluator role required")
    values = data.model_dump()
    if task is None:
        task = Task(**values, owner_id=actor.id)
        db.add(task)
    else:
        require_task(db, task.id, actor, write=True)
        result = db.execute(
            update(Task)
            .where(
                Task.id == task.id, Task.revision == expected_revision, Task.archived_at.is_(None)
            )
            .values(**values, revision=Task.revision + 1, updated_at=utcnow())
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            db.rollback()
            raise HTTPException(409, "Task revision conflict; reload before updating")
    db.commit()
    db.refresh(task)
    return task


def archive_task(db: Session, task_id: int, actor: User, revision: int) -> None:
    require_task(db, task_id, actor, write=True)
    result = db.execute(
        update(Task)
        .where(Task.id == task_id, Task.revision == revision, Task.archived_at.is_(None))
        .values(archived_at=utcnow(), revision=Task.revision + 1)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Task revision conflict; reload before archiving")
    db.commit()


def require_evaluation(db: Session, evaluation_id: int, actor: User) -> Evaluation:
    result = db.get(Evaluation, evaluation_id)
    if result is None:
        raise HTTPException(404, "Evaluation not found")
    require_task(db, result.task_id, actor, archived=True)
    return result


def submit(db: Session, task_id: int, response: str, actor: User) -> Evaluation:
    task = require_task(db, task_id, actor, write=True)
    criteria = [Criterion.model_validate(c) for c in task.criteria]
    score, feedback = evaluate(
        response, criteria, [RubricCategory.model_validate(c) for c in task.categories]
    )
    snapshot = TaskInput.model_validate(
        {key: getattr(task, key) for key in TaskInput.model_fields}
    ).model_dump()
    snapshot["revision"] = task.revision
    result = Evaluation(
        task_id=task_id,
        author_id=actor.id,
        response=response,
        score=score,
        feedback=feedback,
        task_snapshot=snapshot,
        engine_version=ENGINE_VERSION,
        status="completed_with_limits"
        if any(f["reason"] == "regex_time_limit" for f in feedback)
        else "completed",
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result
