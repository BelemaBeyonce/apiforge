import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url

from app.config import settings
from app.database import build_engine


@pytest.mark.parametrize(
    "backend", ["sqlite"] + (["postgresql"] if os.environ.get("APIFORGE_TEST_DATABASE_URL") else [])
)
def test_migration_preserves_legacy_history(tmp_path, monkeypatch, backend):
    parent = None
    schema = "migration_" + uuid4().hex
    if backend == "postgresql":
        base_url = os.environ["APIFORGE_TEST_DATABASE_URL"]
        parent = build_engine(base_url)
        with parent.begin() as db:
            db.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        url = (
            make_url(base_url)
            .update_query_dict({"options": f"-csearch_path={schema}"})
            .render_as_string(hide_password=False)
        )
    else:
        url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setattr(settings, "database_url", url)
    config = Config("alembic.ini")
    command.upgrade(config, "0001")
    engine = build_engine(url)
    with engine.begin() as db:
        db.execute(
            text(
                "INSERT INTO tasks (title,description,language,difficulty,expected_outcome,criteria,revision,created_at,updated_at) VALUES ('legacy','desc','python','easy','6','[]',1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"
            )
        )
        db.execute(
            text(
                "INSERT INTO evaluations (task_id,response,score,feedback,task_snapshot,engine_version,created_at) VALUES (1,'6',100,'[]','{}','deterministic-v1',CURRENT_TIMESTAMP)"
            )
        )
    engine.dispose()
    command.upgrade(config, "head")
    command.check(config)
    engine = build_engine(url)
    with engine.connect() as db:
        assert db.scalar(text("SELECT title FROM tasks WHERE id=1")) == "legacy"
        assert db.scalar(text("SELECT score FROM evaluations WHERE id=1")) == 100
        assert db.scalar(text("SELECT owner_id FROM tasks WHERE id=1")) is None
        assert (
            db.scalar(text("SELECT engine_version FROM evaluations WHERE id=1"))
            == "deterministic-v1"
        )
        assert db.scalar(text("SELECT status FROM evaluations WHERE id=1")) == "completed"
        if backend == "sqlite":
            assert db.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
    assert {"users", "task_access", "tasks", "evaluations", "ai_evaluations"} <= set(
        inspect(engine).get_table_names()
    )
    engine.dispose()
    if parent:
        with parent.begin() as db:
            db.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        parent.dispose()
