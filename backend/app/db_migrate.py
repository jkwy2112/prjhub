"""Lightweight startup migrations for SQLite (no alembic dependency).

Handles the enum->string change of tasks.status by rebuilding the table
without the legacy CHECK constraint, preserving data and foreign keys.
"""
import logging
import re

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def _needs_tasks_status_rebuild(conn) -> bool:
    row = conn.execute(
        text("SELECT sql FROM sqlite_master WHERE type='table' AND name='tasks'")
    ).fetchone()
    if not row or not row[0]:
        return False
    create_sql = str(row[0]).upper()
    return "CHECK" in create_sql and "STATUS" in create_sql


def rebuild_tasks_status_column(engine: Engine) -> None:
    if not engine.url.get_backend_name() == "sqlite":
        return
    with engine.connect() as conn:
        if not _needs_tasks_status_rebuild(conn):
            return
    logger.info("migrating tasks.status enum -> string (SQLite table rebuild)")
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.execute(text("PRAGMA legacy_alter_table=ON"))
        conn.execute(text("ALTER TABLE tasks RENAME TO _tasks_old"))
        conn.execute(text("PRAGMA legacy_alter_table=OFF"))
    # create fresh table from current metadata, then copy data back
    from app.db import Base
    import app.models  # noqa: F401 ensure mappers loaded

    Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables["tasks"]])
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO tasks (id, number, title, description, type, status, priority, "
            "assignee_id, project_id, created_by, due_date, task_order, created_at, updated_at) "
            "SELECT id, number, title, description, type, status, priority, "
            "assignee_id, project_id, created_by, due_date, task_order, created_at, updated_at FROM _tasks_old"
        ))
        conn.execute(text("DROP TABLE _tasks_old"))
        conn.execute(text("PRAGMA foreign_keys=ON"))
    logger.info("tasks table rebuilt, %s rows preserved",
                engine.connect().execute(text("SELECT count(*) FROM tasks")).scalar())
