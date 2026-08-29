import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.security import hash_password
from app.db import Base, SessionLocal, engine
from app.db_migrate import rebuild_tasks_status_column
from app.models import AuthType, Project, ProjectMember, ProjectRole, Task, TaskPriority, TaskType, User
from app.routers import admin, auth, dashboard, projects, tasks, users, workflow
from app.services import workflow_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("prjhub")


def seed() -> None:
    db = SessionLocal()
    try:
        workflow_service.seed_workflow(db)

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
                        type=TaskType.task, status=workflow_service.initial_key(db),
                        priority=TaskPriority.medium, created_by=admin_user.id, task_order=1))
            db.commit()
            logger.info("seeded demo project DEMO")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    rebuild_tasks_status_column(engine)
    Base.metadata.create_all(bind=engine)
    seed()
    yield


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
    app.include_router(workflow.router)
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
