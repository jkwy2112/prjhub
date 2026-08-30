import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.security import hash_password
from app.db import Base, SessionLocal, engine
from app.db_migrate import run_startup_migrations
from app.models import AuthType, Project, ProjectMember, ProjectRole, Task, TaskPriority, TaskType, User
from app.routers import admin, approvals, auth, dashboard, projects, tasks, users
from app.services import approval_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("prjhub")


def seed() -> None:
    db = SessionLocal()
    try:
        approval_service.seed_templates(db)

        admin_user = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
        if not admin_user:
            admin_user = User(
                username=settings.ADMIN_USERNAME,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                name="系统管理员",
                email="admin@prjhub.local",
                auth_type=AuthType.local,
                is_superuser=True,
            )
            db.add(admin_user)
            db.commit()
            logger.info("seeded admin user: %s", settings.ADMIN_USERNAME)

        if db.query(Project).count() == 0:
            demo = Project(key="DEMO", name="示例项目", description="系统自动创建的示例项目, 可直接删除",
                           color="#409EFF", created_by=admin_user.id)
            db.add(demo)
            db.flush()
            db.add(ProjectMember(project_id=demo.id, user_id=admin_user.id, role=ProjectRole.owner))
            db.add(Task(project_id=demo.id, number=1, title="浏览看板并创建你的第一个任务",
                        type=TaskType.task, status="todo",
                        priority=TaskPriority.medium, created_by=admin_user.id, task_order=1))
            db.commit()
            logger.info("seeded demo project DEMO")
    finally:
        db.close()


_scheduler = None


def start_reminder() -> None:
    global _scheduler
    if not settings.REMINDER_ENABLED or _scheduler is not None:
        return
    from apscheduler.schedulers.background import BackgroundScheduler

    from app.services.reminder import remind_overdue

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(remind_overdue, "interval",
                       minutes=max(1, settings.REMINDER_INTERVAL_MINUTES), max_instances=1)
    _scheduler.start()
    logger.info("reminder scheduler started (every %s min)", settings.REMINDER_INTERVAL_MINUTES)


@asynccontextmanager
async def lifespan(_: FastAPI):
    run_startup_migrations(engine)
    Base.metadata.create_all(bind=engine)
    seed()
    start_reminder()
    yield
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def create_app() -> FastAPI:
    app = FastAPI(title=f"{settings.APP_NAME} API", version=settings.APP_VERSION, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(admin.router)
    app.include_router(approvals.router)
    app.include_router(projects.router)
    app.include_router(tasks.router)
    app.include_router(dashboard.router)

    @app.get("/health", tags=["meta"])
    def health():
        return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}

    @app.get("/meta/auth-options", tags=["meta"])
    def auth_options():
        from app.db import SessionLocal
        from app.services import config_service

        db = SessionLocal()
        try:
            return {
                "ldap_enabled": bool(config_service.ldap_config(db).get("enabled")),
                "wecom_enabled": bool(config_service.wecom_config(db).get("enabled")),
            }
        finally:
            db.close()

    return app


app = create_app()
