from datetime import date
from types import SimpleNamespace

import pytest

from app.services.teacher_matching import parse_date, explain_match
from app.services.llm import LLMError


def test_real_dates_and_historical_bad_values():
    assert parse_date('2026-02-28') == date(2026, 2, 28)
    for value in [None, '', '2026-02-30', '2026-2-1', 'bad']:
        assert parse_date(value) is None


class FakeLLM:
    def __init__(self, results):
        self.results = iter(results)
        self.prompts = []

    def chat_json(self, system, user):
        self.prompts.append(user)
        return next(self.results)


def test_explanation_retries_and_keeps_rule_score():
    llm = FakeLLM([{}, {'reasons':['原因一','原因二'], 'suggestions':['练习','项目','复习']}])
    result = explain_match([{'name':'Python','level':3}], [SimpleNamespace(name='Python',required_level=3,importance='must')], llm)
    assert result['score'] == 100
    assert len(llm.prompts) == 2


def test_explanation_rejects_extra_fields():
    llm = FakeLLM([{'reasons':['一','二'], 'suggestions':['一','二','三'], 'score':999}] * 3)
    with pytest.raises(LLMError):
        explain_match([], [], llm)
    assert len(llm.prompts) == 3


@pytest.fixture()
def teacher_client(client):
    from app.main import app
    from app.routers.teacher import router
    from tests.helpers import make_teacher
    if not any(getattr(route, 'path', '') == '/teacher/usage' for route in app.routes):
        app.include_router(router)
    make_teacher(client)
    return client


def seed_job_students():
    from app.db import SessionLocal
    from app.models import User, Company, Job, JobSkill, StudentProfile
    with SessionLocal() as db:
        teacher = db.query(User).filter_by(role='teacher').first()
        company = Company(name='测试公司', created_by=teacher.id)
        db.add(company)
        db.flush()
        job = Job(company_id=company.id, title='测试岗位', created_by=teacher.id)
        db.add(job)
        db.flush()
        db.add(JobSkill(job_id=job.id, name='Python', required_level=3, importance='must'))
        ids = []
        for name, role, available in [('甲学生','student','2026-12-01'),('乙学生','student','2026-12-02'),('丙学生','student','bad'),('非学生','alumni','2026-12-01')]:
            student = User(username=name, real_name=name, password_hash='unused', role=role)
            db.add(student)
            db.flush()
            db.add(StudentProfile(user_id=student.id, skills_json=[{'name':'Python','level':3}], availability_from=available))
            ids.append(student.id)
        db.commit()
        return job.id, ids


def test_teacher_ranking_dates_nonce_and_explanation(teacher_client):
    import re
    from app.main import app
    from app.services.llm import get_llm_client
    job_id, ids = seed_job_students()
    response = teacher_client.get(f'/teacher/jobs/{job_id}/matches')
    assert response.status_code == 200
    assert response.text.index('甲学生') < response.text.index('乙学生') < response.text.index('丙学生')
    assert '非学生' not in response.text
    nonce = re.search('name="request_key" value="([a-f0-9]{32})"', response.text).group(1)
    response = teacher_client.get(f'/teacher/jobs/{job_id}/matches?available_by=2026-12-01')
    assert '甲学生' in response.text and '乙学生' not in response.text and '丙学生' not in response.text
    assert nonce not in response.text
    assert teacher_client.get(f'/teacher/jobs/{job_id}/matches?available_by=2026-02-30').status_code == 422
    fake = FakeLLM([{'reasons':['一','二'], 'suggestions':['一','二','三']}])
    app.dependency_overrides[get_llm_client] = lambda: fake
    try:
        result = teacher_client.post(f'/teacher/jobs/{job_id}/students/{ids[0]}/explanation')
        assert result.status_code == 200 and result.json()['score'] == 100
        assert '甲学生' not in fake.prompts[0]
    finally:
        app.dependency_overrides.pop(get_llm_client, None)


def test_teacher_permissions(teacher_client):
    from tests.helpers import make_student
    make_student(teacher_client)
    assert teacher_client.get('/teacher/usage').status_code == 403
    assert teacher_client.get('/teacher/usage/export.csv').status_code == 403
    assert teacher_client.get('/teacher/jobs/1/matches').status_code == 403


def test_missing_profile_unanalyzed_job_and_safe_llm_error(teacher_client):
    from app.db import SessionLocal
    from app.main import app
    from app.models import User, JobSkill
    from app.services.llm import get_llm_client
    job_id, ids = seed_job_students()
    class Broken:
        def chat_json(self, system, user):
            raise LLMError('secret-key upstream-body')
    app.dependency_overrides[get_llm_client] = lambda: Broken()
    try:
        result = teacher_client.post(f'/teacher/jobs/{job_id}/students/{ids[0]}/explanation')
        assert result.status_code == 502
        assert 'secret-key' not in result.text
    finally:
        app.dependency_overrides.pop(get_llm_client, None)
    with SessionLocal() as db:
        db.add(User(username='empty', real_name='缺资料学生', role='student', password_hash='unused'))
        db.query(JobSkill).filter_by(job_id=job_id).delete()
        db.commit()
    result = teacher_client.get(f'/teacher/jobs/{job_id}/matches')
    assert result.status_code == 200
    assert '缺资料学生' in result.text and '暂无技能资料' in result.text and '未分析' in result.text
    assert teacher_client.post(f'/teacher/jobs/{job_id}/students/{ids[0]}/explanation').status_code == 422
