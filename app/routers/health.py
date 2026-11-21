from urllib.request import getproxies, proxy_bypass

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db

router = APIRouter()


@router.get("/healthz")
def healthz(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "ok"}


@router.get("/healthz/local-ai")
def local_ai_health(request: Request, db: Session = Depends(get_db)):
    if not request.client or request.client.host not in {"127.0.0.1", "::1"}:
        raise HTTPException(status_code=404)
    proxies = getproxies()
    if (
        ((proxies.get("http") or proxies.get("all")) and not proxy_bypass("127.0.0.1"))
        or settings.deepseek_base_url != "http://127.0.0.1:11434/v1"
        or settings.speech_base_url != "http://127.0.0.1:8766/v1"
        or not settings.deepseek_api_key
        or not settings.siliconflow_api_key
        or request.app.state.interview_worker is None
        or request.app.state.resume_export_worker is None
    ):
        raise HTTPException(status_code=503, detail="Local AI configuration or workers are not ready")
    db.execute(text("SELECT 1"))
    return {
        "status": "ok", "service": "task1-local-ai",
        "llm_model": settings.llm_model, "asr_model": settings.asr_model,
        "tts_model": settings.tts_model, "tts_voice": settings.tts_voice,
        "llm_structured_output": settings.llm_structured_output,
    }
