from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select

from app.bootstrap import bootstrap
from app.config import Settings, settings
from app.models import User
from app.security import hash_password, issue_token, rate_keys, verify_password

ROOT = "/api/v1"


def add_user(client, role="viewer", email="person@example.com"):
    with client.factory() as db:
        user = User(email=email, password_hash=hash_password("synthetic-password"), role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id, {"Authorization": "Bearer " + issue_token(user)}


def test_registration_login_and_me(client):
    client.headers.clear()
    payload = {"email": "New@Example.com", "password": "secure-test-password"}
    result = client.post(ROOT + "/auth/register", json=payload)
    assert result.status_code == 201
    assert result.json()["role"] == "viewer"
    assert "password" not in result.text
    assert client.post(ROOT + "/auth/register", json=payload).status_code == 409
    result = client.post(ROOT + "/auth/login", json=payload)
    assert result.status_code == 200
    token = result.json()["access_token"]
    assert result.json()["expires_in"] == 1800
    assert (
        client.get(ROOT + "/auth/me", headers={"Authorization": "Bearer " + token}).json()["email"]
        == "new@example.com"
    )
    with client.factory() as db:
        user = db.scalar(select(User).where(User.email == "new@example.com"))
        assert user.password_hash.startswith("$argon2id$")
        assert verify_password(user.password_hash, payload["password"])
    for payload in [
        {"email": "new@example.com", "password": "wrong-password"},
        {"email": "absent@example.com", "password": "wrong-password"},
    ]:
        assert client.post(ROOT + "/auth/login", json=payload).status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "bad", "password": "secure-test-password"},
        {"email": "valid@example.com", "password": "short"},
        {"email": "valid@example.com", "password": "x" * 129},
        {"email": "valid@example.com", "password": "secure-test-password", "role": "admin"},
    ],
)
def test_invalid_registration(client, payload):
    assert client.post(ROOT + "/auth/register", json=payload).status_code == 422


@pytest.mark.parametrize("token", ["", "not.a.token", "Bearer nonsense"])
def test_bad_tokens(client, token):
    client.headers.clear()
    result = client.get(ROOT + "/tasks", headers={"Authorization": token})
    assert result.status_code == 401
    assert result.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "change",
    [{"exp": 0}, {"aud": "wrong"}, {"iss": "wrong"}, {"sub": "abc"}, {"ver": 999}, {"sub": "999"}],
)
def test_invalid_claims(client, change):
    data = dict(
        sub=str(client.admin_id),
        exp=datetime.now(UTC) + timedelta(minutes=1),
        iat=datetime.now(UTC),
        iss="apiforge",
        aud="apiforge-api",
        jti="test",
        ver=1,
    )
    data.update(change)
    token = jwt.encode(data, settings.jwt_secret.get_secret_value(), algorithm="HS256")
    assert (
        client.get(ROOT + "/tasks", headers={"Authorization": "Bearer " + token}).status_code == 401
    )


def test_wrong_signature(client):
    token = jwt.encode(
        {"sub": "1"}, "different-secret-with-32-characters-minimum", algorithm="HS256"
    )
    assert (
        client.get(ROOT + "/tasks", headers={"Authorization": "Bearer " + token}).status_code == 401
    )
    assert not verify_password("not-a-hash", "password")


def test_roles_grants_isolation_and_revocation(client, task_data):
    owner_id, owner = add_user(client, "evaluator", "owner@example.com")
    viewer_id, viewer = add_user(client)
    editor_id, editor = add_user(client, "evaluator", "editor@example.com")
    task = client.post(ROOT + "/tasks", json=task_data, headers=owner).json()
    url = f"{ROOT}/tasks/{task['id']}"
    assert client.get(url, headers=viewer).status_code == 404
    assert client.get(ROOT + "/tasks", headers=viewer).json()["total"] == 0
    assert client.post(ROOT + "/tasks", json=task_data, headers=viewer).status_code == 403
    assert (
        client.put(
            f"{url}/access/{viewer_id}", json={"permission": "reader"}, headers=owner
        ).status_code
        == 200
    )
    assert client.get(url, headers=viewer).status_code == 200
    assert (
        client.post(url + "/evaluations", json={"response": "sorted"}, headers=viewer).status_code
        == 403
    )
    assert (
        client.put(
            f"{url}/access/{editor_id}", json={"permission": "reader"}, headers=owner
        ).status_code
        == 200
    )
    assert (
        client.post(url + "/evaluations", json={"response": "sorted"}, headers=editor).status_code
        == 403
    )
    client.put(f"{url}/access/{editor_id}", json={"permission": "editor"}, headers=owner)
    evaluation = client.post(
        url + "/evaluations", json={"response": "sorted"}, headers=editor
    ).json()
    assert (
        client.put(
            f"{url}/access/{viewer_id}", json={"permission": "editor"}, headers=editor
        ).status_code
        == 403
    )
    assert client.delete(f"{url}/access/{viewer_id}", headers=editor).status_code == 403
    assert client.get(f"{ROOT}/evaluations/{evaluation['id']}", headers=viewer).status_code == 200
    assert client.delete(f"{url}/access/{viewer_id}", headers=owner).status_code == 204
    assert client.get(f"{ROOT}/evaluations/{evaluation['id']}", headers=viewer).status_code == 404
    assert (
        client.put(f"{url}/access/999", json={"permission": "reader"}, headers=owner).status_code
        == 404
    )
    assert client.delete(f"{url}/access/999", headers=owner).status_code == 204
    assert client.get(ROOT + "/users", headers=viewer).status_code == 403
    assert client.get(ROOT + "/users").status_code == 200
    result = client.put(f"{ROOT}/users/{owner_id}", json={"role": "evaluator", "is_active": False})
    assert result.status_code == 200
    assert client.get(url, headers=owner).status_code == 401
    assert (
        client.post(
            ROOT + "/auth/login",
            json={"email": "owner@example.com", "password": "synthetic-password"},
        ).status_code
        == 401
    )
    assert client.put(f"{ROOT}/users/{client.admin_id}", json={"role": "viewer"}).status_code == 409
    assert client.put(ROOT + "/users/999", json={"role": "viewer"}).status_code == 404


