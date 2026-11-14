from datetime import datetime, timedelta

from sqlalchemy import select

from app.db import SessionLocal
from app.models import ResumeExportTask, ResumeExportItem, StudentProfile, User
from tests.helpers import make_student, make_teacher
from tests.test_jobs import create_job


def setup_export(client):
    make_student(client)
    make_teacher(client)
    job_id = int(create_job(client).headers['location'].split('/')[-1])
    with SessionLocal() as db:
        student_id = db.scalar(select(User.id).where(User.role == 'student'))
    return job_id, student_id


def create_export(client, job_id, student_id, key='a' * 32):
    return client.post(f'/teacher/jobs/{job_id}/resume-exports', data={
        'student_ids': [student_id], 'request_key': key,
    }, follow_redirects=False)


def test_create_idempotent_snapshot_and_status(client):
    job, student = setup_export(client)
    result = create_export(client, job, student)
    assert result.status_code == 303
    assert create_export(client, job, student).headers['location'] == result.headers['location']
    status = client.get(result.headers['location'] + '/status').json()
    assert status['total'] == 1
    assert status['download_url'] is None
    assert status['items'][0]['name'] == '张三'
    assert client.get(result.headers['location']).status_code == 200
    with SessionLocal() as db:
        assert len(db.scalars(select(ResumeExportTask)).all()) == 1
        item = db.scalar(select(ResumeExportItem))
        assert item.snapshot_json['contact']['allowed'] is False


def test_validation_and_key_reuse(client):
    job, student = setup_export(client)
    assert create_export(client, job, student, 'bad').status_code == 422
    assert create_export(client, job, student).status_code == 303
    other_job = int(create_job(client).headers['location'].split('/')[-1])
    assert create_export(client, other_job, student).status_code == 409


def test_ownership_expiry_and_retry(client):
    job, student = setup_export(client)
    url = create_export(client, job, student).headers['location']
    assert client.post(url + '/retry').status_code == 409
    with SessionLocal() as db:
        task = db.scalar(select(ResumeExportTask))
        task.status = 'failed'
        db.scalar(select(ResumeExportItem)).status = 'failed'
        db.commit()
    assert client.post(url + '/retry').status_code == 202
    assert client.post(url + '/retry').status_code == 409
    with SessionLocal() as db:
        db.scalar(select(ResumeExportTask)).expires_at = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.get(url + '/status').json()['status'] == 'expired'
    assert client.get(url + '/download').status_code == 409
    make_teacher(client, username='otherteacher')
    assert client.get(url + '/status').status_code == 404
    make_student(client, username='otherstudent')
    assert client.get(url + '/status').status_code == 403
    client.post('/logout')
    assert client.get(url + '/status', follow_redirects=False).status_code == 303


def test_contact_change_invalidates_and_cleans(client, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, 'data_dir', tmp_path)
    job, student = setup_export(client)
    with SessionLocal() as db:
        profile = db.get(StudentProfile, student)
        if profile is None:
            profile = StudentProfile(user_id=student)
            db.add(profile)
        profile.share_contacts = True
        profile.phone = '123456789'
        db.commit()
    url = create_export(client, job, student).headers['location']
    root = tmp_path / 'resume_exports'
    root.mkdir()
    archive = root / 'test.zip'
    archive.write_bytes(b'private')
    with SessionLocal() as db:
        task = db.scalar(select(ResumeExportTask))
        task.status, task.archive_path = 'completed', 'test.zip'
        db.scalar(select(ResumeExportItem)).status = 'completed'
        db.commit()
    result = client.get(url + '/download')
    assert result.status_code == 200
    assert result.headers['cache-control'] == 'no-store'
    assert 'archive_path' not in client.get(url + '/status').text
    with SessionLocal() as db:
        db.get(StudentProfile, student).contact_revision += 1
        db.commit()
    assert client.get(url + '/status').json()['status'] == 'invalidated'
    assert not archive.exists()
    assert client.post(url + '/retry').status_code == 409
    with SessionLocal() as db:
        assert 'contact' not in db.scalar(select(ResumeExportItem)).snapshot_json


def test_missing_provider_and_invalid_students(client, monkeypatch):
    from app.config import settings
    job, student = setup_export(client)
    monkeypatch.setattr(settings, 'deepseek_api_key', '')
    assert create_export(client, job, student).status_code == 503
    monkeypatch.setattr(settings, 'deepseek_api_key', 'test-key')
    assert create_export(client, job, 99999).status_code == 422
    response = client.post(f'/teacher/jobs/{job}/resume-exports', data={
        'student_ids': [student, student], 'request_key': 'b' * 32})
    assert response.status_code == 422
    response = client.post(f'/teacher/jobs/{job}/resume-exports', data={
        'student_ids': list(range(1, 12)), 'request_key': 'b' * 32})
    assert response.status_code == 422
