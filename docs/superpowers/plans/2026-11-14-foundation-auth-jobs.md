# Foundation, Auth, Jobs & Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Execution note (2026-11-14):** The Git repository is already initialized on branch `p1-foundation` with `origin` configured. Skip the `git init` / branch / remote-add steps in Task 1; only add and commit. Do not push.

**Goal:** Build the first runnable vertical slice: a FastAPI web app with registration/login, role dashboards, job posting with AI skill extraction, student skill self-assessment, basic matching, and a seeded demo dataset.

**Architecture:** Single FastAPI application with Jinja2 server-rendered pages, SQLAlchemy 2.0 over SQLite, signed-cookie sessions, and a thin service layer for LLM calls, text parsing, matching, and usage logging. Templates use vendored Bootstrap 5 with a small custom stylesheet and minimal vanilla JS.

**Tech Stack:** Python 3.10+, FastAPI, Jinja2, SQLAlchemy 2.0, SQLite (WAL), bcrypt, httpx, pytest, Bootstrap 5.

---

## File Structure

| Path | Responsibility |
|---|---|
| `app/config.py` | Environment-backed settings |
| `app/db.py` | Engine, session factory, `get_db`, `init_db` |
| `app/models.py` | All core SQLAlchemy models |
| `app/auth.py` | Password hashing, session user lookup, role guards |
| `app/templating.py` | Jinja2 environment, `render`, flash helpers |
| `app/schemas.py` | Pydantic schemas for LLM structured output |
| `app/main.py` | App factory, middleware, router registration, lifespan |
| `app/routers/home.py` | Landing page |
| `app/routers/health.py` | `/healthz` |
| `app/routers/auth.py` | Register, login, logout |
| `app/routers/dashboard.py` | Role-specific dashboards |
| `app/routers/jobs.py` | Job CRUD, AI extraction, skill editing |
| `app/routers/profile.py` | Student profile and skill self-assessment |
| `app/services/llm.py` | DeepSeek-compatible JSON client |
| `app/services/skills.py` | Skill name normalization |
| `app/services/job_skills.py` | Prompt + extraction service |
| `app/services/matching.py` | Explainable match score and gap list |
| `app/services/profile_text.py` | Parse/format textarea input to JSON |
| `app/services/usage.py` | Usage event logging |
| `app/templates/**` | Jinja2 templates |
| `app/static/**` | Vendored Bootstrap, custom CSS, minimal JS |
| `scripts/seed.py` | Demo teacher/student/job/skills seed |
| `tests/**` | Pytest suite |
| `requirements.txt`, `.env.example`, `.gitignore`, `pytest.ini`, `README.md` | Project setup |

---

## Task 1: Bootstrap the app, health check, and landing page

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `README.md`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `app/templating.py`
- Create: `app/main.py`
- Create: `app/routers/__init__.py`
- Create: `app/routers/health.py`
- Create: `app/routers/home.py`
- Create: `app/templates/base.html`
- Create: `app/templates/index.html`
- Create: `app/static/css/app.css`
- Create: `app/static/js/app.js`
- Create: `tests/conftest.py`
- Create: `tests/__init__.py`
- Create: `tests/test_health.py`
- Download: `app/static/vendor/bootstrap.min.css`
- Download: `app/static/vendor/bootstrap.bundle.min.js`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_health.py`:

```python
def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "AI 职业发展平台" in response.text
```

Create `tests/conftest.py`:

```python
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_app.db"
os.environ["SESSION_SECRET"] = "test-secret"
os.environ["TEACHER_INVITE_CODE"] = "teacher-secret"
os.environ["DEEPSEEK_API_KEY"] = "test-key"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
```

Create `tests/__init__.py` (empty file).

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/test_health.py -v
```

Expected: collection error because `app.main` does not exist yet (`ModuleNotFoundError: No module named 'app'`).

- [ ] **Step 3: Create dependency and environment files**

Create `requirements.txt`:

```text
fastapi==0.115.6
uvicorn[standard]==0.34.0
jinja2==3.1.5
python-multipart==0.0.20
sqlalchemy==2.0.36
pydantic==2.10.4
pydantic-settings==2.7.1
bcrypt==4.2.1
httpx==0.28.1
itsdangerous==2.2.0
pytest==8.3.4
```

Create `.gitignore`:

```text
.venv/
__pycache__/
*.pyc
.env
data/
test_app.db
.pytest_cache/
*.mp4
*.wav
*.mp3
*.zip
AI赋能职业发展和面试指导产品.docx
guide.txt
```

Create `.env.example`:

```text
DATABASE_URL=sqlite:///./data/app.db
SESSION_SECRET=change-me-to-a-long-random-string
TEACHER_INVITE_CODE=change-me-to-a-strong-code
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=2
DATA_DIR=data
```

Create `pytest.ini`:

```ini
[pytest]
testpaths = tests
addopts = -q
```

Create `README.md`:

```markdown
# AI 职业发展与面试指导平台

课程项目：从企业岗位技能拆解，到学生能力自评、AI 简历与 AI 视频面试。

## 本地运行

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

打开 <http://127.0.0.1:8000>。

## 测试

```bash
pytest
```

## 远程仓库

```bash
git remote add origin https://github.com/yu1gg/task1.git
```

首次推送前先确认本地提交内容。
```

Install dependencies:

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

Expected: `Successfully installed ...` with FastAPI, SQLAlchemy, bcrypt, pytest, httpx.

- [ ] **Step 4: Create settings and templating helpers**

Create `app/__init__.py` (empty file).

Create `app/config.py`:

```python
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI 职业发展平台"
    database_url: str = "sqlite:///./data/app.db"
    session_secret: str = "dev-only-change-me"
    teacher_invite_code: str = ""
    data_dir: Path = Path("data")
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2


settings = Settings()
```

Create `app/templating.py`:

```python
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

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
    ctx = {
        "user": None,
        "role_label": "",
        "flashes": request.session.pop("_flashes", []),
    }
    if context:
        ctx.update(context)
    return templates.TemplateResponse(
        request, template_name, ctx, status_code=status_code
    )
```

- [ ] **Step 5: Create the minimal app and routers**

Create `app/routers/__init__.py` (empty file).

Create `app/routers/health.py`:

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
def healthz():
    return {"status": "ok"}
```

Create `app/routers/home.py`:

```python
from fastapi import APIRouter, Request

from app.templating import render

router = APIRouter()


@router.get("/")
def home(request: Request):
    return render(request, "index.html")
```

Create `app/main.py`:

```python
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.routers import health, home


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        same_site="lax",
        https_only=False,
        max_age=7 * 24 * 3600,
    )
    app.mount(
        "/static",
        StaticFiles(directory=str(Path(__file__).resolve().parent / "static")),
        name="static",
    )
    app.include_router(health.router)
    app.include_router(home.router)
    return app


app = create_app()
```

- [ ] **Step 6: Download Bootstrap and create base templates**

Run:

```bash
mkdir -p app/static/vendor
curl -L -o app/static/vendor/bootstrap.min.css https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css
curl -L -o app/static/vendor/bootstrap.bundle.min.js https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js
wc -c app/static/vendor/bootstrap.min.css app/static/vendor/bootstrap.bundle.min.js
```

Expected: CSS file is roughly 230 KB and JS file is roughly 80 KB.

If either download is 0 bytes or contains a 404 page, use the domestic mirror:

```bash
curl -L -o app/static/vendor/bootstrap.min.css https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/5.3.3/css/bootstrap.min.css
curl -L -o app/static/vendor/bootstrap.bundle.min.js https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/5.3.3/js/bootstrap.bundle.min.js
```

Create `app/templates/base.html`:

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}AI 职业发展平台{% endblock %}</title>
  <link rel="stylesheet" href="/static/vendor/bootstrap.min.css">
  <link rel="stylesheet" href="/static/css/app.css">
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark bg-primary">
  <div class="container">
    <a class="navbar-brand" href="/">AI 职业发展平台</a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#mainNav"
            aria-controls="mainNav" aria-expanded="false" aria-label="切换导航">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="mainNav">
      <ul class="navbar-nav me-auto">
        <li class="nav-item"><a class="nav-link" href="/jobs">岗位</a></li>
        {% if user and user.role == 'student' %}
        <li class="nav-item"><a class="nav-link" href="/profile">我的资料</a></li>
        {% endif %}
      </ul>
      <ul class="navbar-nav">
        {% if user %}
        <li class="nav-item">
          <span class="navbar-text me-3">{{ user.real_name }}{% if role_label %}（{{ role_label }}）{% endif %}</span>
        </li>
        <li class="nav-item">
          <form method="post" action="/logout" class="d-inline">
            <button class="btn btn-outline-light btn-sm" type="submit">退出</button>
          </form>
        </li>
        {% else %}
        <li class="nav-item"><a class="nav-link" href="/login">登录</a></li>
        <li class="nav-item"><a class="nav-link" href="/register">注册</a></li>
        {% endif %}
      </ul>
    </div>
  </div>
</nav>

<main class="container py-4">
  {% for f in flashes %}
  <div class="alert alert-{{ f.category }} alert-dismissible fade show" role="alert">
    {{ f.message }}
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="关闭"></button>
  </div>
  {% endfor %}
  {% block content %}{% endblock %}
</main>

<script src="/static/vendor/bootstrap.bundle.min.js"></script>
<script src="/static/js/app.js"></script>
</body>
</html>
```

Create `app/templates/index.html`:

```html
{% extends "base.html" %}
{% block title %}AI 职业发展平台{% endblock %}
{% block content %}
<div class="p-5 mb-4 bg-white rounded-3 shadow-sm">
  <h1 class="display-6 fw-bold">AI 职业发展平台</h1>
  <p class="lead text-muted">从岗位技能拆解，到 AI 简历与视频面试，帮你把能力差距变成成长路径。</p>
  <a class="btn btn-primary btn-lg" href="/register">开始使用</a>
  {% if not user %}
  <a class="btn btn-outline-secondary btn-lg ms-2" href="/login">已有账号，登录</a>
  {% endif %}
</div>
<div class="row g-3">
  <div class="col-md-4">
    <div class="card h-100"><div class="card-body">
      <h5 class="card-title">岗位技能拆解</h5>
      <p class="card-text text-muted">录入企业岗位，AI 自动提取必须技能与要求等级。</p>
    </div></div>
  </div>
  <div class="col-md-4">
    <div class="card h-100"><div class="card-body">
      <h5 class="card-title">能力差距清晰</h5>
      <p class="card-text text-muted">按岗位查看自己的技能差距，知道下一步学什么。</p>
    </div></div>
  </div>
  <div class="col-md-4">
    <div class="card h-100"><div class="card-body">
      <h5 class="card-title">AI 简历与面试</h5>
      <p class="card-text text-muted">生成针对性简历，并通过 AI 视频面试发现短板。</p>
    </div></div>
  </div>
</div>
{% endblock %}
```

Create `app/static/css/app.css`:

```css
:root {
  --brand: #1f4e79;
  --page-bg: #f6f8fb;
}

body {
  background: var(--page-bg);
  color: #1f2933;
}

.navbar.bg-primary {
  background-color: var(--brand) !important;
}

.card {
  border: 0;
  border-radius: 14px;
  box-shadow: 0 1px 3px rgba(16, 24, 40, 0.08);
}

.card-header {
  background: #fff;
  border-bottom: 1px solid #eef2f7;
  font-weight: 600;
}

.btn-primary {
  background-color: var(--brand);
  border-color: var(--brand);
}

.btn-primary:hover {
  background-color: #163a5a;
  border-color: #163a5a;
}

.page-title {
  font-size: 1.35rem;
  font-weight: 700;
  margin-bottom: 1rem;
}

.text-muted {
  color: #667085 !important;
}

.table > :not(caption) > * > * {
  padding: 0.65rem 0.75rem;
}

.form-label {
  font-weight: 500;
}

.form-hint {
  font-size: 0.8rem;
  color: #667085;
}
```

Create `app/static/js/app.js`:

```javascript
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-add-skill-row]").forEach((button) => {
    button.addEventListener("click", () => {
      const tbody = document.querySelector("#skill-rows");
      if (!tbody) return;
      const row = tbody.querySelector("tr.skill-row");
      if (!row) return;
      const clone = row.cloneNode(true);
      clone.querySelectorAll("input, select").forEach((input) => {
        if (input.tagName === "SELECT") {
          input.selectedIndex = 0;
        } else {
          input.value = "";
        }
      });
      tbody.appendChild(clone);
    });
  });
});
```

- [ ] **Step 7: Run the tests to verify they pass**

Run:

```bash
pytest tests/test_health.py -v
```

Expected:

```text
tests/test_health.py::test_healthz PASSED
tests/test_health.py::test_home_page PASSED
```

- [ ] **Step 8: Initialize Git and commit**

Run:

```bash
git init
git branch -M main
git remote add origin https://github.com/yu1gg/task1.git
git add .gitignore .env.example requirements.txt pytest.ini README.md app tests docs
git commit -m "chore: bootstrap FastAPI app with health check and landing page"
```

Do **not** run `git push` yet. Push only after the user explicitly confirms.

---

## Task 2: Database connection and full core schema

**Files:**
- Create: `app/db.py`
- Create: `app/models.py`
- Modify: `app/main.py`
- Modify: `app/routers/health.py`
- Modify: `tests/conftest.py`
- Modify: `tests/test_health.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write the failing tests**

Update `tests/test_health.py`:

```python
def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "AI 职业发展平台" in response.text
```

Create `tests/test_db.py`:

```python
from sqlalchemy import select

