"""Add weighted categories without modifying prior evaluation snapshots."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("categories", sa.JSON(), nullable=True))
    table = sa.table("tasks", sa.column("categories", sa.JSON()))
    op.get_bind().execute(table.update().values(categories=[{"name": "general", "weight": 1}]))
    with op.batch_alter_table("tasks") as batch:
        batch.alter_column("categories", existing_type=sa.JSON(), nullable=False)


def downgrade():
    with op.batch_alter_table("tasks") as batch:
        batch.drop_column("categories")
