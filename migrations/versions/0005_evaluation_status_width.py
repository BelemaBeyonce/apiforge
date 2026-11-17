"""Allow the explicit completed_with_limits status on strict PostgreSQL columns."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("evaluations") as batch:
        batch.alter_column(
            "status", existing_type=sa.String(20), type_=sa.String(32), existing_nullable=False
        )


def downgrade():
    # Narrowing could truncate an existing status; keep rollback explicit.
    raise RuntimeError("Status widening is forward-only; restore a reviewed backup")
