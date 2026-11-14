from contextlib import asynccontextmanager
import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.db import init_db
from app.routers import auth, dashboard, health, home, jobs, profile, resume, interview, teacher, resume_export
from app.services.interview_worker import InterviewWorker
from app.services.resume_export_worker import ResumeExportWorker


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    # Existing databases must be upgraded offline; create_all cannot add columns.
    from sqlalchemy import inspect
    from app.db import engine
    inspector = inspect(engine)
    if ("context_json" not in {c["name"] for c in inspector.get_columns("interviews")}
            or "answer_audio_path" not in {c["name"] for c in inspector.get_columns("interview_turns")}):
        raise RuntimeError("请先停服务并执行 python -m scripts.migrate_p3，再启动单进程服务。")
    if not {"phone", "email", "share_contacts", "contact_revision"}.issubset({c["name"] for c in inspector.get_columns("student_profiles")}):
        raise RuntimeError("请先停服务并执行 python -m scripts.migrate_p4，再启动单进程服务。")
    worker = InterviewWorker() if settings.interview_worker_enabled else None
    export_worker = ResumeExportWorker() if settings.resume_export_worker_enabled else None
    app.state.interview_worker = worker
    app.state.resume_export_worker = export_worker
    started = []
    try:
        for consumer in (worker, export_worker):
            if consumer:
                consumer.start()
                started.append(consumer)
        yield
    finally:
        await asyncio.gather(*(asyncio.to_thread(consumer.stop) for consumer in started))


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        same_site="lax",
        https_only=False,
        max_age=7 * 24 * 3600,
    )
    app.mount(
        "/static",
        StaticFiles(directory=str(Path(__file__).resolve().parent / "static")),
        name="static",
    )
    app.include_router(health.router)
    app.include_router(home.router)
    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(jobs.router)
    app.include_router(profile.router)
    app.include_router(resume.router)
    app.include_router(interview.router)
    app.include_router(teacher.router)
    app.include_router(resume_export.router)
    return app


app = create_app()
