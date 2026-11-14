"""Student-owned, asynchronous audio interview endpoints."""
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from app.auth import require_student
from app.config import settings
from app.db import get_db
from app.models import Interview, InterviewTurn, Job, Resume, StudentProfile, User
from app.services.audio import AudioError, check_tools, media_root, resolve_media
from app.services.usage import log_event
from app.templating import render

router = APIRouter()
MAX_UPLOAD = 20 * 1024 * 1024


def readiness():
    return {"llm": bool(settings.deepseek_api_key), "speech": bool(settings.siliconflow_api_key), "media": check_tools()}


def owned(db, iid, user):
    item = db.scalar(select(Interview).where(Interview.id == iid, Interview.student_id == user.id))
    if item is None:
        raise HTTPException(404, "面试不存在")
    return item


def owned_turn(db, iid, tid, user):
    item = owned(db, iid, user)
    turn = db.scalar(select(InterviewTurn).where(InterviewTurn.id == tid, InterviewTurn.interview_id == iid))
    if turn is None:
        raise HTTPException(404, "题目不存在")
    return item, turn


def current_turn(db, item, turn):
    last = db.scalar(select(func.max(InterviewTurn.seq)).where(InterviewTurn.interview_id == item.id))
    if item.status != "in_progress" or turn.seq != last:
        raise HTTPException(409, "此题不再接受回答")


def list_page(request, db, user, selected_job=None, error=None, status_code=200):
    return render(request, "interviews/list.html", {
        "interviews": db.scalars(select(Interview).where(Interview.student_id == user.id).order_by(Interview.started_at.desc())).all(),
        "jobs": db.scalars(select(Job).where(Job.status == "open").options(selectinload(Job.company)).order_by(Job.created_at.desc())).all(),
        "resumes": db.scalars(select(Resume).where(Resume.student_id == user.id).order_by(Resume.updated_at.desc())).all(),
        "selected_job": selected_job, "error": error, "readiness": readiness(), "question_count": settings.interview_question_count,
    }, status_code=status_code)


@router.get("/interviews")
def interview_list(request: Request, job_id: int | None = None, user: User = Depends(require_student), db: Session = Depends(get_db)):
    profile = db.get(StudentProfile, user.id)
    return list_page(request, db, user, job_id or (profile.target_job_id if profile else None))


@router.post("/interviews")
def create_interview(request: Request, job_id: int = Form(...), round: str = Form("tech"), resume_id: str = Form(""),
                     user: User = Depends(require_student), db: Session = Depends(get_db)):
    if round not in ("tech", "hr"):
        raise HTTPException(422, "轮次必须为技术面或HR面")
    job = db.scalar(select(Job).where(Job.id == job_id, Job.status == "open").options(selectinload(Job.skills)))
    if job is None:
        raise HTTPException(404, "岗位不存在或已关闭")
    resume = None
    if resume_id:
        if not resume_id.isdigit() or len(resume_id) > 9:
            raise HTTPException(422, "简历编号无效")
        resume = db.scalar(select(Resume).where(Resume.id == int(resume_id), Resume.student_id == user.id))
        if resume is None:
            raise HTTPException(404, "简历不存在")
    profile = db.get(StudentProfile, user.id)
    if profile is None:
        return list_page(request, db, user, job.id, "请先完善个人资料。", 422)
    if not all(readiness().values()):
        return list_page(request, db, user, job.id, "语音面试配置未齐全，请配置 DeepSeek、SiliconFlow 及 ffmpeg/ffprobe 后重试。", 503)
    # Keep only interview-relevant fields; contact details are not needed by the AI.
    profile_data = {"summary": profile.summary, "education": profile.education_json, "skills": profile.skills_json,
                    "projects": profile.projects_json, "internships": profile.internships_json, "awards": profile.awards_json}
    resume_data = {key: value for key, value in resume.content_json.items() if key not in ("phone", "email", "name")} if resume else None
    context = {
        "job": {"title": job.title, "description": job.description[:4000], "requirements": job.requirements[:4000],
                "skills": [{"name": s.name, "importance": s.importance, "required_level": s.required_level} for s in job.skills]},
        "profile": profile_data, "resume": resume_data, "resume_id": resume.id if resume else None,
        "resume_version": resume.version if resume else None, "question_count": settings.interview_question_count,
    }
    item = Interview(student_id=user.id, job_id=job.id, round=round, status="preparing", context_json=context)
    db.add(item); db.flush()
    log_event(db, "interview_start", user_id=user.id, request=request, payload={"interview_id": item.id, "job_id": job.id, "round": round})
    db.commit()
    return RedirectResponse(f"/interviews/{item.id}", status_code=303)


@router.get("/interviews/{interview_id}")
def interview_room(request: Request, interview_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)):
    return render(request, "interviews/room.html", {"interview": owned(db, interview_id, user)})


@router.get("/interviews/{interview_id}/status")
def interview_status(interview_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)):
    item = owned(db, interview_id, user)
    turns = db.scalars(select(InterviewTurn).where(InterviewTurn.interview_id == item.id).order_by(InterviewTurn.seq)).all()
    data = []
    for turn in turns:
        base = f"/interviews/{item.id}/turns/{turn.id}"
        data.append({"id": turn.id, "seq": turn.seq, "question": turn.question, "status": turn.status,
                     "transcript": turn.answer_transcript or "", "feedback": turn.ai_feedback or "", "scores": turn.score_json,
                     "error": turn.error_message, "question_audio_url": base + "/question-audio" if turn.question_audio_path else None,
                     "answer_audio_url": base + "/answer-audio" if turn.answer_audio_path else None})
    return JSONResponse({"id": item.id, "status": item.status, "round": item.round,
                         "question_count": item.context_json.get("question_count", settings.interview_question_count), "turns": data,
                         "error": (item.report_json or {}).get("error"),
                         "report_url": f"/interviews/{item.id}/report" if item.status == "completed" else None},
                        headers={"Cache-Control": "no-store"})


