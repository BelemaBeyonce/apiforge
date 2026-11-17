"""Persist optional AI advice separately from immutable deterministic scores."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "evaluation_id",
            sa.Integer(),
            sa.ForeignKey("evaluations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("model_name", sa.String(200), nullable=False),
        sa.Column("prompt_version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("feedback", sa.JSON(), nullable=True),
        sa.Column("safe_metadata", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(40), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending_review','failed','accepted','rejected')", name="ck_ai_status"
        ),
    )
    op.create_index("ix_ai_evaluations_evaluation_id", "ai_evaluations", ["evaluation_id"])


def downgrade():
    op.drop_table("ai_evaluations")
