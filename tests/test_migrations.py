from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.config import settings
from app.database import build_engine
from app.schemas import TaskInput
from app.services.tasks import save_task, submit


def test_migration_roundtrip(tmp_path, monkeypatch, task_data):
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setattr(settings, "database_url", url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.check(config)
    engine = build_engine(url)
    with Session(engine) as db:
        task = save_task(db, TaskInput(**task_data))
        assert submit(db, task.id, "sorted stable").score == 100
    assert {"tasks", "evaluations"} <= set(inspect(engine).get_table_names())
    engine.dispose()
    command.downgrade(config, "base")
    engine = build_engine(url)
    assert "tasks" not in inspect(engine).get_table_names()
    engine.dispose()
    command.upgrade(config, "head")
