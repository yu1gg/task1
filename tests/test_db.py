from sqlalchemy import select, text

from app.db import SessionLocal, engine
from app.models import StudentProfile, User


def test_create_user_and_profile():
    with SessionLocal() as db:
        user = User(
            username="dbuser",
            password_hash="x",
            real_name="测试学生",
            role="student",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        db.add(StudentProfile(user_id=user.id))
        db.commit()

        loaded = db.scalar(select(User).where(User.username == "dbuser"))
        assert loaded is not None
        assert loaded.profile is not None
        assert loaded.real_name == "测试学生"


def test_sqlite_pragmas():
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert connection.execute(text("PRAGMA busy_timeout")).scalar() == 5000
        assert connection.execute(text("PRAGMA journal_mode")).scalar().lower() == "wal"
