"""Explicit, idempotent sample data loading; migrate before invoking."""

import json
from pathlib import Path

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Task
from app.schemas import TaskInput
from app.services.tasks import save_task


def main():
    samples = json.loads(Path(__file__).with_name("tasks.json").read_text())
    with SessionLocal() as db:
        for data in samples:
            if db.scalar(select(Task.id).where(Task.title == data["title"])) is None:
                task = save_task(db, TaskInput(**data))
                print(f"Created task {task.id}: {task.title}")


if __name__ == "__main__":
    main()
