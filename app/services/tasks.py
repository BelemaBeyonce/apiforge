from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Evaluation, Task
from app.schemas import Criterion, TaskInput
from app.services.evaluator import ENGINE_VERSION, evaluate


def require_task(db: Session, task_id: int):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    return task


def save_task(db: Session, data: TaskInput, task: Task | None = None):
    if task is None:
        task = Task(**data.model_dump())
    else:
        for key, value in data.model_dump().items():
            setattr(task, key, value)
        task.revision += 1
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def submit(db: Session, task_id: int, response: str):
    task = require_task(db, task_id)
    criteria = [Criterion.model_validate(c) for c in task.criteria]
    score, feedback = evaluate(response, criteria)
    snapshot = TaskInput.model_validate(
        {key: getattr(task, key) for key in TaskInput.model_fields}
    ).model_dump()
    snapshot["revision"] = task.revision
    result = Evaluation(
        task_id=task_id,
        response=response,
        score=score,
        feedback=feedback,
        task_snapshot=snapshot,
        engine_version=ENGINE_VERSION,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result
