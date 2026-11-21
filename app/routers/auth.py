import hmac
from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import hash_password, verify_password
from app.config import settings
from app.db import get_db
from app.models import StudentProfile, User
from app.services.usage import log_event
from app.templating import flash, render

router = APIRouter()

VALID_ROLES = {"student", "teacher", "alumni"}


@router.get("/register")
def register_page(request: Request):
    return render(request, "auth/register.html")


@router.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    real_name: str = Form(...),
    role: str = Form("student"),
    teacher_code: str = Form(""),
    major: str = Form(""),
    grade: str = Form(""),
    db: Session = Depends(get_db),
):
    username = username.strip()
    real_name = real_name.strip()
    username = username[:32]
    real_name = real_name[:64]
    major = major.strip()[:64]
    grade = grade.strip()[:32]

    if len(username) < 3:
        flash(request, "用户名至少 3 位", "danger")
        return RedirectResponse("/register", status_code=303)
    if len(password) < 6:
        flash(request, "密码至少 6 位", "danger")
        return RedirectResponse("/register", status_code=303)
    if len(password.encode("utf-8")) > 72:
        flash(request, "密码过长，请控制在 72 字节以内", "danger")
        return RedirectResponse("/register", status_code=303)
    if not real_name:
        flash(request, "请填写真实姓名", "danger")
        return RedirectResponse("/register", status_code=303)
    if role not in VALID_ROLES:
        flash(request, "角色不合法", "danger")
        return RedirectResponse("/register", status_code=303)

    existing = db.scalar(select(User).where(User.username == username))
    if existing is not None:
        flash(request, "用户名已存在，请换一个", "danger")
        return RedirectResponse("/register", status_code=303)

    if role == "teacher":
        if not settings.teacher_invite_code:
            flash(request, "教师注册未开启，请联系管理员", "danger")
            return RedirectResponse("/register", status_code=303)
        if not hmac.compare_digest(
            teacher_code.strip().encode("utf-8"),
            settings.teacher_invite_code.encode("utf-8"),
        ):
            flash(request, "教师邀请码错误", "danger")
            return RedirectResponse("/register", status_code=303)

    user = User(
        username=username,
        password_hash=hash_password(password),
        real_name=real_name,
        role=role,
        major=major or None,
        grade=grade or None,
    )
    db.add(user)
    db.flush()

    if role == "student":
        db.add(StudentProfile(user_id=user.id))

    log_event(db, "register", user_id=user.id, request=request, payload={"role": role})
    db.commit()

    request.session["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/login")
def login_page(request: Request):
    return render(request, "auth/login.html")


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.username == username.strip()))
    if user is None or not verify_password(password, user.password_hash):
        log_event(
            db,
            "login_failed",
            user_id=user.id if user is not None else None,
            request=request,
            payload={"username": username.strip()},
        )
        db.commit()
        flash(request, "用户名或密码错误", "danger")
        return RedirectResponse("/login", status_code=303)

    user.last_login_at = datetime.utcnow()
    log_event(db, "login", user_id=user.id, request=request)
    db.commit()

    request.session["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if user_id:
        log_event(db, "logout", user_id=user_id, request=request)
        db.commit()
    request.session.clear()
    return RedirectResponse("/", status_code=303)
