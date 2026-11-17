import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from alembic.config import Config

from app.config import settings
from app.middleware import RequestLimits
from app.models import Task, User
from app.schemas import TaskInput
from app.services.tasks import save_task


def test_real_concurrent_updates(client, task_data):
    task = client.post("/api/v1/tasks", json=task_data).json()
    barrier = Barrier(2)

    def update_task(title):
        with client.factory() as db:
            actor = db.get(User, client.admin_id)
            stale = db.get(Task, task["id"])
            assert stale.revision == 1
            barrier.wait(timeout=10)
            try:
                return save_task(
                    db, TaskInput(**{**task_data, "title": title}), actor, stale, 1
                ).revision
            except Exception as exc:
                if getattr(exc, "status_code", None) == 409:
                    return "conflict"
                raise

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(update_task, ["first", "second"]))
    assert sorted(map(str, results)) == ["2", "conflict"]


def test_liveness_readiness_and_body_limits(client, monkeypatch):
    assert client.get("/api/v1/live").json() == {"status": "alive"}
    assert client.get("/api/v1/ready").status_code == 503  # fixture has no migration stamp
    # Set a proper migration stamp on this otherwise current fixture schema.
    with client.factory() as db:
        from alembic.script import ScriptDirectory
        from sqlalchemy import text

        head = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
        db.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)"))
        db.execute(text("INSERT INTO alembic_version VALUES (:head)"), {"head": head})
        db.commit()
    assert client.get("/api/v1/ready").status_code == 200
    with client.factory() as db:
        from sqlalchemy import text

        db.execute(text("UPDATE alembic_version SET version_num='0001'"))
        db.commit()
    assert client.get("/api/v1/ready").status_code == 503
    monkeypatch.setattr(settings, "max_request_bytes", 1024)
    result = client.post("/api/v1/tasks", content=b"x" * 1025)
    assert result.status_code == 413
    assert result.json()["error"]["request_id"] == result.headers["X-Request-ID"]


def test_request_limits_without_content_length(monkeypatch):
    called = []

    async def target(scope, receive, send):
        called.append(scope["type"])

    async def run(headers, messages):
        sent = []
        iterator = iter(messages)

        async def receive():
            return next(iterator)

        async def send(message):
            sent.append(message)

        await RequestLimits(target)({"type": "http", "headers": headers}, receive, send)
        return sent

    monkeypatch.setattr(settings, "max_request_bytes", 1024)
    sent = asyncio.run(run([], [{"type": "http.request", "body": b"x" * 1025, "more_body": False}]))
    assert sent[0]["status"] == 413
    for bad in [b"-1", b"not-a-number"]:
        sent = asyncio.run(run([(b"content-length", bad)], []))
        assert sent[0]["status"] == 400
    assert asyncio.run(run([], [{"type": "http.disconnect"}])) == []

    async def ws():
        await RequestLimits(target)({"type": "websocket"}, None, None)

    asyncio.run(ws())
    assert called == ["websocket"]


def test_cors_is_explicit(client):
    response = client.options(
        "/api/v1/tasks",
        headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in response.headers
