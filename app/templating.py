from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.db import SessionLocal
from app.models import User

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)

ROLE_LABELS = {"student": "学生", "teacher": "教师", "alumni": "校友"}


def flash(request: Request, message: str, category: str = "info") -> None:
    request.session.setdefault("_flashes", []).append(
        {"message": message, "category": category}
    )


def render(
    request: Request,
    template_name: str,
    context: dict | None = None,
    status_code: int = 200,
):
    user = None
    user_id = request.session.get("user_id")
    if user_id:
        with SessionLocal() as db:
            user = db.get(User, user_id)

    ctx = {
        "user": user,
        "role_label": ROLE_LABELS.get(user.role, user.role) if user else "",
        "flashes": request.session.pop("_flashes", []),
    }
    if context:
        ctx.update(context)
    return templates.TemplateResponse(
        request, template_name, ctx, status_code=status_code
    )
