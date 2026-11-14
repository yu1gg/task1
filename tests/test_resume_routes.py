import json
import re

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Company, Job, Resume, StudentProfile, UsageEvent, User
from tests.helpers import make_student, make_teacher


CONTENT = {"name": "张同学", "target_job": "Python 实习生", "summary": "学习 Python"}


def editor_content(response):
    return json.loads(re.search(r'<script id="resume-initial" type="application/json">(.*?)</script>', response.text, re.S).group(1))


def owned_resume(client):
    make_student(client)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == "stu1"))
        item = Resume(student_id=user.id, content_json=CONTENT)
        db.add(item)
        db.commit()
        return item.id


def test_resume_list_and_auth(client):
    assert client.get("/resumes", follow_redirects=False).status_code == 303
    make_teacher(client)
    assert client.get("/resumes").status_code == 403
    client.post("/logout")
    make_student(client)
    assert client.get("/resumes").status_code == 200


def test_edit_save_reopen_print_docx(client):
    rid = owned_resume(client)
    assert client.get(f"/resumes/{rid}/edit").status_code == 200
    content = {**CONTENT, "phone": "13800000000", "summary": "负责接口开发"}
    response = client.post(f"/resumes/{rid}/edit", data={
        "title": "岗位简历", "version": 1, "content_json": json.dumps(content),
    }, follow_redirects=False)
    assert response.status_code == 303
    assert editor_content(client.get(f"/resumes/{rid}/edit"))["summary"] == "负责接口开发"
    printed = client.get(f"/resumes/{rid}/print")
    assert printed.status_code == 200 and "13800000000" in printed.text
    exported = client.get(f"/resumes/{rid}/export.docx")
    assert exported.status_code == 200 and exported.content[:2] == b"PK"
    with SessionLocal() as db:
        assert db.get(Resume, rid).version == 2
        events = db.scalars(select(UsageEvent).where(UsageEvent.event_type == "resume_save")).all()
        assert len(events) == 1 and "13800000000" not in str(events[0].payload_json)


def test_stale_version_and_invalid_input_preserve_data(client):
    rid = owned_resume(client)
    stale = client.post(f"/resumes/{rid}/edit", data={
        "title": "未保存标题", "version": 0,
        "content_json": json.dumps({**CONTENT, "summary": "未保存内容"}),
    })
    assert stale.status_code == 409 and editor_content(stale)["summary"] == "未保存内容"
    invalid = client.post(f"/resumes/{rid}/edit", data={
        "title": "输入仍在", "version": 1,
        "content_json": json.dumps({**CONTENT, "summary": "长" * 121}),
    })
    assert invalid.status_code == 422 and "输入仍在" in invalid.text
    malformed = client.post(f"/resumes/{rid}/edit", data={"version": 1, "content_json": "{"})
    assert malformed.status_code == 422
    with SessionLocal() as db:
        assert db.get(Resume, rid).version == 1
        assert db.get(Resume, rid).content_json == CONTENT


def test_other_student_cannot_read_or_write_resume(client):
    rid = owned_resume(client)
    with SessionLocal() as db:
        # Foreign keys require a real second owner.
        other = User(username="other", real_name="他人", password_hash="unused", role="student")
        db.add(other)
        db.flush()
        db.get(Resume, rid).student_id = other.id
        db.commit()
    for suffix in ("edit", "print", "export.docx"):
        assert client.get(f"/resumes/{rid}/{suffix}").status_code == 404
    assert client.post(f"/resumes/{rid}/edit", data={"version": 1}).status_code == 404


def test_generate_and_failure_are_atomic(client, monkeypatch):
    make_student(client)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == "stu1"))
        company = Company(name="企业", created_by=user.id)
        db.add(company)
        db.flush()
        job = Job(title="Python 实习生", company_id=company.id, created_by=user.id)
        db.add(job)
        db.get(StudentProfile, user.id).summary = "学习 Python"
        db.commit()
        jid = job.id
    from app.routers import resume
    from app.schemas import ResumeContent
    from app.services.llm import LLMError
    monkeypatch.setattr(resume, "generate_resume", lambda *args: ResumeContent(**CONTENT))
    for _ in range(2):
        assert client.post("/resumes/generate", data={"job_id": jid}, follow_redirects=False).status_code == 303
    def fail(*args):
        raise LLMError("模拟调用失败")
    monkeypatch.setattr(resume, "generate_resume", fail)
    response = client.post("/resumes/generate", data={"job_id": jid})
    assert response.status_code == 502 and "简历生成失败" in response.text
    with SessionLocal() as db:
        assert len(db.scalars(select(Resume)).all()) == 2


def test_generation_requires_valid_job_and_profile(client):
    make_student(client)
    assert client.post("/resumes/generate", data={"job_id": "bad"}).status_code == 422
    assert client.post("/resumes/generate", data={"job_id": 999}).status_code == 404


def test_invalid_stale_submission_keeps_original_version(client):
    rid = owned_resume(client)
    response = client.post(f"/resumes/{rid}/edit", data={
        "version": 0, "content_json": json.dumps({**CONTENT, "summary": "字" * 121}),
    })
    assert response.status_code == 422
    assert 'name="version" value="0"' in response.text
    corrected = client.post(f"/resumes/{rid}/edit", data={
        "version": 0, "content_json": json.dumps({**CONTENT, "summary": "修正后的旧输入"}),
    })
    assert corrected.status_code == 409
    with SessionLocal() as db:
        assert db.get(Resume, rid).content_json == CONTENT


def test_export_failure_keeps_saved_resume(client, monkeypatch):
    rid = owned_resume(client)
    from app.routers import resume
    def fail(content):
        raise RuntimeError("private-document-content")
    monkeypatch.setattr(resume, "export_resume_docx", fail)
    response = client.get(f"/resumes/{rid}/export.docx")
    assert response.status_code == 503 and "private-document-content" not in response.text
    with SessionLocal() as db:
        assert db.get(Resume, rid).content_json == CONTENT