@router.post("/interviews/{interview_id}/turns/{turn_id}/answer")
async def upload_answer(request: Request, interview_id: int, turn_id: int, file: UploadFile = File(...),
                        user: User = Depends(require_student), db: Session = Depends(get_db)):
    item, turn = owned_turn(db, interview_id, turn_id, user)
    current_turn(db, item, turn)
    if turn.status not in ("waiting", "failed"):
        raise HTTPException(409, "回答已提交或正在处理，请勿重复提交")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".wav", ".mp3", ".m4a", ".mp4", ".webm", ".ogg", ".aac", ".flac"):
        suffix = ".bin"
    name = uuid4().hex + suffix
    destination = media_root() / name
    temp = destination.with_suffix(destination.suffix + ".part")
    old_path = turn.answer_audio_path
    accepted = False
    try:
        size = 0
        with temp.open("xb") as handle:
            while chunk := await file.read(64 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD:
                    raise HTTPException(413, "音频大小不能超过20MB")
                handle.write(chunk)
        if size == 0:
            raise HTTPException(422, "录音为空，请重新录制或选择文件")
        temp.replace(destination)
        result = db.execute(update(InterviewTurn).where(InterviewTurn.id == turn.id, InterviewTurn.status.in_(("waiting", "failed")))
                            .values(answer_audio_path=name, status="queued", answer_transcript=None, ai_feedback=None, score_json=None, error_message=None),
                            execution_options={"synchronize_session": False})
        if result.rowcount != 1:
            db.rollback()
            raise HTTPException(409, "回答已由另一页面提交")
        log_event(db, "interview_answer_submit", user_id=user.id, request=request,
                  payload={"interview_id": item.id, "turn_id": turn.id})
        db.commit(); accepted = True
    finally:
        await file.close()
        temp.unlink(missing_ok=True)
        if not accepted:
            destination.unlink(missing_ok=True)
    if old_path and old_path != name:
        try:
            resolve_media(old_path).unlink(missing_ok=True)
        except (AudioError, ValueError, OSError):
            pass  # A missing superseded upload must not undo the newly accepted answer.
    return JSONResponse({"turn_id": turn.id, "status": "queued"}, status_code=202)


@router.post("/interviews/{interview_id}/turns/{turn_id}/retry")
def retry_turn(request: Request, interview_id: int, turn_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)):
    item, turn = owned_turn(db, interview_id, turn_id, user)
    current_turn(db, item, turn)
    try:
        if not turn.answer_audio_path or not resolve_media(turn.answer_audio_path).is_file():
            raise ValueError("missing")
    except (AudioError, ValueError):
        raise HTTPException(409, "回答文件缺失，请重新上传")
    result = db.execute(update(InterviewTurn).where(InterviewTurn.id == turn.id, InterviewTurn.status == "failed")
                        .values(status="queued", error_message=None), execution_options={"synchronize_session": False})
    if result.rowcount != 1:
        raise HTTPException(409, "此题不处于失败状态")
    log_event(db, "interview_answer_retry", user_id=user.id, request=request, payload={"interview_id": item.id, "turn_id": turn.id})
    db.commit()
    return JSONResponse({"turn_id": turn.id, "status": "queued"}, status_code=202)


@router.post("/interviews/{interview_id}/retry")
def retry_interview(request: Request, interview_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)):
    item = owned(db, interview_id, user)
    target = {"setup_failed": "preparing", "report_failed": "report_pending"}.get(item.status)
    if target is None:
        raise HTTPException(409, "面试不处于可重试状态")
    result = db.execute(update(Interview).where(Interview.id == item.id, Interview.status == item.status)
                        .values(status=target, report_json=None), execution_options={"synchronize_session": False})
    if result.rowcount != 1:
        raise HTTPException(409, "重试已由另一页面提交")
    log_event(db, "interview_retry", user_id=user.id, request=request, payload={"interview_id": item.id, "status": target})
    db.commit()
    return JSONResponse({"status": target}, status_code=202)


def audio_response(db, iid, tid, user, field):
    _, turn = owned_turn(db, iid, tid, user)
    relative = getattr(turn, field)
    try:
        path = resolve_media(relative) if relative else None
        if path is None or not path.is_file():
            raise ValueError("missing")
    except (AudioError, ValueError):
        raise HTTPException(404, "音频不存在")
    return FileResponse(path, headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/interviews/{interview_id}/turns/{turn_id}/question-audio")
def question_audio(interview_id: int, turn_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)):
    return audio_response(db, interview_id, turn_id, user, "question_audio_path")


@router.get("/interviews/{interview_id}/turns/{turn_id}/answer-audio")
def answer_audio(interview_id: int, turn_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)):
    return audio_response(db, interview_id, turn_id, user, "answer_audio_path")


@router.get("/interviews/{interview_id}/report")
def interview_report(request: Request, interview_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)):
    item = owned(db, interview_id, user)
    if item.status != "completed" or not item.report_json:
        raise HTTPException(409, "面试尚未完成，报告暂不可用")
    turns = db.scalars(select(InterviewTurn).where(InterviewTurn.interview_id == item.id).order_by(InterviewTurn.seq)).all()
    return render(request, "interviews/report.html", {"interview": item, "turns": turns, "report": item.report_json})
