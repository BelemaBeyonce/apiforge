import pytest
from sqlalchemy.exc import OperationalError

from app.database import get_db
from app.main import app

ROOT = "/api/v1"


def create(client, data):
    response = client.post(ROOT + "/tasks", json=data)
    assert response.status_code == 201, response.text
    return response.json()


def test_crud_and_filtering(client, task_data):
    a = create(client, task_data)
    b = create(client, dict(task_data, language="javascript", difficulty="hard"))
    assert client.get(f"{ROOT}/tasks/{a['id']}").json()["title"] == task_data["title"]
    page = client.get(ROOT + "/tasks?limit=1&offset=1").json()
    assert page["total"] == 2 and page["items"][0]["id"] == b["id"]
    assert client.get(ROOT + "/tasks?language=python&difficulty=easy").json()["total"] == 1
    assert client.get(ROOT + "/tasks?offset=100").json()["items"] == []
    updated = client.put(
        f"{ROOT}/tasks/{a['id']}", json=dict(task_data, title="Revised", expected_revision=1)
    )
    assert updated.status_code == 200
    assert updated.json()["revision"] == 2
    assert client.delete(f"{ROOT}/tasks/{a['id']}", headers={"If-Match": "2"}).status_code == 204
    assert client.get(f"{ROOT}/tasks/{a['id']}").status_code == 404


def test_evaluation_history_snapshot_and_archive(client, task_data):
    task = create(client, task_data)
    url = f"{ROOT}/tasks/{task['id']}"
    result = client.post(url + "/evaluations", json={"response": "use sorted"})
    assert result.status_code == 201
    evaluation = result.json()
    assert evaluation["score"] == 66.67
    assert evaluation["feedback"][1]["passed"] is False
    assert evaluation["created_at"]
    client.put(url, json=dict(task_data, title="Changed", expected_revision=1))
    stored = client.get(f"{ROOT}/evaluations/{evaluation['id']}").json()
    assert stored["task_snapshot"]["title"] == "Explain sorting"
    assert stored["task_snapshot"]["revision"] == 1
    assert client.get(url + "/evaluations?limit=1").json()["total"] == 1
    client.delete(url, headers={"If-Match": "2"})
    assert client.get(f"{ROOT}/evaluations/{evaluation['id']}").status_code == 200


@pytest.mark.parametrize(
    "patch",
    [
        {"title": " "},
        {"language": "Python"},
        {"difficulty": "extreme"},
        {"criteria": []},
        {"criteria": [{"name": "x", "kind": "invalid", "reference": "x"}]},
        {"criteria": [{"name": "x", "kind": "exact", "reference": "x", "weight": 0}]},
        {"title": "x" * 201},
        {"extra": "unknown"},
        {"description": None},
    ],
)
def test_invalid_tasks(client, task_data, patch):
    response = client.post(ROOT + "/tasks", json=dict(task_data, **patch))
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "validation_error"
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert all("input" not in detail for detail in body["details"])


def test_duplicate_criteria(client, task_data):
    task_data["criteria"] *= 2
    assert client.post(ROOT + "/tasks", json=task_data).status_code == 422


@pytest.mark.parametrize(
    "query", ["limit=0", "limit=101", "offset=-1", "difficulty=extreme", "limit=abc"]
)
def test_bad_pagination(client, query):
    assert client.get(ROOT + "/tasks?" + query).status_code == 422


@pytest.mark.parametrize(
    "body", [{}, {"response": " "}, {"response": "x" * 50001}, {"response": "x", "code": "x"}]
)
def test_bad_submission(client, task_data, body):
    task = create(client, task_data)
    assert client.post(f"{ROOT}/tasks/{task['id']}/evaluations", json=body).status_code == 422


def test_missing_and_invalid_ids(client, task_data):
    for method, path, body in [
        ("GET", "/tasks/999", None),
        ("PUT", "/tasks/999", dict(task_data, expected_revision=1)),
        ("DELETE", "/tasks/999", None),
        ("POST", "/tasks/999/evaluations", {"response": "x"}),
        ("GET", "/tasks/999/evaluations", None),
        ("GET", "/evaluations/999", None),
    ]:
        assert (
            client.request(method, ROOT + path, json=body, headers={"If-Match": "1"}).status_code
            == 404
        )
    assert client.get(ROOT + "/tasks/0").status_code == 422
    assert client.get(ROOT + "/tasks/nope").status_code == 422


def test_health_docs_and_malformed_json(client):
    assert client.get(ROOT + "/health").json() == {"status": "ok"}
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").json()["info"]["version"] == "0.2.0"
    response = client.post(
        ROOT + "/tasks", content="{", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert client.get("/missing").json()["error"]["code"] == "http_error"


def test_database_failure_is_sanitized(client):
    def broken():
        raise OperationalError("secret sql", {}, Exception("password"))
        yield

    app.dependency_overrides[get_db] = broken
    response = client.get(ROOT + "/health")
    assert response.status_code == 503
    assert "password" not in response.text


def test_unexpected_failure_is_sanitized(client):
    def broken():
        raise RuntimeError("sensitive detail")
        yield

    app.dependency_overrides[get_db] = broken
    response = client.get(ROOT + "/health")
    assert response.status_code == 500
    assert "sensitive" not in response.text
