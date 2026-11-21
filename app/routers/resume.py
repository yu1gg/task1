import json
import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.auth import require_student
from app.db import get_db
from app.models import Job, Resume, StudentProfile, User
from app.schemas import ResumeContent
from app.services.llm import LLMError, LLMProtocol, get_llm_client
from app.services.resume import generate_resume, resume_text_length
from app.services.resume_docx import export_resume_docx
from app.services.usage import log_event
from app.templating import flash, render

router = APIRouter()
logger = logging.getLogger(__name__)


def owned_resume(db: Session, resume_id: int, user: User) -> Resume:
    item = db.scalar(select(Resume).where(Resume.id == resume_id, Resume.student_id == user.id))
    if item is None:
        raise HTTPException(404, "简历不存在")
    return item


def list_page(request, db, user, job_id=None, error=None, status_code=200):
    profile = db.get(StudentProfile, user.id)
    return render(request, "resumes/list.html", {
        "resumes": db.scalars(select(Resume).where(Resume.student_id == user.id).order_by(Resume.updated_at.desc())).all(),
        "jobs": db.scalars(select(Job).where(Job.status == "open").options(selectinload(Job.company)).order_by(Job.created_at.desc())).all(),
        "selected_job": job_id if job_id is not None else (profile.target_job_id if profile else None),
        "error": error,
    }, status_code=status_code)


@router.get("/resumes")
def resume_list(request: Request, job_id: int | None = None, user: User = Depends(require_student), db: Session = Depends(get_db)):
    return list_page(request, db, user, job_id)


@router.post("/resumes/generate")
def create_resume(request: Request, job_id: int = Form(...), user: User = Depends(require_student),
                  db: Session = Depends(get_db), llm: LLMProtocol = Depends(get_llm_client)):
    job = db.scalar(select(Job).where(Job.id == job_id, Job.status == "open").options(selectinload(Job.company), selectinload(Job.skills)))
    if job is None:
        raise HTTPException(404, "岗位不存在或已关闭")
    profile = db.get(StudentProfile, user.id)
    if profile is None:
        return list_page(request, db, user, job_id, "请先完善个人资料再生成简历。", 422)
    try:
        content = generate_resume(user, profile, job, llm)
    except ValueError:
        return list_page(request, db, user, job_id, "资料为空或所选事实超过简历限制，请先完善或精简资料。", 422)
    except LLMError:
        # Never expose provider response bodies or authentication headers in the page.
        message = "未配置 AI 服务，请联系管理员。" if not getattr(llm, "api_key", True) else "简历生成失败，请稍后重试。"
        return list_page(request, db, user, job_id, message, 502)
    item = Resume(student_id=user.id, job_id=job.id, title=f"{job.title} 简历"[:120], content_json=content.model_dump())
    db.add(item)
    db.flush()
    log_event(db, "resume_generate", user_id=user.id, request=request, payload={"resume_id": item.id, "job_id": job.id, "version": 1})
    db.commit()
    return RedirectResponse(f"/resumes/{item.id}/edit", status_code=303)


def editor_page(request, item, content=None, title=None, error=None, status_code=200, raw=None, submitted_version=None):
    return render(request, "resumes/editor.html", {
        "resume": item, "content": content if content is not None else item.content_json,
        "edit_title": title if title is not None else item.title, "error": error, "raw_input": raw,
        "edit_version": item.version if submitted_version is None else submitted_version,
    }, status_code=status_code)


@router.get("/resumes/{resume_id}/edit")
def edit_resume(request: Request, resume_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)):
    return editor_page(request, owned_resume(db, resume_id, user))


@router.post("/resumes/{resume_id}/edit")
def save_resume(request: Request, resume_id: int, title: str = Form("我的简历"), version: int = Form(...),
                content_json: str = Form(""), user: User = Depends(require_student), db: Session = Depends(get_db)):
    item = owned_resume(db, resume_id, user)
    content = None
    try:
        if len(content_json) > 20000 or not title.strip() or len(title) > 120:
            raise ValueError("输入长度超限")
        content = json.loads(content_json)
        validated = ResumeContent.model_validate(content)
    except (ValueError, ValidationError):
        return editor_page(request, item, content if isinstance(content, dict) else None, title,
                           "保存失败：请检查必填项、字段长度及正文 1200 字上限。输入已保留。", 422, content_json, version)
    # Compare-and-swap in the UPDATE protects concurrent requests, not just stale browser tabs.
    result = db.execute(update(Resume).where(Resume.id == item.id, Resume.student_id == user.id, Resume.version == version)
                        .values(title=title.strip(), content_json=validated.model_dump(), version=Resume.version + 1),
                        execution_options={"synchronize_session": False})
    if result.rowcount != 1:
        db.rollback()
        db.refresh(item)
        return editor_page(request, item, content, title, "版本冲突：其他页面已保存。输入已保留，请核对后再次保存。", 409)
    log_event(db, "resume_save", user_id=user.id, request=request, payload={"resume_id": item.id, "job_id": item.job_id, "version": version + 1})
    db.commit()
    flash(request, "简历已保存，请核对内容真实性及打印页数。", "success")
    return RedirectResponse(f"/resumes/{item.id}/edit", status_code=303)


def saved_content(item):
    try:
        return ResumeContent.model_validate(item.content_json)
    except ValidationError as exc:
        raise HTTPException(422, "简历内容需要修正，请先打开编辑页保存。") from exc


@router.get("/resumes/{resume_id}/print")
def print_resume(request: Request, resume_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)):
    item = owned_resume(db, resume_id, user)
    content = saved_content(item)
    return render(request, "resumes/print.html", {"resume": item, "content": content.model_dump(), "text_length": resume_text_length(content)})


@router.get("/resumes/{resume_id}/export.docx")
def download_resume(request: Request, resume_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)):
    item = owned_resume(db, resume_id, user)
    content = saved_content(item)
    try:
        data = export_resume_docx(content)
    except Exception as exc:
        # Do not log document text or contact details.
        logger.error("Resume DOCX export failed: resume_id=%s error_type=%s", item.id, type(exc).__name__)
        return render(request, "resumes/export_error.html", {"resume": item}, status_code=503)
    log_event(db, "resume_export_docx", user_id=user.id, request=request,
              payload={"resume_id": item.id, "job_id": item.job_id, "version": item.version})
    db.commit()
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="resume-{item.id}-v{item.version}.docx"', "Cache-Control": "no-store"})
