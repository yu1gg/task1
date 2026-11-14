from datetime import date
import re
from types import SimpleNamespace

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.auth import require_student
from app.db import get_db
from app.models import Job, StudentProfile, User
from app.services.profile_text import (
    format_awards,
    format_blocks,
    format_education,
    format_skills,
    parse_awards,
    parse_blocks,
    parse_education,
    parse_skills,
)
from app.services.usage import log_event
from app.templating import flash, render

router = APIRouter()


def profile_context(db, profile):
    return {
        "profile": profile,
        "education_text": format_education(profile.education_json),
        "projects_text": format_blocks(profile.projects_json, ["name", "role", "period"]),
        "internships_text": format_blocks(profile.internships_json, ["company", "role", "period"]),
        "awards_text": format_awards(profile.awards_json),
        "skills_text": format_skills(profile.skills_json),
        "jobs": db.scalars(select(Job).options(selectinload(Job.company)).where(Job.status == "open").order_by(Job.created_at.desc())).all(),
    }


@router.get("/profile")
def profile_page(
    request: Request,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    profile = db.get(StudentProfile, user.id)
    if profile is None:
        profile = StudentProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return render(request, "profile/edit.html", profile_context(db, profile))


@router.post("/profile")
def save_profile(
    request: Request,
    summary: str = Form(""),
    education_text: str = Form(""),
    projects_text: str = Form(""),
    internships_text: str = Form(""),
    awards_text: str = Form(""),
    skills_text: str = Form(""),
    availability_from: str = Form(""),
    availability_note: str = Form(""),
    target_job_id: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    share_contacts: bool = Form(False),
    contact_revision: int | None = Form(None),
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    phone, email, availability_from = phone.strip(), email.strip(), availability_from.strip()
    def render_draft(message, status_code=422):
        draft = SimpleNamespace(summary=summary[:500], phone=phone, email=email, share_contacts=share_contacts,
                                contact_revision=contact_revision if contact_revision is not None else 0,
                                availability_from=availability_from, availability_note=availability_note[:200],
                                target_job_id=int(target_job_id) if target_job_id.isdigit() and len(target_job_id) <= 9 else None,
                                education_json=[], projects_json=[], internships_json=[], awards_json=[], skills_json=[])
        context = profile_context(db, draft)
        context.update(error=message, education_text=education_text[:4000], projects_text=projects_text[:8000],
                       internships_text=internships_text[:8000], awards_text=awards_text[:4000], skills_text=skills_text[:4000])
        return render(request, "profile/edit.html", context, status_code=status_code)
    error = None
    if len(phone) > 40 or len(email) > 120 or any(ord(c) < 32 for c in phone + email):
        error = "电话最多40字、邮箱最多120字，不能包含控制字符。"
    elif email and not re.fullmatch(r"[^\s@]+@[^\s@]+", email):
        error = "请填写有效邮箱，或清空邮箱字段。"
    if availability_from:
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", availability_from):
                raise ValueError()
            date.fromisoformat(availability_from)
        except ValueError:
            error = "请填写有效的可到岗日期（YYYY-MM-DD）。"
    if error:
        # Redisplay submitted text without modifying the stored profile or permission.
        return render_draft(error)
    profile = db.get(StudentProfile, user.id)
    if profile is None:
        profile = StudentProfile(user_id=user.id)
        db.add(profile)
        db.flush()

    contact_changed = (profile.phone, profile.email, profile.share_contacts) != (phone, email, share_contacts)
    if contact_revision is None and contact_changed:
        return render_draft("修改联系方式或授权前，请重新打开资料页获取最新版本。输入已保留。", 409)
    expected_revision = profile.contact_revision if contact_revision is None else contact_revision
    if expected_revision != profile.contact_revision:
        return render_draft("联系方式或授权已在其他页面修改。输入已保留，请重新打开资料页核对后再保存。", 409)
    permission_changed = profile.share_contacts != share_contacts
    # Even unchanged contact fields participate in CAS so stale saves cannot undo a revoke.
    changed = db.execute(update(StudentProfile).where(StudentProfile.user_id == user.id, StudentProfile.contact_revision == expected_revision)
                         .values(phone=phone, email=email, share_contacts=share_contacts,
                                 contact_revision=StudentProfile.contact_revision + int(contact_changed)),
                         execution_options={"synchronize_session": False})
    if changed.rowcount != 1:
        db.rollback()
        return render_draft("联系方式或授权刚刚发生变化。输入已保留，请重新打开资料页核对后再保存。", 409)
    if permission_changed:
        log_event(db, "contact_permission_change", user_id=user.id, request=request, payload={"allowed": share_contacts})

    profile.summary = summary.strip()[:500]
    profile.education_json = parse_education(education_text[:4000])
    profile.projects_json = parse_blocks(
        projects_text[:8000], ["name", "role", "period"]
    )
    profile.internships_json = parse_blocks(
        internships_text[:8000], ["company", "role", "period"]
    )
    profile.awards_json = parse_awards(awards_text[:4000])
    profile.skills_json = parse_skills(skills_text[:4000])
    profile.availability_from = availability_from.strip()[:20] or None
    profile.availability_note = availability_note.strip()[:200] or None

    target_job_id = target_job_id.strip()
    if target_job_id.isdigit() and len(target_job_id) <= 9:
        job = db.get(Job, int(target_job_id))
        profile.target_job_id = (
            job.id if job is not None and job.status == "open" else None
        )
    else:
        profile.target_job_id = None

    log_event(
        db,
        "profile_save",
        user_id=user.id,
        request=request,
        payload={"skill_count": len(profile.skills_json)},
    )
    db.commit()
    flash(request, "资料已保存", "success")
    return RedirectResponse("/profile", status_code=303)