from app.db import SessionLocal
from app.models import StudentProfile, User


def test_create_user_and_profile():
    with SessionLocal() as db:
        user = User(
            username="dbuser",
            password_hash="x",
            real_name="测试学生",
            role="student",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        db.add(StudentProfile(user_id=user.id))
        db.commit()

        loaded = db.scalar(select(User).where(User.username == "dbuser"))
        assert loaded is not None
        assert loaded.profile is not None
        assert loaded.real_name == "测试学生"


def test_sqlite_pragmas():
    from sqlalchemy import text

    from app.db import engine

    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert connection.execute(text("PRAGMA busy_timeout")).scalar() == 5000
        assert (
            connection.execute(text("PRAGMA journal_mode")).scalar().lower()
            == "wal"
        )
```

Update `tests/conftest.py`:

```python
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_app.db"
os.environ["SESSION_SECRET"] = "test-secret"
os.environ["TEACHER_INVITE_CODE"] = "teacher-secret"
os.environ["DEEPSEEK_API_KEY"] = "test-key"

import pytest
from fastapi.testclient import TestClient

from app import models  # noqa: F401
from app.db import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/test_health.py tests/test_db.py -v
```

Expected: fails because `app.db` and `app.models` do not exist.

- [ ] **Step 3: Create the database module**

Create `app/db.py`:

```python
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    future=True,
)

if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Create all core models**

Create `app/models.py`:

```python
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    real_name: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(16), default="student", index=True)
    major: Mapped[str | None] = mapped_column(String(64), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    profile: Mapped[Optional["StudentProfile"]] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    education_json: Mapped[list] = mapped_column(JSON, default=list)
    skills_json: Mapped[list] = mapped_column(JSON, default=list)
    projects_json: Mapped[list] = mapped_column(JSON, default=list)
    internships_json: Mapped[list] = mapped_column(JSON, default=list)
    awards_json: Mapped[list] = mapped_column(JSON, default=list)
    target_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("jobs.id"), nullable=True
    )
    availability_from: Mapped[str | None] = mapped_column(String(20), nullable=True)
    availability_note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="profile")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    industry: Mapped[str | None] = mapped_column(String(80), nullable=True)
    size: Mapped[str | None] = mapped_column(String(40), nullable=True)
    location: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    jobs: Mapped[list["Job"]] = relationship(back_populates="company")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    requirements: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str | None] = mapped_column(String(80), nullable=True)
    salary_range: Mapped[str | None] = mapped_column(String(60), nullable=True)
    headcount: Mapped[int] = mapped_column(Integer, default=1)
    deadline: Mapped[str | None] = mapped_column(String(20), nullable=True)
    expected_start_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped["Company"] = relationship(back_populates="jobs")
    skills: Mapped[list["JobSkill"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="JobSkill.sort_order",
    )


class JobSkill(Base):
    __tablename__ = "job_skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    category: Mapped[str] = mapped_column(String(40), default="通用")
    importance: Mapped[str] = mapped_column(String(8), default="nice")
    required_level: Mapped[int] = mapped_column(Integer, default=3)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    job: Mapped["Job"] = relationship(back_populates="skills")


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(120), default="我的简历")
    content_json: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    round: Mapped[str] = mapped_column(String(16), default="tech")
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    report_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    total_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    turns: Mapped[list["InterviewTurn"]] = relationship(
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="InterviewTurn.seq",
    )


class InterviewTurn(Base):
    __tablename__ = "interview_turns"

    id: Mapped[int] = mapped_column(primary_key=True)
    interview_id: Mapped[int] = mapped_column(
        ForeignKey("interviews.id"), index=True
    )
    seq: Mapped[int] = mapped_column(Integer, default=1)
    question: Mapped[str] = mapped_column(Text)
    question_audio_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    answer_video_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    answer_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    score_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="waiting")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    interview: Mapped["Interview"] = relationship(back_populates="turns")


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )


Index("ix_job_skills_job_sort", JobSkill.job_id, JobSkill.sort_order)
```

- [ ] **Step 5: Wire the database into startup and health check**

Modify `app/main.py`:

```python
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.db import init_db
from app.routers import health, home


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        same_site="lax",
        https_only=False,
        max_age=7 * 24 * 3600,
    )
    app.mount(
        "/static",
        StaticFiles(directory=str(Path(__file__).resolve().parent / "static")),
        name="static",
    )
    app.include_router(health.router)
    app.include_router(home.router)
    return app


app = create_app()
```

Modify `app/routers/health.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter()


@router.get("/healthz")
def healthz(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "ok"}
```

- [ ] **Step 6: Run the tests to verify they pass**

Run:

```bash
pytest tests/test_health.py tests/test_db.py -v
```

Expected:

```text
tests/test_health.py::test_healthz PASSED
tests/test_health.py::test_home_page PASSED
tests/test_db.py::test_create_user_and_profile PASSED
tests/test_db.py::test_sqlite_pragmas PASSED
```

- [ ] **Step 7: Commit**

Run:

```bash
git add app/db.py app/models.py app/main.py app/routers/health.py tests/conftest.py tests/test_health.py tests/test_db.py
git commit -m "feat: add SQLite schema and health check"
```

---

## Task 3: Registration, login, logout, and session-aware rendering

**Files:**
- Create: `app/auth.py`
- Create: `app/services/__init__.py`
- Create: `app/services/usage.py`
- Create: `app/routers/auth.py`
- Create: `app/templates/auth/login.html`
- Create: `app/templates/auth/register.html`
- Modify: `app/templating.py`
- Modify: `app/main.py`
- Create: `app/routers/dashboard.py`
- Create: `app/templates/dashboard/placeholder.html`
- Create: `tests/helpers.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/helpers.py`:

```python
def register(
    client,
    username="stu1",
    password="pass123",
    real_name="张三",
    role="student",
    teacher_code="",
    major="人工智能",
    grade="2024",
):
    return client.post(
        "/register",
        data={
            "username": username,
            "password": password,
            "real_name": real_name,
            "role": role,
            "teacher_code": teacher_code,
            "major": major,
            "grade": grade,
        },
        follow_redirects=False,
    )


def login(client, username="stu1", password="pass123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def make_student(client, username="stu1", real_name="张三"):
    return register(client, username=username, real_name=real_name)


def make_teacher(client, username="teacher1", real_name="李老师"):
    return register(
        client,
        username=username,
        real_name=real_name,
        role="teacher",
        teacher_code="teacher-secret",
        major="",
        grade="",
    )


def make_alumni(client, username="alumni1", real_name="王校友"):
    return register(
        client,
        username=username,
        real_name=real_name,
        role="alumni",
        major="",
        grade="",
    )
```

Create `tests/test_auth.py`:

```python
from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from tests.helpers import login, make_student, make_teacher, register


def test_register_student_and_login(client):
    response = register(client)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"

    client.post("/logout", follow_redirects=False)

    response = login(client)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"

    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "张三" in response.text


def test_duplicate_username_shows_error(client):
    register(client)
    response = register(client)
    assert response.status_code == 303

    response = client.get("/register")
    assert "用户名已存在" in response.text


def test_teacher_requires_invite_code(client):
    response = register(
        client,
        username="teacher_bad",
        real_name="错误老师",
        role="teacher",
        teacher_code="wrong-code",
        major="",
        grade="",
    )
    assert response.status_code == 303

    response = client.get("/register")
    assert "教师邀请码错误" in response.text


def test_teacher_registration_disabled_when_no_invite_code(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "teacher_invite_code", "")

    response = register(
        client,
        username="teacher_disabled",
        real_name="未开启老师",
        role="teacher",
        teacher_code="",
        major="",
        grade="",
    )
    assert response.status_code == 303

    response = client.get("/register")
    assert "教师注册未开启" in response.text


def test_teacher_can_register_with_invite_code(client):
    response = make_teacher(client)
    assert response.status_code == 303
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "李老师" in response.text


def test_password_is_hashed_and_not_stored_plaintext(client):
    make_student(client)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == "stu1"))
        assert user is not None
        assert user.password_hash != "pass123"
        assert user.password_hash.startswith("$2")


def test_logout_clears_session(client):
    make_student(client)
    client.post("/logout", follow_redirects=False)
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/test_auth.py -v
```

Expected: fails with 404 for `/register` and `/login`.

- [ ] **Step 3: Create usage logging and auth helpers**

Create `app/services/__init__.py` (empty file).

Create `app/services/usage.py`:

```python
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
```

Create `app/auth.py`:

```python
import bcrypt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except ValueError:
        return False


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)


def require_user(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
    return user


def require_student(user: User = Depends(require_user)) -> User:
    if user.role != "student":
        raise HTTPException(status_code=403, detail="仅学生可操作")
    return user


def require_teacher(user: User = Depends(require_user)) -> User:
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="仅教师可操作")
    return user
```

- [ ] **Step 4: Make `render` load the current user**

Modify `app/templating.py`:

```python
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
```

- [ ] **Step 5: Create the authentication router**

Create `app/routers/auth.py`:

```python
from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import hash_password, verify_password
from app.config import settings
from app.db import get_db
from app.models import StudentProfile, User
from app.services.usage import log_event
from app.templating import flash, render

router = APIRouter()

VALID_ROLES = {"student", "teacher", "alumni"}


@router.get("/register")
def register_page(request: Request):
    return render(request, "auth/register.html")


@router.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    real_name: str = Form(...),
    role: str = Form("student"),
    teacher_code: str = Form(""),
    major: str = Form(""),
    grade: str = Form(""),
    db: Session = Depends(get_db),
):
    username = username.strip()
    real_name = real_name.strip()

    if len(username) < 3:
        flash(request, "用户名至少 3 位", "danger")
        return RedirectResponse("/register", status_code=303)
    if len(password) < 6:
        flash(request, "密码至少 6 位", "danger")
        return RedirectResponse("/register", status_code=303)
    if len(password.encode("utf-8")) > 72:
        flash(request, "密码过长，请控制在 72 字节以内", "danger")
        return RedirectResponse("/register", status_code=303)
    if not real_name:
        flash(request, "请填写真实姓名", "danger")
        return RedirectResponse("/register", status_code=303)
    if role not in VALID_ROLES:
        flash(request, "角色不合法", "danger")
        return RedirectResponse("/register", status_code=303)

    existing = db.scalar(select(User).where(User.username == username))
    if existing is not None:
        flash(request, "用户名已存在，请换一个", "danger")
        return RedirectResponse("/register", status_code=303)

    if role == "teacher":
        if not settings.teacher_invite_code:
            flash(request, "教师注册未开启，请联系管理员", "danger")
            return RedirectResponse("/register", status_code=303)
        if teacher_code.strip() != settings.teacher_invite_code:
            flash(request, "教师邀请码错误", "danger")
            return RedirectResponse("/register", status_code=303)

    user = User(
        username=username,
        password_hash=hash_password(password),
        real_name=real_name,
        role=role,
        major=major.strip() or None,
        grade=grade.strip() or None,
    )
    db.add(user)
    db.flush()

    if role == "student":
        db.add(StudentProfile(user_id=user.id))

    log_event(db, "register", user_id=user.id, request=request, payload={"role": role})
    db.commit()

    request.session["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/login")
def login_page(request: Request):
    return render(request, "auth/login.html")


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.username == username.strip()))
    if user is None or not verify_password(password, user.password_hash):
        flash(request, "用户名或密码错误", "danger")
        return RedirectResponse("/login", status_code=303)

    user.last_login_at = datetime.utcnow()
    log_event(db, "login", user_id=user.id, request=request)
    db.commit()

    request.session["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if user_id:
        log_event(db, "logout", user_id=user_id, request=request)
        db.commit()
    request.session.clear()
    return RedirectResponse("/", status_code=303)
```

- [ ] **Step 6: Add authentication templates**

Create `app/templates/auth/login.html`:

```html
{% extends "base.html" %}
{% block title %}登录{% endblock %}
{% block content %}
<div class="row justify-content-center">
  <div class="col-md-5">
    <div class="card">
      <div class="card-header">登录</div>
      <div class="card-body">
        <form method="post" action="/login">
          <div class="mb-3">
            <label class="form-label" for="username">用户名</label>
            <input class="form-control" id="username" name="username" required autocomplete="username">
          </div>
          <div class="mb-3">
            <label class="form-label" for="password">密码</label>
            <input class="form-control" id="password" name="password" type="password" required autocomplete="current-password">
          </div>
          <button class="btn btn-primary w-100" type="submit">登录</button>
        </form>
        <p class="form-hint mt-3 mb-0">还没有账号？<a href="/register">立即注册</a></p>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

Create `app/templates/auth/register.html`:

```html
{% extends "base.html" %}
{% block title %}注册{% endblock %}
{% block content %}
<div class="row justify-content-center">
  <div class="col-md-6">
    <div class="card">
      <div class="card-header">注册</div>
      <div class="card-body">
        <form method="post" action="/register">
          <div class="row g-3">
            <div class="col-md-6">
              <label class="form-label" for="username">用户名</label>
              <input class="form-control" id="username" name="username" required minlength="3" autocomplete="username">
            </div>
            <div class="col-md-6">
              <label class="form-label" for="password">密码</label>
              <input class="form-control" id="password" name="password" type="password" required minlength="6" autocomplete="new-password">
            </div>
            <div class="col-md-6">
              <label class="form-label" for="real_name">真实姓名</label>
              <input class="form-control" id="real_name" name="real_name" required>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="role">角色</label>
              <select class="form-select" id="role" name="role">
                <option value="student">学生</option>
                <option value="alumni">校友</option>
                <option value="teacher">教师</option>
              </select>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="major">专业</label>
              <input class="form-control" id="major" name="major" placeholder="人工智能">
            </div>
            <div class="col-md-6">
              <label class="form-label" for="grade">年级</label>
              <input class="form-control" id="grade" name="grade" placeholder="2024">
            </div>
            <div class="col-12">
              <label class="form-label" for="teacher_code">教师邀请码</label>
              <input class="form-control" id="teacher_code" name="teacher_code">
              <div class="form-hint">仅教师角色需要填写，向管理员获取。</div>
            </div>
          </div>
          <button class="btn btn-primary w-100 mt-3" type="submit">注册并登录</button>
        </form>
        <p class="form-hint mt-3 mb-0">已有账号？<a href="/login">去登录</a></p>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 7: Add a minimal dashboard stub and register routers**

