from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user, require_user
from app.db import get_db
from app.models import Company, Job, JobSkill, User
from app.services.job_skills import extract_job_skills
from app.services.llm import LLMClient, LLMError, get_llm_client
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


def can_edit_company(user: User, company: Company) -> bool:
    return user.role == "teacher" or company.created_by == user.id


@router.get("")
def list_jobs(
    request: Request,
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
        if can_edit_company(user, company):
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


def _form_value(form, key: str, index: int, default: str = "") -> str:
    values = form.getlist(key)
    if index < len(values):
        return str(values[index])
    return default


@router.post("/{job_id}/extract-skills")
def extract_skills(
    job_id: int,
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
):
    job = get_job_or_404(db, job_id)
    require_editor(user, job)

    try:
        result = extract_job_skills(job, llm)
    except LLMError as exc:
        flash(request, str(exc), "danger")
        return RedirectResponse(f"/jobs/{job.id}", status_code=303)

    db.execute(delete(JobSkill).where(JobSkill.job_id == job.id))
    for index, skill in enumerate(result.skills):
        db.add(
            JobSkill(
                job_id=job.id,
                name=skill.name,
                category=skill.category,
                importance=skill.importance,
                required_level=skill.required_level,
                sort_order=index,
            )
        )

    log_event(
        db,
        "job_skill_extract",
        user_id=user.id,
        request=request,
        payload={"job_id": job.id, "skill_count": len(result.skills)},
    )
    db.commit()
    flash(request, f"已提取 {len(result.skills)} 项技能，请检查后保存", "success")
    return RedirectResponse(f"/jobs/{job.id}/skills", status_code=303)


@router.get("/{job_id}/skills")
def edit_skills_page(
    job_id: int,
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    job = get_job_or_404(db, job_id)
    require_editor(user, job)
    return render(request, "jobs/skills.html", {"job": job})


@router.post("/{job_id}/skills")
async def update_skills(
    job_id: int,
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    job = get_job_or_404(db, job_id)
    require_editor(user, job)

    form = await request.form()
    names = form.getlist("skill_name")

    db.execute(delete(JobSkill).where(JobSkill.job_id == job.id))

    created = 0
    for index, raw_name in enumerate(names):
        name = str(raw_name).strip()
        if not name:
            continue
        raw_level = _form_value(form, "skill_level", index, "3")
        try:
            level = max(1, min(5, int(raw_level)))
        except ValueError:
            level = 3
        importance = _form_value(form, "skill_importance", index, "nice")
        if importance not in {"must", "nice"}:
            importance = "nice"
        category = _form_value(
            form, "skill_category", index, "通用"
        ).strip() or "通用"
        db.add(
            JobSkill(
                job_id=job.id,
                name=name,
                category=category,
                importance=importance,
                required_level=level,
                sort_order=index,
            )
        )
        created += 1

    log_event(
        db,
        "job_skills_update",
        user_id=user.id,
        request=request,
        payload={"job_id": job.id, "skill_count": created},
    )
    db.commit()
    flash(request, f"已保存 {created} 项技能", "success")
    return RedirectResponse(f"/jobs/{job.id}", status_code=303)
