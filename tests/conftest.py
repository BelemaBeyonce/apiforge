import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.database import Base, build_engine, get_db
from app.main import app


@pytest.fixture
def client(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def override():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    engine.dispose()


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