Create `app/routers/dashboard.py`:

```python
from fastapi import APIRouter, Depends, Request

from app.auth import require_user
from app.models import User
from app.templating import render

router = APIRouter()


@router.get("/dashboard")
def dashboard(request: Request, user: User = Depends(require_user)):
    return render(request, "dashboard/placeholder.html", {"user": user})
```

Create `app/templates/dashboard/placeholder.html`:

```html
{% extends "base.html" %}
{% block title %}工作台{% endblock %}
{% block content %}
<h1 class="page-title">工作台</h1>
<p>欢迎，{{ user.real_name }}。</p>
{% endblock %}
```

Modify `app/main.py`:

```python
from app.routers import auth, dashboard, health, home
```

and inside `create_app`:

```python
    app.include_router(health.router)
    app.include_router(home.router)
    app.include_router(auth.router)
    app.include_router(dashboard.router)
```

- [ ] **Step 8: Run the tests to verify they pass**

Run:

```bash
pytest tests/test_auth.py -v
```

Expected:

```text
tests/test_auth.py::test_register_student_and_login PASSED
tests/test_auth.py::test_duplicate_username_shows_error PASSED
tests/test_auth.py::test_teacher_requires_invite_code PASSED
tests/test_auth.py::test_teacher_registration_disabled_when_no_invite_code PASSED
tests/test_auth.py::test_teacher_can_register_with_invite_code PASSED
tests/test_auth.py::test_password_is_hashed_and_not_stored_plaintext PASSED
tests/test_auth.py::test_logout_clears_session PASSED
```

- [ ] **Step 9: Commit**

Run:

```bash
git add app/auth.py app/services app/routers/auth.py app/templating.py app/main.py app/templates/auth tests/helpers.py tests/test_auth.py
git commit -m "feat: add registration, login, logout and role guards"
```

---

## Task 4: Role-specific dashboards

**Files:**
- Modify: `app/routers/dashboard.py`
- Create: `app/templates/dashboard/student.html`
- Create: `app/templates/dashboard/teacher.html`
- Create: `app/templates/dashboard/alumni.html`
- Delete: `app/templates/dashboard/placeholder.html`
- Modify: `app/templates/base.html`
- Create: `tests/test_dashboard.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_dashboard.py`:

```python
from tests.helpers import make_alumni, make_student, make_teacher


def test_student_dashboard(client):
    make_student(client)
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "学生工作台" in response.text
    assert "张三" in response.text


def test_teacher_dashboard(client):
    make_teacher(client)
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "教师工作台" in response.text


def test_alumni_dashboard(client):
    make_alumni(client)
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "校友工作台" in response.text


def test_dashboard_requires_login(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/test_dashboard.py -v
```

Expected: fails because the placeholder dashboard does not contain the role-specific headings `学生工作台` / `教师工作台` / `校友工作台`.

- [ ] **Step 3: Replace the dashboard stub with role-specific logic**

Replace the contents of `app/routers/dashboard.py` with:

```python
from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.auth import require_user
from app.db import get_db
from app.models import Job, StudentProfile, User
from app.templating import render

router = APIRouter()


@router.get("/dashboard")
def dashboard(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if user.role == "teacher":
        student_count = (
            db.scalar(
                select(func.count())
                .select_from(User)
                .where(User.role == "student")
            )
            or 0
        )
        job_count = db.scalar(select(func.count()).select_from(Job)) or 0
        jobs = db.scalars(
            select(Job)
            .options(selectinload(Job.company))
            .order_by(Job.created_at.desc())
            .limit(5)
        ).all()
        return render(
            request,
            "dashboard/teacher.html",
            {
                "student_count": student_count,
                "job_count": job_count,
                "jobs": jobs,
            },
        )

    if user.role == "alumni":
        jobs = db.scalars(
            select(Job)
            .options(selectinload(Job.company))
            .where(Job.status == "open")
            .order_by(Job.created_at.desc())
            .limit(5)
        ).all()
        return render(request, "dashboard/alumni.html", {"jobs": jobs})

    profile = db.get(StudentProfile, user.id)
    skills = (profile.skills_json if profile else []) or []
    filled = 0
    if profile is not None:
        for value in [
            profile.summary,
            profile.education_json,
            profile.projects_json,
            profile.internships_json,
            profile.awards_json,
            profile.skills_json,
        ]:
            if value:
                filled += 1
    completion = round(filled / 6 * 100)

    jobs = db.scalars(
        select(Job)
        .options(selectinload(Job.company))
        .where(Job.status == "open")
        .order_by(Job.created_at.desc())
        .limit(5)
    ).all()

    return render(
        request,
        "dashboard/student.html",
        {
            "completion": completion,
            "skill_count": len(skills),
            "jobs": jobs,
        },
    )
```

- [ ] **Step 4: Create dashboard templates**

Create `app/templates/dashboard/student.html`:

```html
{% extends "base.html" %}
{% block title %}学生工作台{% endblock %}
{% block content %}
<h1 class="page-title">学生工作台</h1>
<div class="row g-3 mb-4">
  <div class="col-md-4">
    <div class="card h-100"><div class="card-body">
      <div class="text-muted mb-1">资料完成度</div>
      <div class="display-6 fw-bold">{{ completion }}%</div>
      <div class="progress mt-3" role="progressbar" aria-valuenow="{{ completion }}" aria-valuemin="0" aria-valuemax="100">
        <div class="progress-bar" style="width: {{ completion }}%"></div>
      </div>
      <a class="btn btn-sm btn-outline-primary mt-3" href="/profile">完善资料</a>
    </div></div>
  </div>
  <div class="col-md-4">
    <div class="card h-100"><div class="card-body">
      <div class="text-muted mb-1">已填写技能</div>
      <div class="display-6 fw-bold">{{ skill_count }}</div>
      <p class="text-muted mt-3 mb-0">技能自评越完整，岗位差距越准确。</p>
    </div></div>
  </div>
  <div class="col-md-4">
    <div class="card h-100"><div class="card-body">
      <div class="text-muted mb-1">下一步</div>
      <p class="mb-2">浏览岗位，查看能力差距。</p>
      <a class="btn btn-sm btn-primary" href="/jobs">去看岗位</a>
    </div></div>
  </div>
</div>

<div class="card">
  <div class="card-header">最新岗位</div>
  <div class="card-body p-0">
    {% if jobs %}
    <div class="list-group list-group-flush">
      {% for job in jobs %}
      <a class="list-group-item list-group-item-action" href="/jobs/{{ job.id }}">
        <div class="d-flex justify-content-between align-items-center">
          <div>
            <div class="fw-semibold">{{ job.title }}</div>
            <div class="form-hint">{{ job.company.name }}{% if job.location %} · {{ job.location }}{% endif %}</div>
          </div>
          <span class="text-muted">查看 →</span>
        </div>
      </a>
      {% endfor %}
    </div>
    {% else %}
    <div class="p-4 text-muted">还没有岗位，去发布第一个岗位吧。</div>
    {% endif %}
  </div>
</div>
{% endblock %}
```

Create `app/templates/dashboard/teacher.html`:

```html
{% extends "base.html" %}
{% block title %}教师工作台{% endblock %}
{% block content %}
<h1 class="page-title">教师工作台</h1>
<div class="row g-3 mb-4">
  <div class="col-md-4">
    <div class="card h-100"><div class="card-body">
      <div class="text-muted mb-1">学生人数</div>
      <div class="display-6 fw-bold">{{ student_count }}</div>
    </div></div>
  </div>
  <div class="col-md-4">
    <div class="card h-100"><div class="card-body">
      <div class="text-muted mb-1">岗位数量</div>
      <div class="display-6 fw-bold">{{ job_count }}</div>
    </div></div>
  </div>
  <div class="col-md-4">
    <div class="card h-100"><div class="card-body">
      <div class="text-muted mb-1">快捷操作</div>
      <a class="btn btn-sm btn-primary" href="/jobs/new">发布岗位</a>
      <a class="btn btn-sm btn-outline-primary" href="/jobs">查看岗位</a>
    </div></div>
  </div>
</div>

<div class="card">
  <div class="card-header">最近岗位</div>
  <div class="card-body p-0">
    {% if jobs %}
    <div class="list-group list-group-flush">
      {% for job in jobs %}
      <a class="list-group-item list-group-item-action" href="/jobs/{{ job.id }}">
        <div class="d-flex justify-content-between align-items-center">
          <div>
            <div class="fw-semibold">{{ job.title }}</div>
            <div class="form-hint">{{ job.company.name }}{% if job.location %} · {{ job.location }}{% endif %}</div>
          </div>
          <span class="text-muted">查看 →</span>
        </div>
      </a>
      {% endfor %}
    </div>
    {% else %}
    <div class="p-4 text-muted">还没有岗位，点击“发布岗位”开始。</div>
    {% endif %}
  </div>
</div>
{% endblock %}
```

Create `app/templates/dashboard/alumni.html`:

```html
{% extends "base.html" %}
{% block title %}校友工作台{% endblock %}
{% block content %}
<h1 class="page-title">校友工作台</h1>
<div class="card mb-4">
  <div class="card-body d-flex justify-content-between align-items-center">
    <div>
      <div class="fw-semibold">欢迎回来，{{ user.real_name }}</div>
      <div class="form-hint">你可以把知道的实习/招聘岗位分享给学弟学妹。</div>
    </div>
    <a class="btn btn-primary" href="/jobs/new">发布岗位</a>
  </div>
</div>

<div class="card">
  <div class="card-header">最新岗位</div>
  <div class="card-body p-0">
    {% if jobs %}
    <div class="list-group list-group-flush">
      {% for job in jobs %}
      <a class="list-group-item list-group-item-action" href="/jobs/{{ job.id }}">
        <div class="d-flex justify-content-between align-items-center">
          <div>
            <div class="fw-semibold">{{ job.title }}</div>
            <div class="form-hint">{{ job.company.name }}{% if job.location %} · {{ job.location }}{% endif %}</div>
          </div>
          <span class="text-muted">查看 →</span>
        </div>
      </a>
      {% endfor %}
    </div>
    {% else %}
    <div class="p-4 text-muted">还没有岗位，去发布第一个岗位吧。</div>
    {% endif %}
  </div>
</div>
{% endblock %}
```

Delete `app/templates/dashboard/placeholder.html`; it is no longer used.

- [ ] **Step 5: Add dashboard link to the navigation**

Modify `app/templates/base.html` by adding this list item inside the existing left-hand `<ul class="navbar-nav me-auto">`, before the 岗位 link:

```html
        {% if user %}
        <li class="nav-item"><a class="nav-link" href="/dashboard">工作台</a></li>
        {% endif %}
```

- [ ] **Step 6: Confirm the dashboard router is registered**

`app/main.py` already imports and includes `dashboard.router` from Task 3. Verify:

```bash
grep -n "dashboard" app/main.py
```

Expected: both the import and `app.include_router(dashboard.router)` are present. No code change.

- [ ] **Step 7: Run the tests to verify they pass**

Run:

```bash
pytest tests/test_dashboard.py -v
```

Expected:

```text
tests/test_dashboard.py::test_student_dashboard PASSED
tests/test_dashboard.py::test_teacher_dashboard PASSED
tests/test_dashboard.py::test_alumni_dashboard PASSED
tests/test_dashboard.py::test_dashboard_requires_login PASSED
```

- [ ] **Step 8: Commit**

Run:

```bash
git add app/routers/dashboard.py app/templates/dashboard app/templates/base.html app/main.py tests/test_dashboard.py
git commit -m "feat: add role-specific dashboards"
```

---

## Task 5: Job posting, listing, detail, and editing

**Files:**
- Create: `app/routers/jobs.py`
- Create: `app/templates/jobs/list.html`
- Create: `app/templates/jobs/form.html`
- Create: `app/templates/jobs/detail.html`
- Modify: `app/main.py`
- Create: `tests/test_jobs.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_jobs.py`:

