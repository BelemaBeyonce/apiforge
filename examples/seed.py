"""Explicit, idempotent sample data loading; migrate before invoking."""

import json
from pathlib import Path

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Task, User
from app.schemas import TaskInput
from app.services.tasks import save_task


def main():
    samples = json.loads(Path(__file__).with_name("tasks.json").read_text())
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.role == "admin", User.is_active.is_(True)))
        if admin is None:
            raise SystemExit("Run python -m app.bootstrap first")
        for data in samples:
            if db.scalar(select(Task.id).where(Task.title == data["title"])) is None:
                task = save_task(db, TaskInput(**data), admin)
                print(f"Created task {task.id}: {task.title}")


if __name__ == "__main__":
    main()
