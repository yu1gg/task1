from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Company, Job
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


def test_edit_job_updates_fields_and_company(client):
    make_teacher(client)
    response = create_job(client)
    job_id = int(response.headers["location"].split("/")[-1])

    response = client.post(
        f"/jobs/{job_id}/edit",
        data={
            **JOB_DATA,
            "title": "高级 AI 算法实习生",
            "industry": "大模型",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    with SessionLocal() as db:
        job = db.get(Job, job_id)
        assert job.title == "高级 AI 算法实习生"
        assert job.company.industry == "大模型"


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
