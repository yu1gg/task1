from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.auth import require_user
from app.db import get_db
from app.models import Job, ResumeExportTask, StudentProfile, User
from app.services.matching import compute_match
from app.templating import render

router = APIRouter()


@router.get("/dashboard")
def dashboard(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if user.role == "teacher":
        student_count = (
            db.scalar(
                select(func.count())
                .select_from(User)
                .where(User.role == "student")
            )
            or 0
        )
        job_count = db.scalar(select(func.count()).select_from(Job)) or 0
        jobs = db.scalars(
            select(Job)
            .options(selectinload(Job.company))
            .order_by(Job.created_at.desc())
            .limit(5)
        ).all()
        return render(
            request,
            "dashboard/teacher.html",
            {
                "student_count": student_count,
                "job_count": job_count,
                "jobs": jobs,
                "recent_exports": db.scalars(select(ResumeExportTask).where(ResumeExportTask.teacher_id == user.id).order_by(ResumeExportTask.created_at.desc()).limit(5)).all(),
            },
        )

    if user.role == "alumni":
        jobs = db.scalars(
            select(Job)
            .options(selectinload(Job.company))
            .where(Job.status == "open")
            .order_by(Job.created_at.desc())
            .limit(5)
        ).all()
        return render(request, "dashboard/alumni.html", {"jobs": jobs})

    profile = db.get(StudentProfile, user.id)
    skills = (profile.skills_json if profile else []) or []
    filled = 0
    if profile is not None:
        for value in [
            profile.summary,
            profile.education_json,
            profile.projects_json,
            profile.internships_json,
            profile.awards_json,
            profile.skills_json,
        ]:
            if value:
                filled += 1
    completion = round(filled / 6 * 100)

    jobs = db.scalars(
        select(Job)
        .options(selectinload(Job.company), selectinload(Job.skills))
        .where(Job.status == "open")
        .order_by(Job.created_at.desc())
        .limit(20)
    ).all()

    recommendations = []
    for job in jobs:
        result = compute_match(skills, job.skills)
        if result.has_job_skills:
            recommendations.append(
                {
                    "job": job,
                    "score": result.score,
                    "gap_count": len(result.gaps),
                }
            )
    recommendations.sort(key=lambda item: item["score"], reverse=True)
    recommendations = recommendations[:5]

    return render(
        request,
        "dashboard/student.html",
        {
            "completion": completion,
            "skill_count": len(skills),
            "jobs": jobs[:5],
            "recommendations": recommendations,
        },
    )