```python
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Company
from tests.helpers import make_student, make_teacher

JOB_DATA = {
    "company_name": "示例科技有限公司",
    "industry": "人工智能",
    "size": "100-499人",
    "location": "杭州",
    "title": "AI 算法实习生",
    "description": "参与模型训练与数据处理。",
    "requirements": "熟悉 Python，了解 PyTorch。",
    "salary_range": "150-200/天",
    "headcount": "2",
    "deadline": "2026-12-31",
    "expected_start_date": "2026-12-01",
}


def create_job(client, **overrides):
    data = {**JOB_DATA, **overrides}
    return client.post("/jobs/new", data=data, follow_redirects=False)


def test_create_and_view_job(client):
    make_teacher(client)
    response = create_job(client)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/jobs/")

    response = client.get(response.headers["location"])
    assert response.status_code == 200
    assert "AI 算法实习生" in response.text
    assert "示例科技有限公司" in response.text
    assert "熟悉 Python" in response.text


def test_company_is_reused(client):
    make_teacher(client)
    create_job(client, title="岗位A")
    create_job(client, title="岗位B")

    with SessionLocal() as db:
        count = db.scalar(select(func.count()).select_from(Company))
        assert count == 1


def test_creator_can_open_edit_page(client):
    make_teacher(client)
    response = create_job(client)
    job_id = int(response.headers["location"].split("/")[-1])

    response = client.get(f"/jobs/{job_id}/edit")
    assert response.status_code == 200
    assert "AI 算法实习生" in response.text


def test_non_creator_cannot_edit_job(client):
    make_teacher(client)
    response = create_job(client)
    job_id = int(response.headers["location"].split("/")[-1])

    client.post("/logout", follow_redirects=False)
    make_student(client)

    response = client.get(f"/jobs/{job_id}/edit")
    assert response.status_code == 403


def test_job_list_shows_open_jobs(client):
    make_teacher(client)
    create_job(client)

    response = client.get("/jobs")
    assert response.status_code == 200
    assert "AI 算法实习生" in response.text
    assert "发布岗位" in response.text
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/test_jobs.py -v
```

Expected: fails because `/jobs` and `/jobs/new` return 404.

- [ ] **Step 3: Create the jobs router**

Create `app/routers/jobs.py`:

```python
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user, require_user
from app.db import get_db
from app.models import Company, Job, User
from app.services.usage import log_event
from app.templating import flash, render

router = APIRouter(prefix="/jobs")


def get_job_or_404(db: Session, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="岗位不存在")
    return job


def can_edit_job(user: User, job: Job) -> bool:
    return user.role == "teacher" or job.created_by == user.id


def require_editor(user: User, job: Job) -> None:
    if not can_edit_job(user, job):
        raise HTTPException(status_code=403, detail="无权编辑该岗位")


@router.get("")
def list_jobs(
    request: Request,
    user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    jobs = db.scalars(
        select(Job)
        .options(selectinload(Job.company), selectinload(Job.skills))
        .where(Job.status == "open")
        .order_by(Job.created_at.desc())
    ).all()
    return render(request, "jobs/list.html", {"jobs": jobs})


@router.get("/new")
def new_job_page(
    request: Request,
    user: User = Depends(require_user),
):
    return render(request, "jobs/form.html", {"job": None})


@router.post("/new")
def create_job(
    request: Request,
    company_name: str = Form(...),
    industry: str = Form(""),
    size: str = Form(""),
    location: str = Form(""),
    title: str = Form(...),
    description: str = Form(""),
    requirements: str = Form(""),
    salary_range: str = Form(""),
    headcount: str = Form("1"),
    deadline: str = Form(""),
    expected_start_date: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    company_name = company_name.strip()
    title = title.strip()
    if not company_name or not title:
        flash(request, "企业和岗位名称不能为空", "danger")
        return RedirectResponse("/jobs/new", status_code=303)

    try:
        headcount_value = max(1, int(headcount))
    except ValueError:
        headcount_value = 1

    company = db.scalar(select(Company).where(Company.name == company_name))
    if company is None:
        company = Company(
            name=company_name,
            industry=industry.strip() or None,
            size=size.strip() or None,
            location=location.strip() or None,
            created_by=user.id,
        )
        db.add(company)
        db.flush()

    job = Job(
        company_id=company.id,
        title=title,
        description=description.strip(),
        requirements=requirements.strip(),
        location=location.strip() or company.location,
        salary_range=salary_range.strip() or None,
        headcount=headcount_value,
        deadline=deadline.strip() or None,
        expected_start_date=expected_start_date.strip() or None,
        created_by=user.id,
    )
    db.add(job)
    db.flush()

    log_event(
        db,
        "job_create",
        user_id=user.id,
        request=request,
        payload={"job_id": job.id},
    )
    db.commit()

    flash(request, "岗位已发布", "success")
    return RedirectResponse(f"/jobs/{job.id}", status_code=303)


@router.get("/{job_id}")
def job_detail(
    job_id: int,
    request: Request,
    user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_job_or_404(db, job_id)
    can_edit = bool(user and can_edit_job(user, job))
    return render(
        request,
        "jobs/detail.html",
        {"job": job, "can_edit": can_edit},
    )


@router.get("/{job_id}/edit")
def edit_job_page(
    job_id: int,
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    job = get_job_or_404(db, job_id)
    require_editor(user, job)
    return render(request, "jobs/form.html", {"job": job})


@router.post("/{job_id}/edit")
def update_job(
    job_id: int,
    request: Request,
    company_name: str = Form(...),
    industry: str = Form(""),
    size: str = Form(""),
    location: str = Form(""),
    title: str = Form(...),
    description: str = Form(""),
    requirements: str = Form(""),
    salary_range: str = Form(""),
    headcount: str = Form("1"),
    deadline: str = Form(""),
    expected_start_date: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    job = get_job_or_404(db, job_id)
    require_editor(user, job)

    company_name = company_name.strip()
    if not company_name or not title.strip():
        flash(request, "企业和岗位名称不能为空", "danger")
        return RedirectResponse(f"/jobs/{job.id}/edit", status_code=303)

    company = db.scalar(select(Company).where(Company.name == company_name))
    if company is None:
        company = Company(
            name=company_name,
            industry=industry.strip() or None,
            size=size.strip() or None,
            location=location.strip() or None,
            created_by=user.id,
        )
        db.add(company)
        db.flush()

    try:
        headcount_value = max(1, int(headcount))
    except ValueError:
        headcount_value = 1

    job.company_id = company.id
    job.title = title.strip()
    job.description = description.strip()
    job.requirements = requirements.strip()
    job.location = location.strip() or company.location
    job.salary_range = salary_range.strip() or None
    job.headcount = headcount_value
    job.deadline = deadline.strip() or None
    job.expected_start_date = expected_start_date.strip() or None

    log_event(
        db,
        "job_update",
        user_id=user.id,
        request=request,
        payload={"job_id": job.id},
    )
    db.commit()

    flash(request, "岗位已更新", "success")
    return RedirectResponse(f"/jobs/{job.id}", status_code=303)
```

- [ ] **Step 4: Create job templates**

Create `app/templates/jobs/list.html`:

```html
{% extends "base.html" %}
{% block title %}岗位{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3">
  <h1 class="page-title mb-0">岗位</h1>
  {% if user %}
  <a class="btn btn-primary" href="/jobs/new">发布岗位</a>
  {% endif %}
</div>

{% if jobs %}
<div class="row g-3">
  {% for job in jobs %}
  <div class="col-md-6">
    <a class="text-decoration-none text-reset" href="/jobs/{{ job.id }}">
      <div class="card h-100">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-start">
            <div>
              <h5 class="card-title mb-1">{{ job.title }}</h5>
              <div class="form-hint">{{ job.company.name }}{% if job.location %} · {{ job.location }}{% endif %}</div>
            </div>
            {% if job.deadline %}<span class="badge text-bg-light">截止 {{ job.deadline }}</span>{% endif %}
          </div>
          <p class="card-text text-muted mt-3 mb-2">{{ job.description[:90] }}{% if job.description|length > 90 %}…{% endif %}</p>
          <div class="form-hint">
            招聘 {{ job.headcount }} 人
            {% if job.skills %} · {{ job.skills|length }} 项技能要求{% else %} · 技能待分析{% endif %}
          </div>
        </div>
      </div>
    </a>
  </div>
  {% endfor %}
</div>
{% else %}
<div class="card"><div class="card-body text-muted">还没有岗位。登录后点击“发布岗位”开始。</div></div>
{% endif %}
{% endblock %}
```

Create `app/templates/jobs/form.html`:

```html
{% extends "base.html" %}
{% set is_edit = job is not none %}
{% block title %}{{ "编辑岗位" if is_edit else "发布岗位" }}{% endblock %}
{% block content %}
<h1 class="page-title">{{ "编辑岗位" if is_edit else "发布岗位" }}</h1>
<div class="card">
  <div class="card-body">
    <form method="post" action="{{ '/jobs/' ~ job.id ~ '/edit' if is_edit else '/jobs/new' }}">
      <h2 class="h6 text-muted mb-3">企业信息</h2>
      <div class="row g-3 mb-4">
        <div class="col-md-6">
          <label class="form-label" for="company_name">企业名称</label>
          <input class="form-control" id="company_name" name="company_name" required value="{{ job.company.name if is_edit else '' }}">
        </div>
        <div class="col-md-6">
          <label class="form-label" for="industry">行业</label>
          <input class="form-control" id="industry" name="industry" value="{{ (job.company.industry or '') if is_edit else '' }}">
        </div>
        <div class="col-md-4">
          <label class="form-label" for="size">规模</label>
          <input class="form-control" id="size" name="size" value="{{ (job.company.size or '') if is_edit else '' }}" placeholder="100-499人">
        </div>
        <div class="col-md-4">
          <label class="form-label" for="location">地点</label>
          <input class="form-control" id="location" name="location" value="{{ (job.location or '') if is_edit else '' }}" placeholder="杭州">
        </div>
      </div>

      <h2 class="h6 text-muted mb-3">岗位信息</h2>
      <div class="row g-3">
        <div class="col-md-8">
          <label class="form-label" for="title">岗位名称</label>
          <input class="form-control" id="title" name="title" required value="{{ job.title if is_edit else '' }}">
        </div>
        <div class="col-md-4">
          <label class="form-label" for="salary_range">薪资范围</label>
          <input class="form-control" id="salary_range" name="salary_range" value="{{ (job.salary_range or '') if is_edit else '' }}" placeholder="150-200/天">
        </div>
        <div class="col-12">
          <label class="form-label" for="description">岗位描述</label>
          <textarea class="form-control" id="description" name="description" rows="4">{{ job.description if is_edit else '' }}</textarea>
        </div>
        <div class="col-12">
          <label class="form-label" for="requirements">岗位要求</label>
          <textarea class="form-control" id="requirements" name="requirements" rows="4">{{ job.requirements if is_edit else '' }}</textarea>
        </div>
        <div class="col-md-3">
          <label class="form-label" for="headcount">招聘人数</label>
          <input class="form-control" id="headcount" name="headcount" type="number" min="1" value="{{ job.headcount if is_edit else 1 }}">
        </div>
        <div class="col-md-3">
          <label class="form-label" for="deadline">截止日期</label>
          <input class="form-control" id="deadline" name="deadline" type="date" value="{{ (job.deadline or '') if is_edit else '' }}">
        </div>
        <div class="col-md-3">
          <label class="form-label" for="expected_start_date">期望到岗</label>
          <input class="form-control" id="expected_start_date" name="expected_start_date" type="date" value="{{ (job.expected_start_date or '') if is_edit else '' }}">
        </div>
      </div>

      <button class="btn btn-primary mt-4" type="submit">{{ "保存修改" if is_edit else "发布岗位" }}</button>
    </form>
  </div>
</div>
{% endblock %}
```

Create `app/templates/jobs/detail.html`:

```html
{% extends "base.html" %}
{% block title %}{{ job.title }}{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-start mb-3">
  <div>
    <h1 class="page-title mb-1">{{ job.title }}</h1>
    <div class="text-muted">{{ job.company.name }}{% if job.location %} · {{ job.location }}{% endif %}</div>
  </div>
  {% if can_edit %}
  <a class="btn btn-outline-primary" href="/jobs/{{ job.id }}/edit">编辑岗位</a>
  {% endif %}
</div>

<div class="row g-3">
  <div class="col-lg-8">
    <div class="card mb-3">
      <div class="card-header">岗位描述</div>
      <div class="card-body"><div style="white-space: pre-wrap;">{{ job.description or "暂无描述" }}</div></div>
    </div>
    <div class="card mb-3">
      <div class="card-header">岗位要求</div>
      <div class="card-body"><div style="white-space: pre-wrap;">{{ job.requirements or "暂无要求" }}</div></div>
    </div>
    <div class="card">
      <div class="card-header">技能要求</div>
      <div class="card-body p-0">
        {% if job.skills %}
        <table class="table mb-0">
          <thead><tr><th>技能</th><th>类别</th><th>重要性</th><th>要求等级</th></tr></thead>
          <tbody>
          {% for skill in job.skills %}
            <tr>
              <td>{{ skill.name }}</td>
              <td>{{ skill.category }}</td>
              <td>{% if skill.importance == 'must' %}<span class="badge text-bg-danger">必须</span>{% else %}<span class="badge text-bg-secondary">加分</span>{% endif %}</td>
              <td>{{ skill.required_level }} / 5</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
        {% else %}
        <div class="p-4 text-muted">岗位技能尚未分析。</div>
        {% endif %}
      </div>
    </div>
  </div>
  <div class="col-lg-4">
    <div class="card">
      <div class="card-header">岗位信息</div>
      <div class="card-body">
        <dl class="row mb-0">
          <dt class="col-5 text-muted fw-normal">招聘人数</dt><dd class="col-7">{{ job.headcount }}</dd>
          <dt class="col-5 text-muted fw-normal">薪资范围</dt><dd class="col-7">{{ job.salary_range or "面议" }}</dd>
          <dt class="col-5 text-muted fw-normal">截止日期</dt><dd class="col-7">{{ job.deadline or "未设置" }}</dd>
          <dt class="col-5 text-muted fw-normal">期望到岗</dt><dd class="col-7">{{ job.expected_start_date or "未设置" }}</dd>
          <dt class="col-5 text-muted fw-normal">状态</dt><dd class="col-7">{{ "开放" if job.status == "open" else "已关闭" }}</dd>
        </dl>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 5: Register the jobs router**

Modify `app/main.py`:

```python
from app.routers import auth, dashboard, health, home, jobs
```

and inside `create_app`:

```python
    app.include_router(dashboard.router)
    app.include_router(jobs.router)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run:

