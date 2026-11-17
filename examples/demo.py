"""Run a synthetic, isolated end-to-end demo; no paid key or existing admin required."""

import argparse
import os
import tempfile


def run(client, email, password):
    from examples.tasks_data import TASK

    def login(address, secret):
        response = client.post("/api/v1/auth/login", json={"email": address, "password": secret})
        response.raise_for_status()
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    admin = login(email, password)
    import secrets

    suffix = secrets.token_hex(4)
    accounts = {}
    for name, role in [("owner", "evaluator"), ("viewer", "viewer"), ("reviewer", "evaluator")]:
        address = f"{name}-{suffix}@example.com"
        secret = secrets.token_urlsafe(20)
        response = client.post("/api/v1/auth/register", json={"email": address, "password": secret})
        response.raise_for_status()
        user_id = response.json()["id"]
        if role != "viewer":
            client.put(
                f"/api/v1/users/{user_id}", json={"role": role}, headers=admin
            ).raise_for_status()
        accounts[name] = (user_id, login(address, secret))
    owner = accounts["owner"][1]
    response = client.post("/api/v1/tasks", json=TASK, headers=owner)
    response.raise_for_status()
    task = response.json()
    url = f"/api/v1/tasks/{task['id']}"
    assert client.get(url, headers=accounts["viewer"][1]).status_code == 404
    results = []
    for answer, expected in [("Use sorted for stable ordering.", 100), ("Use sorted.", 75)]:
        response = client.post(url + "/evaluations", json={"response": answer}, headers=owner)
        response.raise_for_status()
        evaluation = response.json()
        assert evaluation["score"] == expected
        results.append(evaluation)
        print(f"Deterministic score: {evaluation['score']}")
    viewer_id, viewer = accounts["viewer"]
    client.put(
        f"{url}/access/{viewer_id}", json={"permission": "reader"}, headers=owner
    ).raise_for_status()
    assert client.get(url + "/evaluations", headers=viewer).json()["total"] == 2
    assert (
        client.post(url + "/evaluations", json={"response": "sorted"}, headers=viewer).status_code
        == 403
    )
    replacement = {**TASK, "title": "Updated rubric example", "expected_revision": 1}
    client.put(url, json=replacement, headers=owner).raise_for_status()
    assert client.put(url, json=replacement, headers=owner).status_code == 409
    assert (
        client.post(url + "/evaluations", json={"response": ""}, headers=owner).status_code == 422
    )
    comparison = client.get(
        f"/api/v1/evaluations/{results[0]['id']}/compare/{results[1]['id']}", headers=owner
    )
    comparison.raise_for_status()
    assert comparison.json()["score_delta"] == -25
    print("JWT login, RBAC, history, revision conflict and evaluation comparison verified.")
    ai_url = f"/api/v1/evaluations/{results[0]['id']}/ai"
    advice = client.post(ai_url, json={}, headers=owner)
    if advice.status_code == 201:
        ai = advice.json()
        reviewer_id, reviewer = accounts["reviewer"]
        client.put(
            f"{url}/access/{reviewer_id}", json={"permission": "editor"}, headers=owner
        ).raise_for_status()
        reviewed = client.post(
            f"/api/v1/ai-evaluations/{ai['id']}/review",
            json={
                "decision": "accepted",
                "note": "Synthetic demo: contract reviewed, not evidence of correctness",
            },
            headers=reviewer,
        )
        reviewed.raise_for_status()
        print(
            f"AI provider: {ai['provider']}; advisory feedback reviewed by a different evaluator."
        )
    elif advice.status_code in {403, 503}:
        print("AI is disabled or requires external consent; deterministic demo remains complete.")
    else:
        advice.raise_for_status()
    client.delete(url, headers={**owner, "If-Match": "2"}).raise_for_status()
    assert client.get(url, headers=owner).status_code == 404
    assert client.get(f"/api/v1/evaluations/{results[0]['id']}", headers=owner).status_code == 200
    print("Task archived; historical evaluations preserved. No submitted code executed.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--in-process",
        action="store_true",
        help="Default: isolated temporary SQLite demo with mock AI",
    )
    parser.add_argument(
        "--url", help="Use a disposable running server; requires DEMO_ADMIN_EMAIL/PASSWORD"
    )
    args = parser.parse_args()
    if args.url:
        import httpx

        with httpx.Client(base_url=args.url, timeout=30) as client:
            run(client, os.environ["DEMO_ADMIN_EMAIL"], os.environ["DEMO_ADMIN_PASSWORD"])
        return
    # Set configuration before importing application modules; never mutate a production app.
    with tempfile.TemporaryDirectory(prefix="apiforge-demo-") as directory:
        import secrets

        os.environ.update(
            DATABASE_URL=f"sqlite:///{directory}/demo.db",
            ENVIRONMENT="development",
            AI_ENABLED="true",
            AI_PROVIDER="mock",
            JWT_SECRET=secrets.token_urlsafe(48),
        )
        from alembic import command
        from alembic.config import Config
        from fastapi.testclient import TestClient

        from app.bootstrap import bootstrap
        from app.database import SessionLocal
        from app.main import app

        command.upgrade(Config("alembic.ini"), "head")
        email, password = "demo-admin@example.com", secrets.token_urlsafe(20)
        with SessionLocal() as db:
            bootstrap(db, email, password)
        with TestClient(app) as client:
            run(client, email, password)
        print("Temporary demo database removed on exit.")


if __name__ == "__main__":
    main()
