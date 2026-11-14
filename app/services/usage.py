from fastapi import Request

from app.models import UsageEvent


def log_event(
    db,
    event_type: str,
    user_id: int | None = None,
    request: Request | None = None,
    payload: dict | None = None,
) -> None:
    ip = ""
    user_agent = ""
    if request is not None:
        ip = request.client.host if request.client else ""
        user_agent = request.headers.get("user-agent", "")
    db.add(
        UsageEvent(
            user_id=user_id,
            event_type=event_type,
            payload_json=payload or {},
            ip=ip[:60],
            user_agent=user_agent[:250],
        )
    )
