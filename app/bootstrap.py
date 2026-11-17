"""Explicit operator-only first-admin creation: python -m app.bootstrap."""

from getpass import getpass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.auth import Credentials
from app.database import SessionLocal
from app.models import BootstrapState, User
from app.security import hash_password


def bootstrap(db, email: str, password: str) -> User:
    data = Credentials(email=email, password=password)
    if db.scalar(select(User.id).where(User.role == "admin")) is not None:
        raise ValueError("An admin already exists; use authenticated user administration")
    user = User(email=data.email, password_hash=hash_password(data.password), role="admin")
    db.add(BootstrapState(id=1))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(
            "Bootstrap already completed or email exists; bootstrap never promotes registered users"
        ) from None
    db.refresh(user)
    return user


def main():
    with SessionLocal() as db:
        # The singleton DB guard serializes bootstrap; this command is operator-only.
        bootstrap(
            db, input("First admin email: "), getpass("First admin password (12+ characters): ")
        )
    print("First administrator created.")


if __name__ == "__main__":
    main()
