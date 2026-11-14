from fastapi import APIRouter, Request

from app.templating import render

router = APIRouter()


@router.get("/")
def home(request: Request):
    return render(request, "index.html")
