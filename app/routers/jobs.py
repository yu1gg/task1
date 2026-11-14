from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user, require_user
from app.db import get_db
from app.models import Company, Job, User
from app.services.usage import log_event
from app.templating import flash, render

router = APIRouter(prefix="/jobs")


def get_job_or_404(db: Session, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="岗位不存在")
    return job


def can_edit_job(user: User, job: Job) -> bool:
    return user.role == "teacher" or job.created_by == user.id


def require_editor(user: User, job: Job) -> None:
    if not can_edit_job(user, job):
        raise HTTPException(status_code=403, detail="无权编辑该岗位")


@router.get("")
def list_jobs(
    request: Request,
    user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    jobs = db.scalars(
        select(Job)
        .options(selectinload(Job.company), selectinload(Job.skills))
        .where(Job.status == "open")
        .order_by(Job.created_at.desc())
    ).all()
    return render(request, "jobs/list.html", {"jobs": jobs})


@router.get("/new")
def new_job_page(
    request: Request,
    user: User = Depends(require_user),
):
    return render(request, "jobs/form.html", {"job": None})


@router.post("/new")
def create_job(
    request: Request,
    company_name: str = Form(...),
    industry: str = Form(""),
    size: str = Form(""),
    location: str = Form(""),
    title: str = Form(...),
    description: str = Form(""),
    requirements: str = Form(""),
    salary_range: str = Form(""),
    headcount: str = Form("1"),
    deadline: str = Form(""),
    expected_start_date: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    company_name = company_name.strip()
    title = title.strip()
    if not company_name or not title:
        flash(request, "企业和岗位名称不能为空", "danger")
        return RedirectResponse("/jobs/new", status_code=303)

    try:
        headcount_value = max(1, int(headcount))
    except ValueError:
        headcount_value = 1

    company = db.scalar(select(Company).where(Company.name == company_name))
    if company is None:
        company = Company(
            name=company_name,
            industry=industry.strip() or None,
            size=size.strip() or None,
            location=location.strip() or None,
            created_by=user.id,
        )
        db.add(company)
        db.flush()

    job = Job(
        company_id=company.id,
        title=title,
        description=description.strip(),
        requirements=requirements.strip(),
        location=location.strip() or company.location,
        salary_range=salary_range.strip() or None,
        headcount=headcount_value,
        deadline=deadline.strip() or None,
        expected_start_date=expected_start_date.strip() or None,
        created_by=user.id,
    )
    db.add(job)
    db.flush()

    log_event(
        db,
        "job_create",
        user_id=user.id,
        request=request,
        payload={"job_id": job.id},
    )
    db.commit()

    flash(request, "岗位已发布", "success")
    return RedirectResponse(f"/jobs/{job.id}", status_code=303)


@router.get("/{job_id}")
def job_detail(
    job_id: int,
    request: Request,
    user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_job_or_404(db, job_id)
    can_edit = bool(user and can_edit_job(user, job))
    return render(
        request,
        "jobs/detail.html",
        {"job": job, "can_edit": can_edit},
    )


@router.get("/{job_id}/edit")
def edit_job_page(
    job_id: int,
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    job = get_job_or_404(db, job_id)
    require_editor(user, job)
    return render(request, "jobs/form.html", {"job": job})


@router.post("/{job_id}/edit")
def update_job(
    job_id: int,
    request: Request,
    company_name: str = Form(...),
    industry: str = Form(""),
    size: str = Form(""),
    location: str = Form(""),
    title: str = Form(...),
    description: str = Form(""),
    requirements: str = Form(""),
    salary_range: str = Form(""),
    headcount: str = Form("1"),
    deadline: str = Form(""),
    expected_start_date: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    job = get_job_or_404(db, job_id)
    require_editor(user, job)

    company_name = company_name.strip()
    if not company_name or not title.strip():
        flash(request, "企业和岗位名称不能为空", "danger")
        return RedirectResponse(f"/jobs/{job.id}/edit", status_code=303)

    company = db.scalar(select(Company).where(Company.name == company_name))
    if company is None:
        company = Company(
            name=company_name,
            industry=industry.strip() or None,
            size=size.strip() or None,
            location=location.strip() or None,
            created_by=user.id,
        )
        db.add(company)
        db.flush()
    else:
        company.industry = industry.strip() or company.industry
        company.size = size.strip() or company.size
        company.location = location.strip() or company.location

    try:
        headcount_value = max(1, int(headcount))
    except ValueError:
        headcount_value = 1

    job.company_id = company.id
    job.title = title.strip()
    job.description = description.strip()
    job.requirements = requirements.strip()
    job.location = location.strip() or company.location
    job.salary_range = salary_range.strip() or None
    job.headcount = headcount_value
    job.deadline = deadline.strip() or None
    job.expected_start_date = expected_start_date.strip() or None

    log_event(
        db,
        "job_update",
        user_id=user.id,
        request=request,
        payload={"job_id": job.id},
    )
    db.commit()

    flash(request, "岗位已更新", "success")
    return RedirectResponse(f"/jobs/{job.id}", status_code=303)