def test_rate_limiting_and_expiration(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_rate_limit", 2)
    payload = {"email": "nobody@example.com", "password": "wrong-password"}
    assert client.post(ROOT + "/auth/login", json=payload).status_code == 401
    assert client.post(ROOT + "/auth/login", json=payload).status_code == 401
    result = client.post(
        ROOT + "/auth/login", json=payload, headers={"X-Forwarded-For": "new-address"}
    )
    assert result.status_code == 429 and result.headers["Retry-After"] == "60"
    rate_keys["expired"] = 0
    client.post(ROOT + "/auth/login", json=payload)
    assert "expired" not in rate_keys


def test_bootstrap_is_explicit_and_never_promotes_registered_user(client):
    with client.factory() as db:
        with pytest.raises(ValueError, match="already exists"):
            bootstrap(db, "new@example.com", "strong-password")
        for user in db.scalars(select(User)).all():
            db.delete(user)
        db.commit()
        user = User(
            email="existing@example.com",
            password_hash=hash_password("strong-password"),
            role="viewer",
        )
        db.add(user)
        db.commit()
        with pytest.raises(ValueError, match="never promotes"):
            bootstrap(db, "existing@example.com", "strong-password")
        assert db.scalar(select(User.role)) == "viewer"
        admin = bootstrap(db, "admin@example.com", "strong-password")
        assert admin.role == "admin"


@pytest.mark.parametrize(
    "config",
    [
        {"jwt_secret": "short"},
        {"cors_origins": ["*"]},
        {"environment": "production"},
        {"environment": "production", "jwt_secret": "a" * 40},
        {
            "environment": "production",
            "jwt_secret": "a" * 40,
            "database_url": "postgresql+psycopg://localhost/db",
            "cors_origins": ["http://localhost"],
        },
        {"ai_enabled": True},
        {
            "ai_enabled": True,
            "ai_allow_external": True,
            "ai_api_key": "test",
            "ai_base_url": "http://example.com",
        },
        {
            "environment": "production",
            "jwt_secret": "a" * 40,
            "database_url": "postgresql+psycopg://localhost/db",
            "ai_enabled": True,
            "ai_provider": "mock",
        },
    ],
)
def test_unsafe_configuration_rejected(config):
    with pytest.raises(ValueError):
        Settings(_env_file=None, **config)


def test_revision_compare_and_swap_and_archived_history(client, task_data):
    task = client.post(ROOT + "/tasks", json=task_data).json()
    url = f"{ROOT}/tasks/{task['id']}"
    result = client.post(url + "/evaluations", json={"response": "sorted stable"}).json()
    assert client.put(url, json={**task_data, "expected_revision": 1}).status_code == 200
    assert client.put(url, json={**task_data, "expected_revision": 1}).status_code == 409
    assert client.delete(url, headers={"If-Match": "1"}).status_code == 409
    assert client.delete(url, headers={"If-Match": "2"}).status_code == 204
    assert client.get(url).status_code == 404
    assert client.get(url + "?include_archived=true").json()["revision"] == 3
    assert client.get(ROOT + "/tasks").json()["total"] == 0
    assert client.get(ROOT + "/tasks?include_archived=true").json()["total"] == 1
    assert client.get(url + "/evaluations").json()["total"] == 1
    assert client.get(f"{ROOT}/evaluations/{result['id']}").json()["score"] == 100
    assert client.post(url + "/evaluations", json={"response": "sorted"}).status_code == 404
    assert client.put(url, json={**task_data, "expected_revision": 3}).status_code == 404
