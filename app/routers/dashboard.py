from fastapi import APIRouter, Depends, Request

from app.auth import require_user
from app.models import User
from app.templating import render

router = APIRouter()


@router.get("/dashboard")
def dashboard(request: Request, user: User = Depends(require_user)):
    return render(request, "dashboard/placeholder.html", {"user": user})
