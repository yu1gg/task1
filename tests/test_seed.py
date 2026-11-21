from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Job, JobSkill, StudentProfile, User
from scripts.seed import seed_database


def test_seed_database_is_idempotent():
    with SessionLocal() as db:
        first = seed_database(db)
        second = seed_database(db)

        assert first["teacher"] == "teacher"
        assert second["teacher"] == "teacher"
        assert db.scalar(select(func.count()).select_from(User)) == 2
        assert db.scalar(select(func.count()).select_from(Job)) == 1
        assert db.scalar(select(func.count()).select_from(JobSkill)) >= 3
        assert db.scalar(select(func.count()).select_from(StudentProfile)) == 1


def test_seed_repairs_partial_state():
    with SessionLocal() as db:
        student = User(
            username="student",
            password_hash="x",
            real_name="张三",
            role="student",
        )
        db.add(student)
        db.commit()

    with SessionLocal() as db:
        seed_database(db)
        assert db.scalar(select(func.count()).select_from(StudentProfile)) == 1
