from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Annotated
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from limits import RateLimitItemPerMinute
from limits.storage import MemoryStorage
from limits.strategies import FixedWindowRateLimiter
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

hasher = PasswordHasher()
DUMMY_HASH = hasher.hash("dummy-credential-for-timing-only")
bearer = HTTPBearer(auto_error=False)
limiter = FixedWindowRateLimiter(MemoryStorage())
rate_keys: dict[str, float] = {}
rate_lock = Lock()


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(encoded: str, password: str) -> bool:
    try:
        return hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def issue_token(user: User) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user.id),
            "exp": now + timedelta(minutes=settings.token_minutes),
            "iat": now,
            "iss": "apiforge",
            "aud": "apiforge-api",
            "jti": str(uuid4()),
            "ver": user.token_version,
        },
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    unauthorized = HTTPException(
        401, "Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"}
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            issuer="apiforge",
            audience="apiforge-api",
            options={"require": ["sub", "exp", "iat", "jti", "ver"]},
        )
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise unauthorized from None
    user = db.get(User, user_id)
    if user is None or not user.is_active or user.token_version != payload["ver"]:
        raise unauthorized
    return user


def admin_user(user: Annotated[User, Depends(current_user)]) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Administrator role required")
    return user


def auth_rate_limit(request: Request) -> None:
    # Trust the direct peer, never caller-controlled X-Forwarded-For.
    import time

    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with rate_lock:
        for expired in [k for k, expiry in rate_keys.items() if expiry <= now]:
            rate_keys.pop(expired)
        if key not in rate_keys and len(rate_keys) >= 10000:
            raise HTTPException(429, "Authentication capacity reached; retry later")
        rate_keys[key] = now + 60
    if not limiter.hit(RateLimitItemPerMinute(settings.auth_rate_limit), key):
        raise HTTPException(429, "Too many authentication attempts", headers={"Retry-After": "60"})
