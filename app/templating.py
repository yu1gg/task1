from fastapi import Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

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
    ctx = {
        "request": request,
        "user": None,
        "role_label": "",
        "flashes": request.session.pop("_flashes", []),
    }
    if context:
        ctx.update(context)
    return templates.TemplateResponse(template_name, ctx, status_code=status_code)
