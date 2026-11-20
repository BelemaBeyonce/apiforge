import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.database import Base, build_engine, get_db
from app.main import app
from app.models import User
from app.security import hash_password, issue_token


@pytest.fixture
def client(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def override():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override

    try:
        with factory() as session:
            admin = User(
                email="admin@example.com",
                password_hash=hash_password("TestPassword123!"),
                role="admin",
                is_active=True,
            )
            session.add(admin)
            session.commit()
            session.refresh(admin)
            token = issue_token(admin)

        with TestClient(app) as test_client:
            test_client.headers.update({"Authorization": f"Bearer {token}"})

            response = test_client.get("/api/v1/auth/me")
            print("\nAUTH STATUS:", response.status_code)
            print("AUTH RESPONSE:", response.text)

            yield test_client
    finally:
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
