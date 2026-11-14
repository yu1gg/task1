import pytest
from sqlalchemy import func, select

from app.db import SessionLocal
from app.main import app
from app.models import JobSkill
from app.services.llm import LLMError, get_llm_client
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


class BoomLLM:
    def chat_json(self, system, user):
        raise LLMError("boom")


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


def test_extract_llm_error_preserves_existing_skills(client, fake_llm):
    make_teacher(client)
    job_id = create_job(client)
    client.post(f"/jobs/{job_id}/extract-skills", follow_redirects=False)
    assert skill_count(job_id) == 2

    app.dependency_overrides[get_llm_client] = lambda: BoomLLM()
    try:
        response = client.post(
            f"/jobs/{job_id}/extract-skills", follow_redirects=True
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "boom" in response.text
    assert skill_count(job_id) == 2


def test_update_skills_normalizes_blank_category(client):
    make_teacher(client)
    job_id = create_job(client)

    response = client.post(
        f"/jobs/{job_id}/skills",
        data={
            "skill_name": ["SQL"],
            "skill_category": ["   "],
            "skill_importance": ["nice"],
            "skill_level": ["3"],
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    with SessionLocal() as db:
        skill = db.scalar(
            select(JobSkill).where(JobSkill.job_id == job_id)
        )
        assert skill.category == "通用"


def test_schema_none_name_rejected_and_none_category_defaults():
    from pydantic import ValidationError

    from app.schemas import JobSkillExtraction

    with pytest.raises(ValidationError):
        JobSkillExtraction.model_validate({"skills": [{"name": None}]})

    parsed = JobSkillExtraction.model_validate(
        {"skills": [{"name": "Python", "category": None}]}
    )
    assert parsed.skills[0].category == "通用"
