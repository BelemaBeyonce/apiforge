from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import StrictModel
from app.security import (
    DUMMY_HASH,
    admin_user,
    auth_rate_limit,
    current_user,
    hash_password,
    issue_token,
    verify_password,
)

router = APIRouter(tags=["authentication"])
DB = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(admin_user)]


class Credentials(StrictModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=12, max_length=128)
    model_config = {"extra": "forbid", "str_strip_whitespace": False}

    @field_validator("email")
    @classmethod
    def normalize(cls, value):
        return value.lower()


class UserRead(StrictModel):
    model_config = {"from_attributes": True}
    id: int
    email: str
    role: str
    is_active: bool


class TokenRead(StrictModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserUpdate(StrictModel):
    role: Literal["admin", "evaluator", "viewer"]
    is_active: bool = True


@router.post(
    "/auth/register",
    response_model=UserRead,
    status_code=201,
    dependencies=[Depends(auth_rate_limit)],
)
def register(data: Credentials, db: DB):
    user = User(email=data.email, password_hash=hash_password(data.password), role="viewer")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email is already registered") from None
    db.refresh(user)
    return user


@router.post("/auth/login", response_model=TokenRead, dependencies=[Depends(auth_rate_limit)])
def login(data: Credentials, db: DB):
    user = db.scalar(select(User).where(User.email == data.email))
    valid = verify_password(user.password_hash if user else DUMMY_HASH, data.password)
    if not valid or user is None or not user.is_active:
        raise HTTPException(401, "Invalid email or password")
    return dict(
        access_token=issue_token(user),
        expires_in=settings.token_minutes * 60,
    )


@router.get("/auth/me", response_model=UserRead)
def me(user: Annotated[User, Depends(current_user)]):
    return user


@router.get("/users", response_model=list[UserRead])
def users(
    db: DB,
    admin: Admin,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return db.scalars(select(User).order_by(User.id).limit(limit).offset(offset)).all()


@router.put("/users/{user_id}", response_model=UserRead)
def update_user(user_id: int, data: UserUpdate, db: DB, admin: Admin):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    if user.id == admin.id and (data.role != "admin" or not data.is_active):
        raise HTTPException(409, "Administrators cannot demote or disable themselves")
    user.role, user.is_active = data.role, data.is_active
    user.token_version += 1
    db.commit()
    db.refresh(user)
    return user
