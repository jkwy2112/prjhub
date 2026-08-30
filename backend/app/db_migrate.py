"""Lightweight startup migrations for SQLite (no alembic dependency)."""
import logging

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
    """tasks.status was an enum with CHECK constraint; rebuild as plain string."""
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
    logger.info("tasks table rebuilt")


def ensure_project_workflow_column(engine: Engine) -> None:
    """Add late-introduced columns if missing: projects.workflow_id,
    process_definitions.tree / node_meta (SQLite and PostgreSQL)."""
    if engine.url.get_backend_name() == "sqlite":
        with engine.connect() as conn:
            cols = [row[1] for row in conn.execute(text("PRAGMA table_info(projects)")).fetchall()]
        if cols and "workflow_id" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE projects ADD COLUMN workflow_id INTEGER"))
            logger.info("added projects.workflow_id column")
        with engine.connect() as conn:
            tcols = [row[1] for row in conn.execute(text("PRAGMA table_info(approval_tasks)")).fetchall()]
        for col in ("due_at", "reminded_at"):
            if tcols and col not in tcols:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE approval_tasks ADD COLUMN {col} DATETIME"))
                logger.info("added approval_tasks.%s column", col)
        with engine.connect() as conn:
            cols = [row[1] for row in conn.execute(text("PRAGMA table_info(process_definitions)")).fetchall()]
        for col in ("tree", "node_meta", "group_name", "remark", "logo"):
            if cols and col not in cols:
                coltype = "JSON" if col in ("tree", "node_meta", "logo") else "VARCHAR(255) DEFAULT ''"
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE process_definitions ADD COLUMN {col} {coltype}"))
                logger.info("added process_definitions.%s column", col)
    elif engine.url.get_backend_name() == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS workflow_id INTEGER"))
            conn.execute(text("ALTER TABLE process_definitions ADD COLUMN IF NOT EXISTS tree JSONB"))
            conn.execute(text("ALTER TABLE process_definitions ADD COLUMN IF NOT EXISTS node_meta JSONB"))
            conn.execute(text("ALTER TABLE process_definitions ADD COLUMN IF NOT EXISTS form_items JSONB"))
            conn.execute(text("ALTER TABLE approval_tasks ADD COLUMN IF NOT EXISTS due_at TIMESTAMPTZ"))
            conn.execute(text("ALTER TABLE approval_tasks ADD COLUMN IF NOT EXISTS reminded_at TIMESTAMPTZ"))
            conn.execute(text("ALTER TABLE process_definitions ADD COLUMN IF NOT EXISTS group_name VARCHAR(64) DEFAULT '默认分组'"))
            conn.execute(text("ALTER TABLE process_definitions ADD COLUMN IF NOT EXISTS remark VARCHAR(500) DEFAULT ''"))
            conn.execute(text("ALTER TABLE process_definitions ADD COLUMN IF NOT EXISTS logo JSONB"))


def run_startup_migrations(engine: Engine) -> None:
    rebuild_tasks_status_column(engine)
    ensure_project_workflow_column(engine)
