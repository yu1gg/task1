from sqlalchemy import select

from app.db import SessionLocal
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