```bash
pytest tests/test_jobs.py -v
```

Expected:

```text
tests/test_jobs.py::test_create_and_view_job PASSED
tests/test_jobs.py::test_company_is_reused PASSED
tests/test_jobs.py::test_creator_can_open_edit_page PASSED
tests/test_jobs.py::test_non_creator_cannot_edit_job PASSED
tests/test_jobs.py::test_job_list_shows_open_jobs PASSED
```

- [ ] **Step 7: Commit**

Run:

```bash
git add app/routers/jobs.py app/templates/jobs app/main.py tests/test_jobs.py
git commit -m "feat: add job posting, listing, detail and editing"
```

---

## Task 6: Explainable matching score and gap list

**Files:**
- Create: `app/services/skills.py`
- Create: `app/services/matching.py`
- Create: `tests/test_matching.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_matching.py`:

```python
from types import SimpleNamespace

from app.services.matching import compute_match
from app.services.skills import normalize_skill


def job_skill(name, importance, required_level):
    return SimpleNamespace(
        name=name,
        importance=importance,
        required_level=required_level,
    )


def test_normalize_skill():
    assert normalize_skill("  Python  ") == "python"
    assert normalize_skill("Machine   Learning") == "machine learning"


def test_score_and_gaps():
    student_skills = [
        {"name": "Python", "level": 4},
        {"name": "SQL", "level": 3},
    ]
    job_skills = [
        job_skill("python", "must", 5),
        job_skill("SQL", "nice", 3),
    ]

    result = compute_match(student_skills, job_skills)

    assert result.score == 85
    assert result.has_job_skills is True
    assert len(result.gaps) == 1
    assert result.gaps[0].name == "python"
    assert result.gaps[0].student_level == 4
    assert result.gaps[0].required_level == 5


def test_no_job_skills():
    result = compute_match([{"name": "Python", "level": 5}], [])
    assert result.score == 0
    assert result.has_job_skills is False
    assert result.gaps == []


def test_student_without_skills_gets_zero():
    result = compute_match([], [job_skill("Python", "must", 3)])
    assert result.score == 0
    assert len(result.gaps) == 1
    assert result.gaps[0].student_level == 0


def test_multiple_entries_take_max_level():
    result = compute_match(
        [
            {"name": "Python", "level": 2},
            {"name": " python ", "level": 4},
        ],
        [job_skill("Python", "must", 4)],
    )
    assert result.score == 100
    assert result.gaps == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/test_matching.py -v
```

Expected: fails because `app.services.matching` does not exist.

- [ ] **Step 3: Create skill normalization**

Create `app/services/skills.py`:

```python
def normalize_skill(name: str) -> str:
    return " ".join(str(name).strip().lower().split())
```

- [ ] **Step 4: Create the matching service**

Create `app/services/matching.py`:

```python
from dataclasses import dataclass, field

from app.services.skills import normalize_skill


@dataclass
class MatchGap:
    name: str
    required_level: int
    student_level: int
    importance: str


@dataclass
class MatchResult:
    score: int
    gaps: list[MatchGap] = field(default_factory=list)
    matched: list[dict] = field(default_factory=list)
    has_job_skills: bool = True


def compute_match(student_skills: list[dict], job_skills: list) -> MatchResult:
    normalized: dict[str, int] = {}
    for item in student_skills or []:
        key = normalize_skill(item.get("name", ""))
        if not key:
            continue
        try:
            level = int(item.get("level", 0))
        except (TypeError, ValueError):
            level = 0
        level = max(0, min(5, level))
        normalized[key] = max(normalized.get(key, 0), level)

    if not job_skills:
        return MatchResult(score=0, has_job_skills=False)

    total_weight = 0
    weighted_score = 0.0
    gaps: list[MatchGap] = []
    matched: list[dict] = []

    for skill in job_skills:
        required_level = max(1, min(5, int(skill.required_level)))
        weight = 3 if skill.importance == "must" else 1
        student_level = normalized.get(normalize_skill(skill.name), 0)
        coverage = min(student_level / required_level, 1.0)

        total_weight += weight
        weighted_score += weight * coverage

        entry = {
            "name": skill.name,
            "importance": skill.importance,
            "required_level": required_level,
            "student_level": student_level,
            "coverage": round(coverage, 2),
        }
        if coverage >= 1:
            matched.append(entry)
        else:
            gaps.append(
                MatchGap(
                    name=skill.name,
                    required_level=required_level,
                    student_level=student_level,
                    importance=skill.importance,
                )
            )

    score = round(100 * weighted_score / total_weight) if total_weight else 0
    gaps.sort(
        key=lambda gap: (
            0 if gap.importance == "must" else 1,
            -(gap.required_level - gap.student_level),
        )
    )
    return MatchResult(
        score=score,
        gaps=gaps,
        matched=matched,
        has_job_skills=True,
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run:

```bash
pytest tests/test_matching.py -v
```

Expected:

```text
tests/test_matching.py::test_normalize_skill PASSED
tests/test_matching.py::test_score_and_gaps PASSED
tests/test_matching.py::test_no_job_skills PASSED
tests/test_matching.py::test_student_without_skills_gets_zero PASSED
tests/test_matching.py::test_multiple_entries_take_max_level PASSED
```

- [ ] **Step 6: Commit**

Run:

```bash
git add app/services/skills.py app/services/matching.py tests/test_matching.py
git commit -m "feat: add explainable skill matching and gap calculation"
```

---

## Task 7: LLM client and job skill extraction service

**Files:**
- Create: `app/schemas.py`
- Create: `app/services/llm.py`
- Create: `app/services/job_skills.py`
- Create: `tests/test_job_skills.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_job_skills.py`:

```python
from types import SimpleNamespace

import pytest

from app.services.job_skills import extract_job_skills
from app.services.llm import LLMClient, LLMError


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def chat_json(self, system, user):
        self.calls += 1
        return self.payload


def make_job():
    return SimpleNamespace(
        title="AI 算法实习生",
        description="负责模型训练与数据处理",
        requirements="熟悉 Python 和 PyTorch",
        company=SimpleNamespace(name="示例科技有限公司"),
    )


def test_normalizes_chinese_importance_and_level():
    fake = FakeLLM(
        {
            "summary": "AI 算法实习",
            "responsibilities": ["模型训练"],
            "skills": [
                {
                    "name": "Python",
                    "category": "编程",
                    "importance": "必须",
                    "required_level": "高级",
                }
            ],
        }
    )

    result = extract_job_skills(make_job(), fake)

    assert fake.calls == 1
    assert result.skills[0].name == "Python"
    assert result.skills[0].importance == "must"
    assert result.skills[0].required_level == 5


def test_dedupes_skill_names_case_insensitively():
    fake = FakeLLM(
        {
            "skills": [
                {"name": "Python", "required_level": 3},
                {"name": " python ", "required_level": 4},
            ]
        }
    )

    result = extract_job_skills(make_job(), fake)

    assert len(result.skills) == 1
    assert result.skills[0].required_level == 3


def test_invalid_payload_raises_llm_error():
    fake = FakeLLM({"skills": [{"name": ""}]})

    with pytest.raises(LLMError):
        extract_job_skills(make_job(), fake)


def test_missing_api_key_raises_llm_error():
    client = LLMClient(
        api_key="",
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
    )

    with pytest.raises(LLMError):
        client.chat_json("system", "user")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/test_job_skills.py -v
```

Expected: fails because `app.services.job_skills` and `app.services.llm` do not exist.

- [ ] **Step 3: Create Pydantic schemas for structured skill extraction**

Create `app/schemas.py`:

```python
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

IMPORTANCE_MAP = {
    "must": "must",
    "required": "must",
    "必须": "must",
    "必需": "must",
    "硬性": "must",
    "nice": "nice",
    "optional": "nice",
    "加分": "nice",
    "优先": "nice",
    "可选": "nice",
}

LEVEL_MAP = {
    "初级": 1,
    "入门": 1,
    "了解": 1,
    "中级": 3,
    "熟练": 3,
    "掌握": 3,
    "高级": 5,
    "精通": 5,
    "专家": 5,
}


class JobSkillItem(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    category: str = Field(default="通用", max_length=40)
    importance: str = "nice"
    required_level: int = 3

    @field_validator("importance", mode="before")
    @classmethod
    def normalize_importance(cls, value: Any) -> str:
        text = str(value).strip().lower()
        return IMPORTANCE_MAP.get(text, "nice")

    @field_validator("required_level", mode="before")
    @classmethod
    def normalize_level(cls, value: Any) -> int:
        if isinstance(value, bool):
            return 3
        if isinstance(value, (int, float)):
            return max(1, min(5, int(value)))
        text = str(value).strip()
        if text in LEVEL_MAP:
            return LEVEL_MAP[text]
        digits = re.findall(r"\d", text)
        if digits:
            return max(1, min(5, int(digits[0])))
        return 3


class JobSkillExtraction(BaseModel):
    summary: str = Field(default="", max_length=500)
    responsibilities: list[str] = Field(default_factory=list, max_length=10)
    skills: list[JobSkillItem] = Field(default_factory=list, max_length=30)
```

- [ ] **Step 4: Create the LLM client**

Create `app/services/llm.py`:

```python
import json
import time
from typing import Any, Protocol

import httpx

from app.config import settings


class LLMError(Exception):
    pass


class LLMProtocol(Protocol):
    def chat_json(self, system: str, user: str) -> dict[str, Any]:
        ...


class LLMClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 60.0,
        max_retries: int = 2,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

    def chat_json(self, system: str, user: str) -> dict[str, Any]:
        if not self.api_key:
            raise LLMError("未配置 DEEPSEEK_API_KEY，请先在 .env 中填写")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                        },
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()

                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                if not isinstance(parsed, dict):
                    raise ValueError("LLM 返回的 JSON 不是对象")
                return parsed
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))

        raise LLMError(f"LLM 调用失败：{last_error}")


def get_llm_client() -> LLMClient:
    return LLMClient(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        model=settings.llm_model,
        timeout=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )
```

- [ ] **Step 5: Create the job skill extraction service**

Create `app/services/job_skills.py`:

```python
from pydantic import ValidationError

from app.models import Job
from app.schemas import JobSkillExtraction
from app.services.llm import LLMError, LLMProtocol
from app.services.skills import normalize_skill

SYSTEM_PROMPT = """你是企业招聘分析助手。请根据岗位信息提取技能要求，并只输出一个 JSON 对象。
JSON 结构：
{
  "summary": "岗位一句话摘要",
  "responsibilities": ["职责1", "职责2"],
  "skills": [
    {"name": "技能名", "category": "编程/算法/数据/工程/通用", "importance": "must 或 nice", "required_level": 1到5的整数}
  ]
}
规则：
1. 只提取岗位描述和要求中明确或合理隐含的技能，不要编造。
2. importance=must 表示硬性要求，nice 表示加分项。
3. required_level：1=了解，2=基础，3=熟练，4=深入，5=精通。
4. 技能名使用常见写法，最多 20 个。
5. 不要输出 Markdown 代码块，只输出 JSON。"""


def build_user_prompt(job: Job) -> str:
    company_name = job.company.name if job.company else ""
    return (
        f"企业：{company_name}\n"
        f"岗位：{job.title}\n"
        f"岗位描述：{job.description or '无'}\n"
        f"岗位要求：{job.requirements or '无'}"
    )


def extract_job_skills(job: Job, llm: LLMProtocol) -> JobSkillExtraction:
    data = llm.chat_json(SYSTEM_PROMPT, build_user_prompt(job))

    try:
        result = JobSkillExtraction.model_validate(data)
    except ValidationError as exc:
        raise LLMError(f"技能拆解结果格式错误：{exc}") from exc

    seen: set[str] = set()
    unique = []
    for item in result.skills:
        key = normalize_skill(item.name)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)

    result.skills = unique
    return result
```

- [ ] **Step 6: Run the tests to verify they pass**

Run:

```bash
pytest tests/test_job_skills.py -v
```

Expected:

```text
tests/test_job_skills.py::test_normalizes_chinese_importance_and_level PASSED
tests/test_job_skills.py::test_dedupes_skill_names_case_insensitively PASSED
tests/test_job_skills.py::test_invalid_payload_raises_llm_error PASSED
tests/test_job_skills.py::test_missing_api_key_raises_llm_error PASSED
```

- [ ] **Step 7: Commit**

Run:

```bash
git add app/schemas.py app/services/llm.py app/services/job_skills.py tests/test_job_skills.py
git commit -m "feat: add LLM client and structured job skill extraction"
```

---

## Task 8: AI skill extraction route and editable skill list

**Files:**
- Modify: `app/routers/jobs.py`
- Modify: `app/templates/jobs/detail.html`
- Create: `app/templates/jobs/skills.html`
- Create: `tests/test_job_skill_routes.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_job_skill_routes.py`:

```python
import pytest
from sqlalchemy import func, select

from app.db import SessionLocal
from app.main import app
from app.models import JobSkill
from app.services.llm import get_llm_client
from tests.helpers import make_student, make_teacher

