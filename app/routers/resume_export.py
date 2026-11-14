"""Teacher-owned, private batch resume export tasks."""
from datetime import datetime, timedelta
import re

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import require_teacher
from app.config import settings
from app.db import get_db
from app.models import Job, ResumeExportItem, ResumeExportTask, StudentProfile, User
from app.services import resume_exports as exports
from app.services.usage import log_event
from app.templating import render

router = APIRouter()


def task_items(db, task):
    return db.scalars(select(ResumeExportItem).where(ResumeExportItem.task_id == task.id).order_by(ResumeExportItem.student_id)).all()


def owned_task(db, task_id, user):
    task = db.scalar(select(ResumeExportTask).where(ResumeExportTask.id == task_id, ResumeExportTask.teacher_id == user.id))
    if task is None:
        raise HTTPException(404, '导出任务不存在')
    if task.status not in ('expired', 'invalidated'):
        if task.expires_at <= datetime.utcnow():
            task.status = 'expired'
        elif not exports.contacts_current(db, task):
            task.status = 'invalidated'
        else:
            return task
        exports.cleanup_task_files(db, task)
        db.commit()
    return task


def redirect_existing(db, task, job_id, student_ids):
    if task.job_id != job_id or [item.student_id for item in task_items(db, task)] != student_ids:
        raise HTTPException(409, '请求标识已用于其他岗位或学生，请重新选择并创建任务')
    return RedirectResponse(f'/teacher/resume-exports/{task.id}', status_code=303)


@router.post('/teacher/jobs/{job_id}/resume-exports')
def create_export(job_id: int, request: Request, student_ids: list[int] = Form(...), request_key: str = Form(...), user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    if not re.fullmatch(r'[A-Za-z0-9_-]{32,64}', request_key):
        raise HTTPException(422, '请求标识必须为32至64位字母、数字、连字符或下划线')
    if not 1 <= len(student_ids) <= 10 or len(set(student_ids)) != len(student_ids):
        raise HTTPException(422, '请选择1至10名不同学生')
    student_ids = sorted(student_ids)
    existing = db.scalar(select(ResumeExportTask).where(ResumeExportTask.teacher_id == user.id, ResumeExportTask.request_key == request_key))
    if existing:
        return redirect_existing(db, existing, job_id, student_ids)
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, '岗位不存在')
    students = db.scalars(select(User).where(User.id.in_(student_ids), User.role == 'student').order_by(User.id)).all()
    if len(students) != len(student_ids):
        raise HTTPException(422, '所选学生不存在或身份无效')
    if not settings.deepseek_api_key.strip():
        raise HTTPException(503, '未配置 DeepSeek 服务，请联系管理员配置后再导出')
    task = ResumeExportTask(teacher_id=user.id, job_id=job.id, request_key=request_key,
        expires_at=datetime.utcnow() + timedelta(hours=24), job_snapshot={
            'title': job.title, 'description': job.description[:4000], 'requirements': job.requirements[:4000],
            'skills': [{'name': s.name, 'importance': s.importance, 'required_level': s.required_level} for s in job.skills]})
    try:
        db.add(task)
        db.flush()
        for student in students:
            db.add(ResumeExportItem(task_id=task.id, student_id=student.id,
                snapshot_json=exports.snapshot_student(student, db.get(StudentProfile, student.id))))
        log_event(db, 'resume_export_create', user.id, request=request, payload={'task_id': task.id, 'job_id': job.id, 'count': len(students)})
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(ResumeExportTask).where(ResumeExportTask.teacher_id == user.id, ResumeExportTask.request_key == request_key))
        if existing is None:
            raise
        return redirect_existing(db, existing, job_id, student_ids)
    return RedirectResponse(f'/teacher/resume-exports/{task.id}', status_code=303)


@router.get('/teacher/resume-exports/{task_id}')
def export_page(task_id: int, request: Request, user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    task = owned_task(db, task_id, user)
    return render(request, 'teacher/export_task.html', {'task': task})


@router.get('/teacher/resume-exports/{task_id}/status')
def export_status(task_id: int, response: Response, user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    response.headers['Cache-Control'] = 'no-store'
    task = owned_task(db, task_id, user)
    items = task_items(db, task)
    return {'id': task.id, 'status': task.status, 'items': [
        {'student_id': item.student_id, 'name': item.snapshot_json.get('user', {}).get('real_name', ''), 'status': item.status, 'error': item.error_message} for item in items],
        'completed': sum(item.status in ('completed', 'failed') for item in items), 'total': len(items),
        'error': task.error_message, 'download_url': f'/teacher/resume-exports/{task.id}/download' if task.status in ('completed', 'partial') and task.archive_path else None,
        'can_retry': task.status in ('partial', 'failed')}


@router.get('/teacher/resume-exports/{task_id}/download')
def export_download(task_id: int, request: Request, user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    task = owned_task(db, task_id, user)
    if task.status not in ('completed', 'partial'):
        raise HTTPException(409, '任务尚无可下载文件或已经失效，请查看任务状态')
    try:
        path = exports.resolve_export_file(task.archive_path) if task.archive_path else None
    except ValueError:
        raise HTTPException(404, '导出文件不存在') from None
    if path is None or not path.is_file():
        raise HTTPException(404, '导出文件不存在')
    log_event(db, 'resume_export_download', user.id, request=request, payload={'task_id': task.id})
    db.commit()
    return FileResponse(path, filename=f'resumes-{task.id}.zip', media_type='application/zip', headers={'Cache-Control': 'no-store'})


@router.post('/teacher/resume-exports/{task_id}/retry', status_code=202)
def retry_export(task_id: int, request: Request, user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    task = owned_task(db, task_id, user)
    if task.status not in ('partial', 'failed'):
        raise HTTPException(409, '当前任务不能重试，失效任务请重新创建')
    changed = db.execute(update(ResumeExportTask).where(ResumeExportTask.id == task.id, ResumeExportTask.status.in_(('partial', 'failed'))).values(status='queued', error_message=None))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, '任务已经在重试中')
    db.execute(update(ResumeExportItem).where(ResumeExportItem.task_id == task.id, ResumeExportItem.status == 'failed').values(status='pending', error_message=None))
    log_event(db, 'resume_export_retry', user.id, request=request, payload={'task_id': task.id})
    db.commit()
    return {'id': task.id, 'status': 'queued'}
