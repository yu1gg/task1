from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from tests.helpers import login, make_student, make_teacher, register


def test_register_student_and_login(client):
    response = register(client)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"

    client.post("/logout", follow_redirects=False)

    response = login(client)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"

    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "张三" in response.text


def test_duplicate_username_shows_error(client):
    register(client)
    response = register(client)
    assert response.status_code == 303

    response = client.get("/register")
    assert "用户名已存在" in response.text


def test_teacher_requires_invite_code(client):
    response = register(
        client,
        username="teacher_bad",
        real_name="错误老师",
        role="teacher",
        teacher_code="wrong-code",
        major="",
        grade="",
    )
    assert response.status_code == 303

    response = client.get("/register")
    assert "教师邀请码错误" in response.text


def test_teacher_registration_disabled_when_no_invite_code(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "teacher_invite_code", "")

    response = register(
        client,
        username="teacher_disabled",
        real_name="未开启老师",
        role="teacher",
        teacher_code="",
        major="",
        grade="",
    )
    assert response.status_code == 303

    response = client.get("/register")
    assert "教师注册未开启" in response.text


def test_teacher_can_register_with_invite_code(client):
    response = make_teacher(client)
    assert response.status_code == 303
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "李老师" in response.text


def test_password_is_hashed_and_not_stored_plaintext(client):
    make_student(client)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == "stu1"))
        assert user is not None
        assert user.password_hash != "pass123"
        assert user.password_hash.startswith("$2")


def test_logout_clears_session(client):
    make_student(client)
    client.post("/logout", follow_redirects=False)
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_verify_password_roundtrip():
    from app.auth import hash_password, verify_password

    password_hash = hash_password("pass123")
    assert verify_password("pass123", password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_verify_password_returns_false_for_malformed_hash():
    from app.auth import verify_password

    assert verify_password("pass123", "not-a-hash") is False
    assert verify_password("pass123", "") is False
    assert verify_password("pass123", "$2b$12$short") is False