JOB_DATA = {
    "company_name": "示例科技有限公司",
    "industry": "人工智能",
    "size": "100-499人",
    "location": "杭州",
    "title": "AI 算法实习生",
    "description": "参与模型训练与数据处理。",
    "requirements": "熟悉 Python，了解 PyTorch。",
    "salary_range": "",
    "headcount": "1",
    "deadline": "",
    "expected_start_date": "",
}


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload

    def chat_json(self, system, user):
        return self.payload


def create_job(client):
    response = client.post("/jobs/new", data=JOB_DATA, follow_redirects=False)
    assert response.status_code == 303
    return int(response.headers["location"].split("/")[-1])


def skill_count(job_id):
    with SessionLocal() as db:
        return db.scalar(
            select(func.count())
            .select_from(JobSkill)
            .where(JobSkill.job_id == job_id)
        )


@pytest.fixture()
def fake_llm():
    payload = {
        "summary": "AI 算法实习",
        "responsibilities": ["模型训练", "数据处理"],
        "skills": [
            {
                "name": "Python",
                "category": "编程",
                "importance": "must",
                "required_level": 4,
            },
            {
                "name": "PyTorch",
                "category": "算法",
                "importance": "nice",
                "required_level": 3,
            },
        ],
    }
    app.dependency_overrides[get_llm_client] = lambda: FakeLLM(payload)
    yield payload
    app.dependency_overrides.clear()


