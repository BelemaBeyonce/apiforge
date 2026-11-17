import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.database import Base, build_engine, get_db
from app.main import app
from app.models import User
from app.security import hash_password, issue_token, limiter, rate_keys


@pytest.fixture
def client(tmp_path):
    postgres_url = os.environ.get("APIFORGE_TEST_DATABASE_URL")
    schema = "test_" + uuid4().hex
    parent_engine = None
    if postgres_url:
        if not postgres_url.startswith("postgresql+psycopg://"):
            raise ValueError("Integration test URL must use PostgreSQL/Psycopg")
        parent_engine = build_engine(postgres_url)
        with parent_engine.begin() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        url = make_url(postgres_url).update_query_dict({"options": f"-csearch_path={schema}"})
        engine = build_engine(url.render_as_string(hide_password=False))
    else:
        engine = build_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def override():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override
    limiter.storage.reset()
    rate_keys.clear()
    with factory() as db:
        admin = User(
            email="admin@example.com",
            password_hash=hash_password("test-admin-password"),
            role="admin",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        token = issue_token(admin)
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer " + token
        client.factory = factory
        client.admin_id = admin.id
        yield client
    app.dependency_overrides.clear()
    engine.dispose()
    if parent_engine:
        with parent_engine.begin() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        parent_engine.dispose()


@pytest.fixture
def task_data():
    return {
        "title": "Explain sorting",
        "description": "Describe Python sorting",
        "language": "python",
        "difficulty": "easy",
        "expected_outcome": "Mention sorted and stability",
        "criteria": [
            {"name": "sorted", "kind": "contains", "reference": "sorted", "weight": 2},
            {"name": "stability", "kind": "contains", "reference": "stable", "weight": 1},
        ],
    }
