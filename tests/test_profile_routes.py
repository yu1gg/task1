from sqlalchemy import select

from app.db import SessionLocal
from app.models import Company, Job, StudentProfile, User
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


def test_profile_saves_target_job(client):
    make_student(client)

    with SessionLocal() as db:
        student = db.scalar(select(User).where(User.username == "stu1"))
        company = Company(name="目标公司", created_by=student.id)
        db.add(company)
        db.flush()
        job = Job(
            company_id=company.id,
            title="目标岗位",
            created_by=student.id,
        )
        db.add(job)
        db.commit()
        job_id = job.id

    response = client.post(
        "/profile",
        data={**PROFILE_DATA, "target_job_id": str(job_id)},
        follow_redirects=False,
    )
    assert response.status_code == 303

    with SessionLocal() as db:
        student = db.scalar(select(User).where(User.username == "stu1"))
        profile = db.get(StudentProfile, student.id)
        assert profile.target_job_id == job_id


def test_teacher_cannot_access_student_profile(client):
    make_teacher(client)
    response = client.get("/profile")
    assert response.status_code == 403
