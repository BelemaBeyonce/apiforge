"""Preserve legacy tasks/evaluations; add ownership and archive metadata."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "bootstrap_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.CheckConstraint("id = 1", name="ck_bootstrap_singleton"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("token_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('admin','evaluator','viewer')", name="ck_user_role"),
    )
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key("fk_tasks_owner", "users", ["owner_id"], ["id"])
        batch.create_index("ix_tasks_owner_id", ["owner_id"])
        batch.create_check_constraint("ck_task_revision", "revision >= 1")
        batch.create_check_constraint(
            "ck_task_difficulty", "difficulty IN ('easy','medium','hard')"
        )
    foreign_key_name = (
        sa.inspect(op.get_bind()).get_foreign_keys("evaluations")[0]["name"]
        or "fk_evaluations_task_id_tasks"
    )
    with op.batch_alter_table(
        "evaluations",
        naming_convention={"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"},
    ) as batch:
        batch.add_column(sa.Column("author_id", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column("status", sa.String(20), nullable=False, server_default="completed")
        )
        batch.create_foreign_key("fk_evaluations_author", "users", ["author_id"], ["id"])
        batch.drop_constraint(foreign_key_name, type_="foreignkey")
        batch.create_foreign_key(
            "fk_evaluations_task_id_tasks", "tasks", ["task_id"], ["id"], ondelete="RESTRICT"
        )
        batch.create_check_constraint("ck_evaluation_score", "score >= 0 AND score <= 100")
    op.create_table(
        "task_access",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "task_id", sa.Integer(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("permission", sa.String(20), nullable=False),
        sa.UniqueConstraint("task_id", "user_id", name="uq_task_access"),
        sa.CheckConstraint("permission IN ('reader','editor')", name="ck_access_permission"),
    )
    op.create_index("ix_task_access_task_id", "task_access", ["task_id"])
    op.create_index("ix_task_access_user_id", "task_access", ["user_id"])


def downgrade():
    # Downgrade intentionally blocked: dropping access controls can expose private data.
    raise RuntimeError("Security migration is forward-only; restore a reviewed backup to roll back")
