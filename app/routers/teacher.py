from uuid import uuid4
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.auth import require_teacher
from app.config import settings
from app.db import get_db, SessionLocal
from app.models import Job, UsageEvent, User
from app.services.llm import LLMClient, LLMError, get_llm_client
from app.services.matching import compute_match
from app.services.teacher_matching import explain_match, parse_date
from app.services.usage import log_event
from app.services.usage_csv import beijing_time, csv_chunks, filtered_usage
from app.templating import render

router = APIRouter(prefix='/teacher')


def stream_usage(stmt):
    # FastAPI may finalize request dependencies before consuming a streaming body.
    with SessionLocal() as db:
        yield from csv_chunks(db, stmt)


def optional_user_id(user_id: str = '') -> int | None:
    if not user_id:
        return None
    try:
        result = int(user_id)
    except ValueError:
        raise HTTPException(422, '用户ID应为整数') from None
    if not -(2**63) <= result < 2**63:
        raise HTTPException(422, '用户ID超出允许范围')
    return result


def job_or_404(db, job_id):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, '岗位不存在')
    return job


@router.get('/jobs/{job_id}/matches')
def matches(job_id: int, request: Request, available_by: str = '',
            user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    job = job_or_404(db, job_id)
    cutoff = parse_date(available_by) if available_by else None
    if available_by and cutoff is None:
        raise HTTPException(422, '到岗日期应为有效的YYYY-MM-DD日期')
    students = db.scalars(select(User).where(User.role == 'student').options(selectinload(User.profile))).all()
    rows = []
    for student in students:
        profile = student.profile
        available = parse_date(profile.availability_from) if profile else None
        if cutoff is not None and (available is None or available > cutoff):
            continue
        skills = profile.skills_json or [] if profile else []
        rows.append({'student': student, 'match': compute_match(skills, job.skills),
                     'available': available, 'has_skills': bool(skills)})
    rows.sort(key=lambda row: (-row['match'].score, row['student'].id))
    return render(request, 'teacher/matches.html', {'job': job, 'rows': rows,
                  'available_by': available_by, 'request_key': uuid4().hex,
                  'llm_configured': bool(settings.deepseek_api_key)})


@router.post('/jobs/{job_id}/students/{student_id}/explanation')
def explanation(job_id: int, student_id: int, user: User = Depends(require_teacher),
                db: Session = Depends(get_db), llm: LLMClient = Depends(get_llm_client)):
    job = job_or_404(db, job_id)
    student = db.get(User, student_id)
    if student is None or student.role != 'student':
        raise HTTPException(404, '学生不存在')
    if not job.skills:
        raise HTTPException(422, '岗位尚未分析技能，请先分析')
    skills = student.profile.skills_json or [] if student.profile else []
    try:
        return explain_match(skills, job.skills, llm)
    except LLMError:
        raise HTTPException(502, '匹配解释暂不可用，请稍后重试') from None


@router.get('/usage')
def usage(request: Request, user_id: int | None = Depends(optional_user_id), event_type: str = '',
          start_date: str = '', end_date: str = '', page: int = Query(1, ge=1),
          user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    stmt = filtered_usage(user_id, event_type, start_date, end_date)
    rows = db.execute(stmt.offset((page - 1) * 50).limit(51)).all()
    filters = dict(user_id=user_id, event_type=event_type, start_date=start_date, end_date=end_date)
    query = urlencode({key: value for key, value in filters.items() if value is not None})
    return render(request, 'teacher/usage.html', {'rows': rows[:50], 'has_next': len(rows) > 50,
                  'page': page, 'query': query, 'filters': filters, 'beijing_time': beijing_time})


@router.get('/usage/export.csv')
def export_usage(request: Request, user_id: int | None = Depends(optional_user_id), event_type: str = '',
                 start_date: str = '', end_date: str = '', user: User = Depends(require_teacher),
                 db: Session = Depends(get_db)):
    stmt = filtered_usage(user_id, event_type, start_date, end_date)
    # Fix the selected rows before adding the export's own audit event.
    last_id = db.scalar(select(func.max(UsageEvent.id))) or 0
    stmt = stmt.where(UsageEvent.id <= last_id)
    count = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    log_event(db, 'usage_csv_export', user_id=user.id, request=request,
              payload={'filters': {'user_id': user_id, 'event_type': event_type,
                                   'start_date': start_date, 'end_date': end_date}, 'count': count})
    db.commit()
    return StreamingResponse(stream_usage(stmt), media_type='text/csv; charset=utf-8',
                             headers={'Content-Disposition': 'attachment; filename="usage.csv"', 'Cache-Control': 'no-store'})
