from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Company, Job, UsageEvent
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


def test_student_creator_can_edit_own_job_and_company(client):
    make_student(client)
    response = create_job(
        client,
        company_name="学生创业公司",
        industry="教育科技",
        title="学生自己的岗位",
    )
    job_id = int(response.headers["location"].split("/")[-1])

    response = client.post(
        f"/jobs/{job_id}/edit",
        data={
            **JOB_DATA,
            "company_name": "学生创业公司",
            "industry": "AI 教育",
            "title": "学生自己的岗位（更新）",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    with SessionLocal() as db:
        job = db.get(Job, job_id)
        assert job.title == "学生自己的岗位（更新）"
        assert job.company.industry == "AI 教育"


def test_student_cannot_overwrite_teacher_company_metadata(client):
    make_teacher(client)
    response = create_job(client, title="老师岗位")
    teacher_job_id = int(response.headers["location"].split("/")[-1])

    client.post("/logout", follow_redirects=False)
    make_student(client)
    response = create_job(client, title="学生岗位")
    student_job_id = int(response.headers["location"].split("/")[-1])

    response = client.post(
        f"/jobs/{student_job_id}/edit",
        data={**JOB_DATA, "title": "学生岗位", "industry": "篡改行业"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "企业信息由创建者维护" in response.text

    with SessionLocal() as db:
        company = db.scalar(
            select(Company).where(Company.name == "示例科技有限公司")
        )
        assert company.industry == "人工智能"
        teacher_job = db.get(Job, teacher_job_id)
        assert teacher_job.company.industry == "人工智能"


def test_student_cannot_post_edit_teacher_job(client):
    make_teacher(client)
    response = create_job(client)
    job_id = int(response.headers["location"].split("/")[-1])

    client.post("/logout", follow_redirects=False)
    make_student(client)

    response = client.post(
        f"/jobs/{job_id}/edit",
        data={**JOB_DATA, "title": "越权修改"},
        follow_redirects=False,
    )
    assert response.status_code == 403


def test_missing_job_returns_404(client):
    response = client.get("/jobs/99999")
    assert response.status_code == 404


def test_blank_job_validation_flashes(client):
    make_teacher(client)
    response = client.post(
        "/jobs/new",
        data={**JOB_DATA, "company_name": "", "title": ""},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "企业和岗位名称不能为空" in response.text


def test_job_usage_events_are_logged(client):
    make_teacher(client)
    response = create_job(client)
    job_id = int(response.headers["location"].split("/")[-1])

    client.post(
        f"/jobs/{job_id}/edit",
        data={**JOB_DATA, "title": "更新后的岗位"},
        follow_redirects=False,
    )

    with SessionLocal() as db:
        events = db.scalars(
            select(UsageEvent).where(
                UsageEvent.event_type.in_(["job_create", "job_update"])
            )
        ).all()
        event_types = {event.event_type for event in events}
        assert event_types == {"job_create", "job_update"}


def test_long_job_fields_are_truncated(client):
    make_teacher(client)
    response = create_job(
        client,
        title="T" * 300,
        description="D" * 25000,
    )
    assert response.status_code == 303
    job_id = int(response.headers["location"].split("/")[-1])

    with SessionLocal() as db:
        job = db.get(Job, job_id)
        assert len(job.title) == 120
        assert len(job.description) == 20000
