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
    assert "85%" in response.text
    assert "4 / 5" in response.text


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


def test_student_with_empty_skills_gets_zero_and_gaps(client):
    make_teacher(client)
    job_id = create_job(client)
    add_skills(job_id)

    client.post("/logout", follow_redirects=False)
    make_student(client)

    response = client.get(f"/jobs/{job_id}")

    assert response.status_code == 200
    assert "0%" in response.text
    assert "待补齐技能" in response.text


def test_job_without_skills_shows_analysis_prompt(client):
    make_teacher(client)
    job_id = create_job(client)

    client.post("/logout", follow_redirects=False)
    make_student(client)
    client.post("/profile", data=PROFILE_DATA, follow_redirects=False)

    response = client.get(f"/jobs/{job_id}")

    assert "岗位技能尚未分析" in response.text


def test_teacher_does_not_see_match_card(client):
    make_teacher(client)
    job_id = create_job(client)
    add_skills(job_id)

    response = client.get(f"/jobs/{job_id}")

    assert "我的匹配情况" not in response.text


def test_dashboard_shows_empty_recommendation_state(client):
    make_teacher(client)
    create_job(client)  # no skills, so no recommendations

    client.post("/logout", follow_redirects=False)
    make_student(client)
    client.post("/profile", data=PROFILE_DATA, follow_redirects=False)

    response = client.get("/dashboard")

    assert "推荐岗位" in response.text
    assert "先完善技能资料" in response.text