def test_extract_job_skills_route(client, fake_llm):
    make_teacher(client)
    job_id = create_job(client)

    response = client.post(
        f"/jobs/{job_id}/extract-skills", follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == f"/jobs/{job_id}/skills"

    response = client.get(f"/jobs/{job_id}/skills")
    assert response.status_code == 200
    assert "Python" in response.text
    assert "PyTorch" in response.text
    assert skill_count(job_id) == 2


def test_update_skills_replaces_rows(client, fake_llm):
    make_teacher(client)
    job_id = create_job(client)
    client.post(f"/jobs/{job_id}/extract-skills", follow_redirects=False)

    response = client.post(
        f"/jobs/{job_id}/skills",
        data={
            "skill_name": ["Python", "SQL"],
            "skill_category": ["编程", "数据"],
            "skill_importance": ["must", "nice"],
            "skill_level": ["5", "3"],
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert skill_count(job_id) == 2

    response = client.get(f"/jobs/{job_id}")
    assert "SQL" in response.text
    assert "5 / 5" in response.text


def test_non_editor_cannot_extract_skills(client, fake_llm):
    make_teacher(client)
    job_id = create_job(client)

    client.post("/logout", follow_redirects=False)
    make_student(client)

    response = client.post(
        f"/jobs/{job_id}/extract-skills", follow_redirects=False
    )
    assert response.status_code == 403
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/test_job_skill_routes.py -v
```

Expected: fails because `/jobs/{id}/extract-skills` and `/jobs/{id}/skills` return 404.

- [ ] **Step 3: Add the extraction and skill editing routes**

Modify `app/routers/jobs.py` by adding imports:

```python
from sqlalchemy import delete, select

from app.models import Company, Job, JobSkill, User
from app.services.job_skills import extract_job_skills
from app.services.llm import LLMClient, LLMError, get_llm_client
```

Append these routes after `update_job`:

```python
def _form_value(form, key: str, index: int, default: str = "") -> str:
    values = form.getlist(key)
    if index < len(values):
        return str(values[index])
    return default


@router.post("/{job_id}/extract-skills")
def extract_skills(
    job_id: int,
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
):
    job = get_job_or_404(db, job_id)
    require_editor(user, job)

    try:
        result = extract_job_skills(job, llm)
    except LLMError as exc:
        flash(request, str(exc), "danger")
        return RedirectResponse(f"/jobs/{job.id}", status_code=303)

    db.execute(delete(JobSkill).where(JobSkill.job_id == job.id))
    for index, skill in enumerate(result.skills):
        db.add(
            JobSkill(
                job_id=job.id,
                name=skill.name,
                category=skill.category,
                importance=skill.importance,
                required_level=skill.required_level,
                sort_order=index,
            )
        )

    log_event(
        db,
        "job_skill_extract",
        user_id=user.id,
        request=request,
        payload={"job_id": job.id, "skill_count": len(result.skills)},
    )
    db.commit()
    flash(request, f"已提取 {len(result.skills)} 项技能，请检查后保存", "success")
    return RedirectResponse(f"/jobs/{job.id}/skills", status_code=303)


@router.get("/{job_id}/skills")
def edit_skills_page(
    job_id: int,
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    job = get_job_or_404(db, job_id)
    require_editor(user, job)
    return render(request, "jobs/skills.html", {"job": job})


@router.post("/{job_id}/skills")
async def update_skills(
    job_id: int,
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    job = get_job_or_404(db, job_id)
    require_editor(user, job)

    form = await request.form()
    names = form.getlist("skill_name")

    db.execute(delete(JobSkill).where(JobSkill.job_id == job.id))

    created = 0
    for index, raw_name in enumerate(names):
        name = str(raw_name).strip()
        if not name:
            continue
        raw_level = _form_value(form, "skill_level", index, "3")
        try:
            level = max(1, min(5, int(raw_level)))
        except ValueError:
            level = 3
        importance = _form_value(form, "skill_importance", index, "nice")
        if importance not in {"must", "nice"}:
            importance = "nice"
        db.add(
            JobSkill(
                job_id=job.id,
                name=name,
                category=_form_value(form, "skill_category", index, "通用")
                or "通用",
                importance=importance,
                required_level=level,
                sort_order=index,
            )
        )
        created += 1

    log_event(
        db,
        "job_skills_update",
        user_id=user.id,
        request=request,
        payload={"job_id": job.id, "skill_count": created},
    )
    db.commit()
    flash(request, f"已保存 {created} 项技能", "success")
    return RedirectResponse(f"/jobs/{job.id}", status_code=303)
```

- [ ] **Step 4: Add the edit buttons and skills template**

Modify the header block in `app/templates/jobs/detail.html`:

```html
<div class="d-flex justify-content-between align-items-start mb-3">
  <div>
    <h1 class="page-title mb-1">{{ job.title }}</h1>
    <div class="text-muted">{{ job.company.name }}{% if job.location %} · {{ job.location }}{% endif %}</div>
  </div>
  {% if can_edit %}
  <div class="d-flex gap-2 flex-wrap">
    <form method="post" action="/jobs/{{ job.id }}/extract-skills">
      <button class="btn btn-outline-primary" type="submit">AI 分析技能</button>
    </form>
    <a class="btn btn-outline-primary" href="/jobs/{{ job.id }}/skills">编辑技能</a>
    <a class="btn btn-outline-primary" href="/jobs/{{ job.id }}/edit">编辑岗位</a>
  </div>
  {% endif %}
</div>
```

Create `app/templates/jobs/skills.html`:

```html
{% extends "base.html" %}
{% block title %}编辑技能 - {{ job.title }}{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-start mb-3 flex-wrap gap-2">
  <div>
    <h1 class="page-title mb-1">编辑技能</h1>
    <div class="text-muted">{{ job.title }}</div>
  </div>
  <div class="d-flex gap-2">
    <form method="post" action="/jobs/{{ job.id }}/extract-skills">
      <button class="btn btn-outline-primary" type="submit">AI 重新分析</button>
    </form>
    <a class="btn btn-outline-secondary" href="/jobs/{{ job.id }}">返回岗位</a>
  </div>
</div>

<form method="post" action="/jobs/{{ job.id }}/skills">
  <div class="card">
    <div class="card-header">技能清单</div>
    <div class="card-body p-0">
      <div class="table-responsive">
        <table class="table mb-0">
          <thead>
            <tr><th>技能名</th><th>类别</th><th>重要性</th><th>要求等级</th></tr>
          </thead>
          <tbody id="skill-rows">
          {% for skill in job.skills %}
            <tr class="skill-row">
              <td><input class="form-control" name="skill_name" value="{{ skill.name }}"></td>
              <td><input class="form-control" name="skill_category" value="{{ skill.category }}"></td>
              <td>
                <select class="form-select" name="skill_importance">
                  <option value="must" {% if skill.importance == 'must' %}selected{% endif %}>必须</option>
                  <option value="nice" {% if skill.importance != 'must' %}selected{% endif %}>加分</option>
                </select>
              </td>
              <td>
                <select class="form-select" name="skill_level">
                  {% for i in range(1, 6) %}
                  <option value="{{ i }}" {% if skill.required_level == i %}selected{% endif %}>{{ i }}</option>
                  {% endfor %}
                </select>
              </td>
            </tr>
          {% endfor %}
          {% for _ in range(3 if not job.skills else 1) %}
            <tr class="skill-row">
              <td><input class="form-control" name="skill_name" placeholder="技能名"></td>
              <td><input class="form-control" name="skill_category" value="通用"></td>
              <td>
                <select class="form-select" name="skill_importance">
                  <option value="must">必须</option>
                  <option value="nice" selected>加分</option>
                </select>
              </td>
              <td>
                <select class="form-select" name="skill_level">
                  <option value="1">1</option>
                  <option value="2">2</option>
                  <option value="3" selected>3</option>
                  <option value="4">4</option>
                  <option value="5">5</option>
                </select>
              </td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
    <div class="card-footer d-flex justify-content-between">
      <button class="btn btn-outline-secondary" type="button" data-add-skill-row>添加一行</button>
      <button class="btn btn-primary" type="submit">保存技能</button>
    </div>
  </div>
  <p class="form-hint mt-2 mb-0">清空技能名即可删除该行；空白行会被忽略。</p>
</form>
{% endblock %}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run:

```bash
pytest tests/test_job_skill_routes.py -v
```

Expected:

```text
tests/test_job_skill_routes.py::test_extract_job_skills_route PASSED
tests/test_job_skill_routes.py::test_update_skills_replaces_rows PASSED
tests/test_job_skill_routes.py::test_non_editor_cannot_extract_skills PASSED
```

- [ ] **Step 6: Commit**

Run:

```bash
git add app/routers/jobs.py app/templates/jobs/detail.html app/templates/jobs/skills.html tests/test_job_skill_routes.py
git commit -m "feat: add AI skill extraction and editable skill list"
```

---

## Task 9: Student profile and skill self-assessment

**Files:**
- Create: `app/services/profile_text.py`
- Create: `app/routers/profile.py`
- Create: `app/templates/profile/edit.html`
- Modify: `app/main.py`
- Create: `tests/test_profile_text.py`
- Create: `tests/test_profile_routes.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_profile_text.py`:

```python
from app.services.profile_text import (
    format_awards,
    format_blocks,
    format_education,
    format_skills,
    parse_awards,
    parse_blocks,
    parse_education,
    parse_skills,
)


def test_education_roundtrip():
    text = "某某大学 | 人工智能 | 本科 | 2023-2027\n另一所大学 | 计算机 | 硕士 | 2027-2030"
    items = parse_education(text)
    assert items[0]["school"] == "某某大学"
    assert items[1]["degree"] == "硕士"
    assert format_education(items) == text


def test_projects_blocks_roundtrip():
    text = (
        "智能简历系统 | 后端 | 2026.03-2026.05\n"
        "负责 FastAPI 与 LLM 集成\n\n"
        "课程项目 | 成员 | 2025"
    )
    items = parse_blocks(text, ["name", "role", "period"])
    assert items[0]["name"] == "智能简历系统"
    assert "FastAPI" in items[0]["description"]
    assert items[1]["name"] == "课程项目"
    assert format_blocks(items, ["name", "role", "period"]) == text


def test_awards_roundtrip():
    text = "校级奖学金\nACM 校赛二等奖"
    items = parse_awards(text)
    assert len(items) == 2
    assert format_awards(items) == text


def test_skills_parse_clamps_and_formats():
    items = parse_skills("Python | 9 | 课程项目\nSQL | abc")
    assert items[0]["level"] == 5
    assert items[1]["level"] == 3
    assert items[0]["evidence"] == "课程项目"
    assert "Python | 5 | 课程项目" in format_skills(items)
```

Create `tests/test_profile_routes.py`:

```python
from sqlalchemy import select

from app.db import SessionLocal
from app.models import StudentProfile, User
from tests.helpers import make_student, make_teacher

PROFILE_DATA = {
    "summary": "热爱 AI 工程",
    "education_text": "某某大学 | 人工智能 | 本科 | 2023-2027",
    "projects_text": "智能简历系统 | 后端 | 2026.03-2026.05\n负责 FastAPI 与 LLM 集成",
    "internships_text": "",
    "awards_text": "校级奖学金",
    "skills_text": "Python | 5 | 课程项目\nSQL | 3 | 课程设计",
    "availability_from": "2026-12-01",
    "availability_note": "每周可实习 4 天",
    "target_job_id": "",
}


def test_student_can_save_profile(client):
    make_student(client)

    response = client.post("/profile", data=PROFILE_DATA, follow_redirects=False)
    assert response.status_code == 303

    response = client.get("/profile")
    assert response.status_code == 200
    assert "热爱 AI 工程" in response.text
    assert "Python | 5 | 课程项目" in response.text


def test_profile_is_persisted(client):
    make_student(client)
    client.post("/profile", data=PROFILE_DATA, follow_redirects=False)

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == "stu1"))
        profile = db.get(StudentProfile, user.id)
        assert profile.summary == "热爱 AI 工程"
        assert profile.skills_json[0]["name"] == "Python"
        assert profile.education_json[0]["school"] == "某某大学"
        assert profile.availability_from == "2026-12-01"


def test_teacher_cannot_access_student_profile(client):
    make_teacher(client)
    response = client.get("/profile")
    assert response.status_code == 403
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/test_profile_text.py tests/test_profile_routes.py -v
```

Expected: fails because `app.services.profile_text` and `/profile` do not exist.

- [ ] **Step 3: Create the profile text parser**

Create `app/services/profile_text.py`:

```python
def _split_lines(text: str) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def parse_education(text: str) -> list[dict]:
    items = []
    for line in _split_lines(text):
        parts = [part.strip() for part in line.split("|")]
        parts += [""] * (4 - len(parts))
        items.append(
            {
                "school": parts[0],
                "major": parts[1],
                "degree": parts[2],
                "period": parts[3],
            }
        )
    return items


def format_education(items: list[dict]) -> str:
    return "\n".join(
        " | ".join(
            [
                item.get("school", ""),
                item.get("major", ""),
                item.get("degree", ""),
                item.get("period", ""),
            ]
        )
        for item in items or []
    )


def parse_blocks(text: str, fields: list[str]) -> list[dict]:
    blocks: list[list[str]] = []
    current: list[str] = []

    for line in (text or "").splitlines():
        if line.strip() == "":
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(line.strip())

    if current:
        blocks.append(current)

    items = []
    for block in blocks:
        header = [part.strip() for part in block[0].split("|")]
        header += [""] * (len(fields) - len(header))
        item = {field: header[index] for index, field in enumerate(fields)}
        item["description"] = "\n".join(block[1:]).strip()
        items.append(item)
    return items


def format_blocks(items: list[dict], fields: list[str]) -> str:
    blocks = []
    for item in items or []:
        header = " | ".join(item.get(field, "") for field in fields)
        description = item.get("description", "")
        blocks.append(header + ("\n" + description if description else ""))
    return "\n\n".join(blocks)


def parse_awards(text: str) -> list[dict]:
    return [{"name": line} for line in _split_lines(text)]


def format_awards(items: list[dict]) -> str:
    return "\n".join(item.get("name", "") for item in items or [])


def parse_skills(text: str) -> list[dict]:
    skills = []
    for line in _split_lines(text):
        parts = [part.strip() for part in line.split("|")]
        name = parts[0] if parts else ""
        if not name:
            continue

        level = 3
        if len(parts) > 1:
            try:
                level = int(parts[1])
            except ValueError:
                level = 3
        level = max(1, min(5, level))

        evidence = parts[2] if len(parts) > 2 else ""
        skills.append({"name": name, "level": level, "evidence": evidence})
    return skills


def format_skills(items: list[dict]) -> str:
    return "\n".join(
        f"{item.get('name', '')} | {item.get('level', 3)} | {item.get('evidence', '')}"
        for item in items or []
    )
```

- [ ] **Step 4: Create the profile router**

Create `app/routers/profile.py`:

```python
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_student
from app.db import get_db
from app.models import Job, StudentProfile, User
from app.services.profile_text import (
    format_awards,
    format_blocks,
    format_education,
    format_skills,
    parse_awards,
    parse_blocks,
    parse_education,
    parse_skills,
)
from app.services.usage import log_event
from app.templating import flash, render

router = APIRouter()


@router.get("/profile")
def profile_page(
    request: Request,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    profile = db.get(StudentProfile, user.id)
    if profile is None:
        profile = StudentProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    jobs = db.scalars(
        select(Job).where(Job.status == "open").order_by(Job.created_at.desc())
    ).all()

    return render(
        request,
        "profile/edit.html",
        {
            "profile": profile,
            "education_text": format_education(profile.education_json),
            "projects_text": format_blocks(
                profile.projects_json, ["name", "role", "period"]
            ),
            "internships_text": format_blocks(
                profile.internships_json, ["company", "role", "period"]
            ),
            "awards_text": format_awards(profile.awards_json),
            "skills_text": format_skills(profile.skills_json),
            "jobs": jobs,
        },
    )


@router.post("/profile")
def save_profile(
    request: Request,
    summary: str = Form(""),
    education_text: str = Form(""),
    projects_text: str = Form(""),
    internships_text: str = Form(""),
    awards_text: str = Form(""),
    skills_text: str = Form(""),
    availability_from: str = Form(""),
    availability_note: str = Form(""),
    target_job_id: str = Form(""),
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    profile = db.get(StudentProfile, user.id)
    if profile is None:
        profile = StudentProfile(user_id=user.id)
        db.add(profile)
        db.flush()

    profile.summary = summary.strip()
    profile.education_json = parse_education(education_text)
    profile.projects_json = parse_blocks(projects_text, ["name", "role", "period"])
    profile.internships_json = parse_blocks(
        internships_text, ["company", "role", "period"]
    )
    profile.awards_json = parse_awards(awards_text)
    profile.skills_json = parse_skills(skills_text)
    profile.availability_from = availability_from.strip() or None
    profile.availability_note = availability_note.strip() or None

    target_job_id = target_job_id.strip()
    if target_job_id.isdigit():
        job = db.get(Job, int(target_job_id))
        profile.target_job_id = job.id if job is not None else None
    else:
        profile.target_job_id = None

    log_event(
        db,
        "profile_save",
        user_id=user.id,
        request=request,
        payload={"skill_count": len(profile.skills_json)},
    )
    db.commit()
    flash(request, "资料已保存", "success")
    return RedirectResponse("/profile", status_code=303)
```

- [ ] **Step 5: Create the profile template**

Create `app/templates/profile/edit.html`:

```html
{% extends "base.html" %}
{% block title %}我的资料{% endblock %}
{% block content %}
<h1 class="page-title">我的资料</h1>
<div class="card">
  <div class="card-body">
    <form method="post" action="/profile">
      <div class="mb-4">
        <label class="form-label" for="summary">个人简介</label>
        <textarea class="form-control" id="summary" name="summary" rows="3" placeholder="一句话介绍你的方向、优势和目标。">{{ profile.summary }}</textarea>
      </div>

      <div class="row g-3 mb-4">
        <div class="col-md-4">
          <label class="form-label" for="availability_from">可到岗时间</label>
          <input class="form-control" id="availability_from" name="availability_from" type="date" value="{{ profile.availability_from or '' }}">
        </div>
        <div class="col-md-8">
          <label class="form-label" for="availability_note">时间说明</label>
          <input class="form-control" id="availability_note" name="availability_note" value="{{ profile.availability_note or '' }}" placeholder="如：每周可实习 4 天，寒暑假全职">
        </div>
        <div class="col-md-6">
          <label class="form-label" for="target_job_id">目标岗位</label>
          <select class="form-select" id="target_job_id" name="target_job_id">
            <option value="">暂不选择</option>
            {% for job in jobs %}
            <option value="{{ job.id }}" {% if profile.target_job_id == job.id %}selected{% endif %}>{{ job.title }} - {{ job.company.name }}</option>
            {% endfor %}
          </select>
        </div>
      </div>

      <div class="mb-4">
        <label class="form-label" for="education_text">教育经历</label>
        <textarea class="form-control" id="education_text" name="education_text" rows="3" placeholder="学校 | 专业 | 学历 | 时间">{{ education_text }}</textarea>
        <div class="form-hint">每行一条，用 | 分隔。示例：某某大学 | 人工智能 | 本科 | 2023-2027</div>
      </div>

      <div class="mb-4">
        <label class="form-label" for="projects_text">项目经历</label>
        <textarea class="form-control" id="projects_text" name="projects_text" rows="6" placeholder="项目名 | 角色 | 时间&#10;描述...">{{ projects_text }}</textarea>
        <div class="form-hint">每个项目之间空一行；第一行写“项目名 | 角色 | 时间”，后面写描述和技术栈。</div>
      </div>

      <div class="mb-4">
        <label class="form-label" for="internships_text">实习经历</label>
        <textarea class="form-control" id="internships_text" name="internships_text" rows="4" placeholder="公司 | 角色 | 时间&#10;描述...">{{ internships_text }}</textarea>
        <div class="form-hint">格式同项目经历，每个实习之间空一行。</div>
      </div>

      <div class="mb-4">
        <label class="form-label" for="awards_text">奖项荣誉</label>
        <textarea class="form-control" id="awards_text" name="awards_text" rows="3" placeholder="每行一个奖项">{{ awards_text }}</textarea>
      </div>

      <div class="mb-4">
        <label class="form-label" for="skills_text">技能自评</label>
        <textarea class="form-control" id="skills_text" name="skills_text" rows="6" placeholder="Python | 5 | 课程项目&#10;SQL | 3 | 课程设计">{{ skills_text }}</textarea>
        <div class="form-hint">每行一项：技能名 | 等级(1-5) | 证据。等级 1=了解，3=熟练，5=精通。</div>
      </div>

      <button class="btn btn-primary" type="submit">保存资料</button>
    </form>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 6: Register the profile router**

Modify `app/main.py`:

```python
from app.routers import auth, dashboard, health, home, jobs, profile
```

and inside `create_app`:

```python
    app.include_router(jobs.router)
    app.include_router(profile.router)
```

- [ ] **Step 7: Run the tests to verify they pass**

Run:

```bash
pytest tests/test_profile_text.py tests/test_profile_routes.py -v
```

Expected:

```text
tests/test_profile_text.py::test_education_roundtrip PASSED
tests/test_profile_text.py::test_projects_blocks_roundtrip PASSED
tests/test_profile_text.py::test_awards_roundtrip PASSED
tests/test_profile_text.py::test_skills_parse_clamps_and_formats PASSED
tests/test_profile_routes.py::test_student_can_save_profile PASSED
tests/test_profile_routes.py::test_profile_is_persisted PASSED
tests/test_profile_routes.py::test_teacher_cannot_access_student_profile PASSED
```

- [ ] **Step 8: Commit**

Run:

```bash
git add app/services/profile_text.py app/routers/profile.py app/templates/profile app/main.py tests/test_profile_text.py tests/test_profile_routes.py
git commit -m "feat: add student profile and skill self-assessment"
```

---

## Task 10: Gap view, dashboard recommendations, demo seed, and README

**Files:**
- Modify: `app/routers/jobs.py`
- Modify: `app/routers/dashboard.py`
- Modify: `app/templates/jobs/detail.html`
- Modify: `app/templates/dashboard/student.html`
- Create: `scripts/__init__.py`
- Create: `scripts/seed.py`
- Modify: `README.md`
- Create: `tests/test_gap_view.py`
- Create: `tests/test_seed.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_gap_view.py`:

```python
from sqlalchemy import select

from app.db import SessionLocal
from app.models import JobSkill
from tests.helpers import make_student, make_teacher

JOB_DATA = {
    "company_name": "示例科技有限公司",
    "industry": "人工智能",
    "size": "100-499人",
    "location": "杭州",
    "title": "AI 算法实习生",
    "description": "参与模型训练与数据处理。",
    "requirements": "熟悉 Python，了解 PyTorch。",
    "salary_range": "",
    "headcount": "1",
    "deadline": "",
    "expected_start_date": "",
}

PROFILE_DATA = {
    "summary": "热爱 AI 工程",
    "education_text": "",
    "projects_text": "",
    "internships_text": "",
    "awards_text": "",
    "skills_text": "Python | 4 | 课程项目\nSQL | 3 | 课程设计",
    "availability_from": "2026-12-01",
    "availability_note": "",
    "target_job_id": "",
}


def create_job(client):
    response = client.post("/jobs/new", data=JOB_DATA, follow_redirects=False)
    assert response.status_code == 303
    return int(response.headers["location"].split("/")[-1])


def add_skills(job_id):
    with SessionLocal() as db:
        db.add_all(
            [
                JobSkill(
                    job_id=job_id,
                    name="Python",
                    category="编程",
                    importance="must",
                    required_level=5,
                    sort_order=0,
                ),
                JobSkill(
                    job_id=job_id,
                    name="SQL",
                    category="数据",
                    importance="nice",
                    required_level=3,
                    sort_order=1,
                ),
            ]
        )
        db.commit()


def test_student_sees_match_and_gaps(client):
    make_teacher(client)
    job_id = create_job(client)
    add_skills(job_id)

    client.post("/logout", follow_redirects=False)
    make_student(client)
    client.post("/profile", data=PROFILE_DATA, follow_redirects=False)

    response = client.get(f"/jobs/{job_id}")

    assert response.status_code == 200
    assert "匹配度" in response.text
    assert "待补齐技能" in response.text
    assert "Python" in response.text


def test_student_dashboard_shows_recommendations(client):
    make_teacher(client)
    job_id = create_job(client)
    add_skills(job_id)

    client.post("/logout", follow_redirects=False)
    make_student(client)
    client.post("/profile", data=PROFILE_DATA, follow_redirects=False)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "推荐岗位" in response.text
    assert "AI 算法实习生" in response.text
```

Create `tests/test_seed.py`:

```python
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Job, JobSkill, StudentProfile, User
from scripts.seed import seed_database


def test_seed_database_is_idempotent():
    with SessionLocal() as db:
        first = seed_database(db)
        second = seed_database(db)

        assert first["teacher"] == "teacher"
        assert second["teacher"] == "teacher"
        assert db.scalar(select(func.count()).select_from(User)) == 2
        assert db.scalar(select(func.count()).select_from(Job)) == 1
        assert db.scalar(select(func.count()).select_from(JobSkill)) >= 3
        assert db.scalar(select(func.count()).select_from(StudentProfile)) == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/test_gap_view.py tests/test_seed.py -v
```

Expected: fails because the templates do not show match data and `scripts.seed` does not exist.

- [ ] **Step 3: Add match data to the job detail route**

Modify `app/routers/jobs.py` imports:

```python
from app.models import Company, Job, JobSkill, StudentProfile, User
from app.services.matching import compute_match
```

Replace `job_detail` with:

```python
@router.get("/{job_id}")
def job_detail(
    job_id: int,
    request: Request,
    user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_job_or_404(db, job_id)
    can_edit = bool(user and can_edit_job(user, job))

    match = None
    profile = None
    if user is not None and user.role == "student":
        profile = db.get(StudentProfile, user.id)
        if profile is not None:
            match = compute_match(profile.skills_json or [], job.skills)

    return render(
        request,
        "jobs/detail.html",
        {
            "job": job,
            "can_edit": can_edit,
            "match": match,
            "profile": profile,
        },
    )
```

- [ ] **Step 4: Add the match card to the job detail template**

Append this block to `app/templates/jobs/detail.html`, inside the right column (`col-lg-4`), after the existing "岗位信息" card:

```html
    {% if user and user.role == 'student' %}
    <div class="card mt-3">
      <div class="card-header">我的匹配情况</div>
      <div class="card-body">
        {% if match is none %}
        <p class="mb-2">先完善你的技能资料，才能计算匹配度。</p>
        <a class="btn btn-sm btn-primary" href="/profile">完善资料</a>
        {% elif not match.has_job_skills %}
        <p class="text-muted mb-0">岗位技能尚未分析，暂时无法计算匹配度。</p>
        {% else %}
        <div class="d-flex align-items-baseline gap-2 mb-2">
          <span class="display-6 fw-bold">{{ match.score }}%</span>
          <span class="text-muted">匹配度</span>
        </div>
        {% if match.gaps %}
        <div class="fw-semibold mb-2">待补齐技能</div>
        <ul class="mb-0 ps-3">
          {% for gap in match.gaps %}
          <li>{{ gap.name }}：{{ gap.student_level }} / {{ gap.required_level }}（{% if gap.importance == 'must' %}必须{% else %}加分{% endif %}）</li>
          {% endfor %}
        </ul>
        {% else %}
        <p class="text-success mb-0">技能要求已全部达到。</p>
        {% endif %}
        {% endif %}
      </div>
    </div>
    {% endif %}
```

- [ ] **Step 5: Add recommendations to the student dashboard route**

Modify `app/routers/dashboard.py` imports:

```python
from app.services.matching import compute_match
```

Replace the student branch of `dashboard` with:

```python
    profile = db.get(StudentProfile, user.id)
    skills = (profile.skills_json if profile else []) or []
    filled = 0
    if profile is not None:
        for value in [
            profile.summary,
            profile.education_json,
            profile.projects_json,
            profile.internships_json,
            profile.awards_json,
            profile.skills_json,
        ]:
            if value:
                filled += 1
    completion = round(filled / 6 * 100)

    jobs = db.scalars(
        select(Job)
        .options(selectinload(Job.company), selectinload(Job.skills))
        .where(Job.status == "open")
        .order_by(Job.created_at.desc())
        .limit(20)
    ).all()

    recommendations = []
    for job in jobs:
        result = compute_match(skills, job.skills)
        if result.has_job_skills:
            recommendations.append(
                {
                    "job": job,
                    "score": result.score,
                    "gap_count": len(result.gaps),
                }
            )
    recommendations.sort(key=lambda item: item["score"], reverse=True)
    recommendations = recommendations[:5]

    return render(
        request,
        "dashboard/student.html",
        {
            "completion": completion,
            "skill_count": len(skills),
            "jobs": jobs[:5],
            "recommendations": recommendations,
        },
    )
```

- [ ] **Step 6: Add the recommendation card to the student dashboard template**

Insert this block in `app/templates/dashboard/student.html`, before the existing "最新岗位" card:

```html
<div class="card mb-4">
  <div class="card-header">推荐岗位</div>
  <div class="card-body p-0">
    {% if recommendations %}
    <div class="list-group list-group-flush">
      {% for item in recommendations %}
      <a class="list-group-item list-group-item-action" href="/jobs/{{ item.job.id }}">
        <div class="d-flex justify-content-between align-items-center">
          <div>
            <div class="fw-semibold">{{ item.job.title }}</div>
            <div class="form-hint">{{ item.job.company.name }} · 待补齐 {{ item.gap_count }} 项技能</div>
          </div>
          <span class="badge text-bg-primary">{{ item.score }}%</span>
        </div>
      </a>
      {% endfor %}
    </div>
    {% else %}
    <div class="p-4 text-muted">先完善技能资料，系统会按匹配度推荐岗位。</div>
    {% endif %}
  </div>
</div>
```

- [ ] **Step 7: Create the demo seed script**

Create `scripts/__init__.py` (empty file).

Create `scripts/seed.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.auth import hash_password
from app.config import settings
from app.db import SessionLocal, init_db
from app.models import Company, Job, JobSkill, StudentProfile, User

TEACHER_USERNAME = "teacher"
STUDENT_USERNAME = "student"


def seed_database(db) -> dict:
    teacher = db.scalar(
        select(User).where(User.username == TEACHER_USERNAME)
    )
    if teacher is None:
        teacher = User(
            username=TEACHER_USERNAME,
            password_hash=hash_password("Teacher123!"),
            real_name="李老师",
            role="teacher",
            major="人工智能",
        )
        db.add(teacher)
        db.flush()

    student = db.scalar(
        select(User).where(User.username == STUDENT_USERNAME)
    )
    if student is None:
        student = User(
            username=STUDENT_USERNAME,
            password_hash=hash_password("Student123!"),
            real_name="张三",
            role="student",
            major="人工智能",
            grade="2024",
        )
        db.add(student)
        db.flush()

    profile = db.get(StudentProfile, student.id)
    if profile is None:
        profile = StudentProfile(
            user_id=student.id,
            summary="热爱 AI 工程实践，希望成为算法工程师。",
            education_json=[
                {
                    "school": "示例大学",
                    "major": "人工智能",
                    "degree": "本科",
                    "period": "2023-2027",
                }
            ],
            skills_json=[
                {"name": "Python", "level": 3, "evidence": "课程项目"},
                {"name": "SQL", "level": 3, "evidence": "课程设计"},
            ],
            projects_json=[
                {
                    "name": "智能简历系统",
                    "role": "后端",
                    "period": "2026.03-2026.05",
                    "description": "使用 FastAPI 与 LLM 生成简历。",
                }
            ],
            internships_json=[],
            awards_json=[{"name": "校级奖学金"}],
            availability_from="2026-12-01",
            availability_note="每周可实习 4 天",
        )
        db.add(profile)

    company = db.scalar(
        select(Company).where(Company.name == "示例科技有限公司")
    )
    if company is None:
        company = Company(
            name="示例科技有限公司",
            industry="人工智能",
            size="100-499人",
            location="杭州",
            created_by=teacher.id,
        )
        db.add(company)
        db.flush()

    job = db.scalar(
        select(Job).where(Job.title == "AI 算法实习生")
    )
    if job is None:
        job = Job(
            company_id=company.id,
            title="AI 算法实习生",
            description="参与模型训练与数据处理。",
            requirements="熟悉 Python，了解 PyTorch。",
            location="杭州",
            salary_range="150-200/天",
            headcount=2,
            deadline="2026-12-31",
            expected_start_date="2026-12-01",
            created_by=teacher.id,
        )
        db.add(job)
        db.flush()

    existing_skills = db.scalars(
        select(JobSkill).where(JobSkill.job_id == job.id)
    ).all()
    if not existing_skills:
        db.add_all(
            [
                JobSkill(
                    job_id=job.id,
                    name="Python",
                    category="编程",
                    importance="must",
                    required_level=4,
                    sort_order=0,
                ),
                JobSkill(
                    job_id=job.id,
                    name="PyTorch",
                    category="算法",
                    importance="nice",
                    required_level=3,
                    sort_order=1,
                ),
                JobSkill(
                    job_id=job.id,
                    name="SQL",
                    category="数据",
                    importance="nice",
                    required_level=3,
                    sort_order=2,
                ),
                JobSkill(
                    job_id=job.id,
                    name="沟通表达",
                    category="通用",
                    importance="must",
                    required_level=3,
                    sort_order=3,
                ),
            ]
        )

    db.commit()
    return {
        "teacher": TEACHER_USERNAME,
        "student": STUDENT_USERNAME,
        "job": job.title,
    }


if __name__ == "__main__":
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    with SessionLocal() as db:
        summary = seed_database(db)

    print("种子数据已写入：")
    print("教师账号：teacher / Teacher123!")
    print("学生账号：student / Student123!")
    print(summary)
```

- [ ] **Step 8: Update the README with seed and phase status**

Replace the contents of `README.md` with:

```markdown
# AI 职业发展与面试指导平台

课程项目：从企业岗位技能拆解，到学生能力自评、AI 简历与 AI 视频面试。

## 本地运行

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

打开 <http://127.0.0.1:8000>。

在 `.env` 中填写 `DEEPSEEK_API_KEY` 后，岗位页的“AI 分析技能”才可用；未填写时会显示明确错误，不影响其他功能。

## 种子数据

```bash
python -m scripts.seed
```

- 教师：`teacher / Teacher123!`
- 学生：`student / Student123!`

## 测试

```bash
pytest
```

## 当前阶段

- P1：认证、岗位、AI 技能拆解、学生资料、基础匹配（本阶段）
- P2：AI 简历生成与导出
- P3：异步视频模拟面试
- P4：教师匹配、批量导出、使用记录
- P5：部署与提交物

## 远程仓库

```bash
git remote add origin https://github.com/yu1gg/task1.git
```

首次推送前先确认本地提交内容。
```

- [ ] **Step 9: Run the tests to verify they pass**

Run:

```bash
pytest tests/test_gap_view.py tests/test_seed.py -v
```

Expected:

```text
tests/test_gap_view.py::test_student_sees_match_and_gaps PASSED
tests/test_gap_view.py::test_student_dashboard_shows_recommendations PASSED
tests/test_seed.py::test_seed_database_is_idempotent PASSED
```

- [ ] **Step 10: Run the full test suite and a manual smoke test**

Run:

```bash
pytest -v
```

Expected: all tests pass.

Start the app:

```bash
uvicorn app.main:app --reload
```

Manual smoke checklist:

1. Open <http://127.0.0.1:8000> and confirm the landing page renders with Bootstrap styles.
2. Register a student and confirm redirect to `/dashboard`.
3. Open `/profile`, fill the example text formats, save, and confirm the values persist after refresh.
4. Log in as the seeded teacher (`teacher / Teacher123!`), create a job, and confirm it appears in `/jobs`.
5. Without a real API key, click “AI 分析技能” and confirm a readable error message appears.
6. With a real `DEEPSEEK_API_KEY`, run extraction and confirm skill rows appear and can be edited.
7. Log in as the seeded student, open the job, and confirm the match score and gap list render.

- [ ] **Step 11: Commit and update the roadmap**

Run:

```bash
git add app/routers/jobs.py app/routers/dashboard.py app/templates/jobs/detail.html app/templates/dashboard/student.html scripts README.md tests/test_gap_view.py tests/test_seed.py
git commit -m "feat: add gap view, recommendations, seed data and docs"
```

Update `docs/superpowers/plans/2026-11-14-roadmap.md` by checking the P1 box:

```markdown
- [x] P1 完成
```

Then commit the roadmap:

```bash
git add docs/superpowers/plans/2026-11-14-roadmap.md
git commit -m "docs: mark P1 complete"
```

---

## Self-Review

### Spec coverage for this plan

| Spec requirement | Implemented in |
|---|---|
| 学生/校友自由注册，教师邀请码 | Task 3 |
| 角色首页 | Task 4 |
| 企业岗位录入（教师/学生/校友） | Task 5 |
| AI 岗位技能拆解与教师修正 | Tasks 7–8 |
| 学生技能自评与项目证据 | Task 9 |
| 低年级引导：岗位差距与学习方向基础版 | Task 10 |
| 使用记录（注册、登录、岗位、技能、资料） | Tasks 3, 5, 8, 9 |
| 基础匹配算法（规则分 + 差距） | Task 6 |
| 演示种子数据 | Task 10 |

Resume, interview, teacher ranking, batch export, and usage CSV are intentionally left for P2–P4.

### Placeholder scan

- No `TBD`, `TODO`, or “implement later” steps.
- Every code step includes the actual code.
- Every test step includes the actual test code and expected result.

### Type consistency

- `LLMClient` / `get_llm_client` / `LLMProtocol` / `LLMError` names are consistent across Tasks 7–8.
- `JobSkillExtraction` / `JobSkillItem` names are consistent.
- `MatchResult` / `MatchGap` / `compute_match` / `normalize_skill` names are consistent across Tasks 6 and 10.
- `StudentProfile` JSON fields match the parser outputs and templates.
- `JobSkill.importance` is always `"must"` or `"nice"`.
- `UsageEvent` fields match `log_event` arguments.
- Template variables passed by routers match the variables used in templates.

### Known deliberate simplifications

- Textarea formats instead of dynamic structured form rows; this is intentional for the 2-week timeline and is testable.
- No CSRF token; `SameSite=Lax` session cookie is used. This is a documented MVP limitation.
- No email verification, password reset, or account lockout.
- No company account; teachers handle matching and batch export in P4.
- HTTP deployment limitation and asynchronous video interview are addressed in P3/P5.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-11-14-foundation-auth-jobs.md`. Two execution options:**

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

Which approach?

```
```
