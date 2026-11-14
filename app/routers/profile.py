from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
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

    jobs = db.scalars(
        select(Job)
        .options(selectinload(Job.company))
        .where(Job.status == "open")
        .order_by(Job.created_at.desc())
    ).all()

    return render(
        request,
        "profile/edit.html",
        {
            "profile": profile,
            "education_text": format_education(profile.education_json),
            "projects_text": format_blocks(
                profile.projects_json, ["name", "role", "period"]
            ),
            "internships_text": format_blocks(
                profile.internships_json, ["company", "role", "period"]
            ),
            "awards_text": format_awards(profile.awards_json),
            "skills_text": format_skills(profile.skills_json),
            "jobs": jobs,
        },
    )


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
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    profile = db.get(StudentProfile, user.id)
    if profile is None:
        profile = StudentProfile(user_id=user.id)
        db.add(profile)
        db.flush()

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
    profile.availability_from = availability_from.strip() or None
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
