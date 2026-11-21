from datetime import datetime, timedelta
import zipfile
import pytest
from sqlalchemy import select
from app.db import SessionLocal
from app.models import User, Job, Company, ResumeExportTask, ResumeExportItem, StudentProfile
from app.services.resume_exports import snapshot_student, resolve_export_file
from app.services.resume_export_worker import ResumeExportWorker

class LLM:
    def chat_json(self, *args):
        return {'summary': True}

def seed(count=2):
    with SessionLocal() as db:
        teacher = User(username='teacher', password_hash='x', real_name='老师', role='teacher')
        db.add(teacher)
        db.flush()
        company = Company(name='Co', created_by=teacher.id)
        db.add(company)
        db.flush()
        job = Job(company_id=company.id, title='Engineer', created_by=teacher.id)
        db.add(job)
        db.flush()
        task = ResumeExportTask(teacher_id=teacher.id, job_id=job.id, request_key='test', expires_at=datetime.utcnow()+timedelta(hours=24), job_snapshot=dict(title='工程师', description='', requirements='', skills=[]))
        db.add(task)
        db.flush()
        for i in range(count):
            user = User(username=f's{i}', password_hash='x', real_name=f'=学生{i}')
            db.add(user)
            db.flush()
            profile = StudentProfile(user_id=user.id, summary='真实资料', phone='123', email='x@y', share_contacts=True, contact_revision=1)
            db.add(profile)
            db.flush()
            db.add(ResumeExportItem(task_id=task.id, student_id=user.id, snapshot_json=snapshot_student(user, profile)))
        db.commit()
        return task.id

def test_worker_generates_and_packages(monkeypatch, tmp_path):
    monkeypatch.setattr('app.config.settings.data_dir', tmp_path)
    key = seed()
    worker = ResumeExportWorker(llm=LLM())
    assert worker.run_once()
    assert worker.run_once()
    assert worker.run_once()
    with SessionLocal() as db:
        task = db.get(ResumeExportTask, key)
        assert task.status == 'completed'
        with zipfile.ZipFile(resolve_export_file(task.archive_path)) as archive:
            assert len(archive.namelist()) == 3
            text = archive.read('manifest.csv').decode('utf-8-sig')
            assert "'=学生" in text
            assert '123' not in text
    assert not worker.run_once()

def test_revocation_and_expiry_remove_files(monkeypatch, tmp_path):
    monkeypatch.setattr('app.config.settings.data_dir', tmp_path)
    key = seed(1)
    worker = ResumeExportWorker(llm=LLM())
    worker.run_once()
    with SessionLocal() as db:
        profile = db.scalar(select(StudentProfile))
        profile.share_contacts = False
        db.commit()
    worker.run_once()
    with SessionLocal() as db:
        task = db.get(ResumeExportTask, key)
        assert task.status == 'invalidated'
        assert not db.scalar(select(ResumeExportItem)).file_path
        assert 'contact' not in db.scalar(select(ResumeExportItem)).snapshot_json
    assert not list(tmp_path.rglob('*.docx'))

def test_failure_is_finite_and_recovery_keeps_success(monkeypatch, tmp_path):
    monkeypatch.setattr('app.config.settings.data_dir', tmp_path)
    key = seed(1)
    worker = ResumeExportWorker(llm=LLM())
    def fail(*args):
        raise RuntimeError('secret')
    monkeypatch.setattr('app.services.resume_export_worker.generate_resume', fail)
    worker.run_once()
    worker.run_once()
    assert not worker.run_once()
    with SessionLocal() as db:
        task = db.get(ResumeExportTask, key)
        assert task.status == 'failed' and task.archive_path is None
        assert 'secret' not in db.scalar(select(ResumeExportItem)).error_message



def test_recovery_reuses_success_and_expiry_scrubs(monkeypatch, tmp_path):
    monkeypatch.setattr('app.config.settings.data_dir', tmp_path)
    key = seed(2)
    worker = ResumeExportWorker(llm=LLM())
    worker.run_once()
    with SessionLocal() as db:
        items = db.scalars(select(ResumeExportItem).order_by(ResumeExportItem.id)).all()
        preserved = items[0].file_path
        items[1].status = 'processing'
        db.commit()
    worker.recover()
    with SessionLocal() as db:
        items = db.scalars(select(ResumeExportItem).order_by(ResumeExportItem.id)).all()
        assert items[0].status == 'completed' and items[0].file_path == preserved
        assert items[1].status == 'pending'
        assert db.get(ResumeExportTask, key).status == 'queued'
    worker.run_once()
    worker.run_once()
    with SessionLocal() as db:
        task = db.get(ResumeExportTask, key)
        task.expires_at = datetime.utcnow()-timedelta(seconds=1)
        db.commit()
    worker.run_once()
    with SessionLocal() as db:
        task = db.get(ResumeExportTask, key)
        assert task.status == 'expired' and task.archive_path is None
        assert task.job_snapshot == {}
        assert all('profile' not in i.snapshot_json for i in db.scalars(select(ResumeExportItem)))
    assert not list(tmp_path.rglob('*.docx'))
    assert not list(tmp_path.rglob('*.zip'))

def test_revocation_during_generation_discards_result(monkeypatch, tmp_path):
    monkeypatch.setattr('app.config.settings.data_dir', tmp_path)
    key = seed(1)
    class RevokingLLM:
        def chat_json(self, *args):
            with SessionLocal() as db:
                profile = db.scalar(select(StudentProfile))
                profile.share_contacts = False
                db.commit()
            return {'summary': True}
    worker = ResumeExportWorker(llm=RevokingLLM())
    worker.run_once()
    with SessionLocal() as db:
        assert db.get(ResumeExportTask, key).status == 'invalidated'
        assert not db.scalar(select(ResumeExportItem)).file_path
    assert not list(tmp_path.rglob('*.docx'))

