from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow():
    return datetime.now(UTC)


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("revision >= 1", name="ck_task_revision"),
        CheckConstraint("difficulty IN ('easy','medium','hard')", name="ck_task_difficulty"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(40), index=True)
    difficulty: Mapped[str] = mapped_column(String(20), index=True)
    expected_outcome: Mapped[str] = mapped_column(Text)
    criteria: Mapped[list] = mapped_column(JSON)
    categories: Mapped[list] = mapped_column(
        JSON, default=lambda: [{"name": "general", "weight": 1}]
    )
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    python_assessment: Mapped[dict | None] = mapped_column(
    JSON,
    nullable=True
    )


class Evaluation(Base):
    __tablename__ = "evaluations"
    __table_args__ = (CheckConstraint("score >= 0 AND score <= 100", name="ck_evaluation_score"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="RESTRICT"), index=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(32), default="completed", server_default="completed")
    response: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float)
    feedback: Mapped[list] = mapped_column(JSON)
    task_snapshot: Mapped[dict] = mapped_column(JSON)
    engine_version: Mapped[str] = mapped_column(String(40), default="deterministic-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin','evaluator','viewer')", name="ck_user_role"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    token_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class TaskAccess(Base):
    __tablename__ = "task_access"
    __table_args__ = (
        UniqueConstraint("task_id", "user_id", name="uq_task_access"),
        CheckConstraint("permission IN ('reader','editor')", name="ck_access_permission"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    permission: Mapped[str] = mapped_column(String(20))


class AIEvaluation(Base):
    __tablename__ = "ai_evaluations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_review','failed','accepted','rejected')", name="ck_ai_status"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(
        ForeignKey("evaluations.id", ondelete="RESTRICT"), index=True
    )
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    provider: Mapped[str] = mapped_column(String(20))
    model_name: Mapped[str] = mapped_column(String(200))
    prompt_version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20))
    feedback: Mapped[dict | None] = mapped_column(JSON)
    safe_metadata: Mapped[dict] = mapped_column(JSON)
    error_code: Mapped[str | None] = mapped_column(String(40))
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BootstrapState(Base):
    __tablename__ = "bootstrap_state"
    __table_args__ = (CheckConstraint("id = 1", name="ck_bootstrap_singleton"),)
    id: Mapped[int] = mapped_column(primary_key=True)
