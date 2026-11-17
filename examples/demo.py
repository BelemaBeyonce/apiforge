"""Repeatable demo that exercises a real migrated database through the API."""

import argparse

import httpx

TASK = {
    "title": "Interview demo: output prediction",
    "description": "Predict sum([1, 2, 3]).",
    "language": "python",
    "difficulty": "easy",
    "expected_outcome": "6",
    "criteria": [{"name": "output", "kind": "exact", "reference": "6", "weight": 1}],
}


def demo(client):
    response = client.post("/api/v1/tasks", json=TASK)
    response.raise_for_status()
    task = response.json()
    url = f"/api/v1/tasks/{task['id']}"
    try:
        for answer, expected in [("6", 100), ("7", 0)]:
            result = client.post(url + "/evaluations", json={"response": answer})
            result.raise_for_status()
            assert result.json()["score"] == expected
            print(f"Response {answer!r}: score={result.json()['score']}")
        result = client.get(url + "/evaluations")
        result.raise_for_status()
        assert result.json()["total"] == 2
        revised = client.put(url, json={**TASK, "title": "Revised interview demo"})
        revised.raise_for_status()
        assert revised.json()["revision"] == 2
        stored = client.get(f"/api/v1/evaluations/{result.json()['items'][0]['id']}")
        stored.raise_for_status()
        assert stored.json()["task_snapshot"]["revision"] == 1
        page = client.get(
            "/api/v1/tasks", params={"language": "python", "difficulty": "easy", "limit": 1}
        )
        page.raise_for_status()
        assert page.json()["total"] >= 1
        invalid = client.post(url + "/evaluations", json={"response": ""})
        assert invalid.status_code == 422
        print("History persisted; invalid response rejected with 422.")
    finally:
        client.delete(url).raise_for_status()
    assert client.get(url).status_code == 404
    assert client.get(f"/api/v1/evaluations/{stored.json()['id']}").status_code == 404
    print("Task replacement, snapshots, filtering, and cascade deletion verified.")
    print("Demo task and its evaluations cleaned up.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--in-process", action="store_true")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    if args.in_process:
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app) as client:
            demo(client)
    else:
        with httpx.Client(base_url=args.url, timeout=10) as client:
            demo(client)