def test_single_consumer_lock_precedes_recovery(monkeypatch):
    from app.services import resume_export_worker as module
    first = ResumeExportWorker(llm=LLM())
    second = ResumeExportWorker(llm=LLM())
    monkeypatch.setattr(first, '_loop', lambda: first._stop.wait(5))
    # Simulate another live consumer without starting a leaking thread.
    assert module._consumer_lock.acquire(blocking=False)
    try:
        monkeypatch.setattr(second, 'recover', lambda: pytest.fail('must not recover while running'))
        with pytest.raises(RuntimeError):
            second.start()
    finally:
        module._consumer_lock.release()

@pytest.mark.parametrize('stage', ['generate', 'package', 'package_error'])
def test_terminal_status_wins_validation_race(monkeypatch, tmp_path, stage):
    from sqlalchemy import update
    monkeypatch.setattr('app.config.settings.data_dir', tmp_path)
    key = seed(1)
    worker = ResumeExportWorker(llm=LLM())
    if stage != 'generate':
        worker.run_once()
    original = worker._valid
    calls = 0
    def interleaved(db, task):
        nonlocal calls
        valid = original(db, task)
        calls += 1
        if calls == 2:
            with SessionLocal() as other:
                other.execute(update(ResumeExportTask).where(ResumeExportTask.id == key).values(status='invalidated'))
                other.commit()
        return valid
    monkeypatch.setattr(worker, '_valid', interleaved)
    if stage == 'package_error':
        # Invalidate after the exception handler validates its stale task.
        def error_interleaved(db, task):
            valid = original(db, task)
            with SessionLocal() as other:
                other.execute(update(ResumeExportTask).where(ResumeExportTask.id == key).values(status='invalidated'))
                other.commit()
            return valid
        # Enter package directly so the injection targets exception handling.
        def raise_package(*args):
            monkeypatch.setattr(worker, '_valid', error_interleaved)
            raise OSError('missing')
        monkeypatch.setattr('app.services.resume_export_worker.atomic_file', raise_package)
        monkeypatch.setattr(worker, '_valid', original)
        worker._package(key)
    elif stage == 'package':
        worker._package(key)
    else:
        worker.run_once()
    with SessionLocal() as db:
        task = db.get(ResumeExportTask, key)
        assert task.status == 'invalidated'
        assert task.archive_path is None
        if stage == 'generate':
            assert db.scalar(select(ResumeExportItem)).file_path is None
    assert not list(tmp_path.rglob('*.zip'))

def test_cleanup_retries_permission_denied(monkeypatch, tmp_path):
    from pathlib import Path
    monkeypatch.setattr('app.config.settings.data_dir', tmp_path)
    key = seed(1)
    worker = ResumeExportWorker(llm=LLM())
    worker.run_once()
    with SessionLocal() as db:
        item = db.scalar(select(ResumeExportItem))
        retained = item.file_path
        db.get(ResumeExportTask, key).expires_at = datetime.utcnow()-timedelta(seconds=1)
        db.commit()
    original = Path.unlink
    denied = True
    def transient(self, *args, **kwargs):
        nonlocal denied
        if self.name == retained and denied:
            denied = False
            raise PermissionError('busy')
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Path, 'unlink', transient)
    worker.run_once()
    with SessionLocal() as db:
        assert db.scalar(select(ResumeExportItem)).file_path == retained
    worker.run_once()
    with SessionLocal() as db:
        assert db.scalar(select(ResumeExportItem)).file_path is None
    assert not resolve_export_file(retained).exists()


def test_recover_only_removes_generated_unreferenced_files(monkeypatch, tmp_path):
    from uuid import uuid4
    from app.services.resume_exports import export_root
    monkeypatch.setattr('app.config.settings.data_dir', tmp_path)
    seed(1)
    worker = ResumeExportWorker(llm=LLM())
    worker.run_once()
    root = export_root()
    garbage = [root/(uuid4().hex+suffix) for suffix in ('.docx', '.zip', '.docx.tmp', '.zip.tmp')]
    for path in garbage:
        path.write_bytes(b'orphan')
    manual = root/'manual.docx'
    manual.write_bytes(b'keep')
    with SessionLocal() as db:
        referenced = resolve_export_file(db.scalar(select(ResumeExportItem)).file_path)
    worker.recover()
    assert all(not p.exists() for p in garbage)
    assert manual.exists() and referenced.exists()


def test_filename_has_portable_byte_length():
    from app.services.resume_export_worker import safe_filename
    value = safe_filename('学'*64, 123456, '岗'*120)
    assert len(value.encode('utf-8')) < 200

def test_old_archive_cleanup_retries_without_restart(monkeypatch, tmp_path):
    from pathlib import Path
    monkeypatch.setattr('app.config.settings.data_dir', tmp_path)
    key = seed(1)
    worker = ResumeExportWorker(llm=LLM())
    worker.run_once()
    worker.run_once()
    with SessionLocal() as db:
        task = db.get(ResumeExportTask, key)
        old = task.archive_path
        task.status = 'queued'
        db.commit()
    original = Path.unlink
    denied = True
    def transient(self, *args, **kwargs):
        nonlocal denied
        if self.name == old and denied:
            denied = False
            raise PermissionError('busy')
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Path, 'unlink', transient)
    worker.run_once()
    with SessionLocal() as db:
        new = db.get(ResumeExportTask, key).archive_path
        document = db.scalar(select(ResumeExportItem)).file_path
    assert new != old
    assert resolve_export_file(old).exists()
    worker.run_once()
    assert not resolve_export_file(old).exists()
    assert resolve_export_file(new).exists()
    assert resolve_export_file(document).exists()
