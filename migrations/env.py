from alembic import context

from app import models  # noqa: F401
from app.config import settings
from app.database import Base, build_engine

target_metadata = Base.metadata


def offline():
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def online():
    engine = build_engine(settings.database_url)
    with engine.connect() as connection:
        if connection.dialect.name == "sqlite":
            # Batch table recreation must not trigger legacy ON DELETE CASCADE.
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()
        if connection.dialect.name == "sqlite":
            violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RuntimeError("Foreign key validation failed after migration")
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()
    engine.dispose()


if context.is_offline_mode():
    offline()
else:
    online()
