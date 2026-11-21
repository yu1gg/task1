"""One durable export consumer, independent of the interview consumer."""
import csv
from datetime import datetime
from io import BytesIO, StringIO
import logging
import re
import threading
from types import SimpleNamespace
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED
from sqlalchemy import select, update
from app.db import SessionLocal
from app.models import ResumeExportTask, ResumeExportItem, UsageEvent
from app.schemas import ResumeContent
from app.services.llm import get_llm_client
from app.services.resume import generate_resume
from app.services.resume_docx import export_resume_docx
from app.services.resume_exports import (export_root, resolve_export_file, contacts_current,
                                        cleanup_task_files, discard_file)

logger = logging.getLogger(__name__)
_consumer_lock = threading.Lock()


def csvsafe(value):
    value = str(value or '')
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) or value.startswith(('\t', '\r', '\n')) else value


def safe_filename(name, student_id, job):
    def clean(value):
        value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', str(value)).replace('..', '_')
        return value.strip(' .').encode('utf-8')[:72].decode('utf-8', errors='ignore') or 'resume'
    return f'{clean(name)}_{student_id}_{clean(job)}.docx'


def atomic_file(data, suffix):
    export_root().mkdir(parents=True, exist_ok=True)
    name = uuid4().hex + suffix
    temporary = name + '.tmp'
    try:
        resolve_export_file(temporary).write_bytes(data)
        resolve_export_file(temporary).replace(resolve_export_file(name))
        return name
    finally:
        discard_file(temporary)


class ResumeExportWorker:
    def __init__(self, session_factory=SessionLocal, llm=None):
        self.sessions = session_factory
        self.llm = llm if llm is not None else get_llm_client()
        self._stop = threading.Event()
        self._thread = None
        self._lifecycle_lock = threading.Lock()
        self._run_lock = threading.Lock()

    def recover(self):
        with self.sessions() as db:
            db.execute(update(ResumeExportItem).where(ResumeExportItem.status == 'processing', ResumeExportItem.task_id.in_(select(ResumeExportTask.id).where(ResumeExportTask.status.in_(['queued', 'processing'])))).values(status='pending'))
            db.execute(update(ResumeExportTask).where(ResumeExportTask.status == 'processing').values(status='queued'))
            db.commit()
        self._recover_orphans()

    def _recover_orphans(self):
        # Startup holds the consumer lock; normal iterations hold _run_lock.
        # Neither call site overlaps this consumer's generation or packaging.
        with self.sessions() as db:
            references = set(db.scalars(select(ResumeExportTask.archive_path)))
            references.update(db.scalars(select(ResumeExportItem.file_path)))
        referenced = set()
        for name in references:
            if name:
                try:
                    referenced.add(resolve_export_file(name))
                except ValueError:
                    pass
        root = export_root()
        try:
            candidates = list(root.iterdir()) if root.is_dir() else []
        except OSError:
            return
        for path in candidates:
            if (re.fullmatch(r'[0-9a-f]{32}\.(?:docx|zip)(?:\.tmp)?', path.name)
                    and not path.is_symlink() and path.is_file()
                    and path.resolve() not in referenced):
                discard_file(path.name)

    def start(self):
        with self._lifecycle_lock:
            if self._thread and self._thread.is_alive():
                return
            if not _consumer_lock.acquire(blocking=False):
                raise RuntimeError('An export consumer is already running')
            try:
                self.recover()
                self._stop.clear()
                self._thread = threading.Thread(target=self._loop, daemon=True, name='resume-export-worker')
                self._thread.start()
            except BaseException:
                _consumer_lock.release()
                raise

    def stop(self):
        self._stop.set()
        if self._thread:
            if self._thread is threading.current_thread():
                raise RuntimeError('Export consumer cannot join itself')
            self._thread.join()

    def _loop(self):
        try:
            while not self._stop.is_set():
                try:
                    worked = self.run_once()
                except Exception:
                    logger.error('resume_export_iteration_failed')
                    worked = False
                if not worked:
                    self._stop.wait(1)
        finally:
            _consumer_lock.release()

    def _valid(self, db, task):
        db.refresh(task)
        if task.status in ('expired', 'invalidated'):
            return False
        if task.expires_at <= datetime.utcnow():
            task.status = 'expired'
        elif not contacts_current(db, task):
            task.status = 'invalidated'
        else:
            return True
        cleanup_task_files(db, task)
        return False

    def _event(self, db, task, status, student_id=None):
        db.add(UsageEvent(user_id=task.teacher_id, event_type='resume_export', payload_json={
            'task_id': task.id, 'student_id': student_id, 'status': status}))

    def run_once(self):
        with self._run_lock:
            self._recover_orphans()
            return self._run_once()

    def _run_once(self):
        with self.sessions() as db:
            # Completed packages also expire and lose authorization without a download request.
            tasks = db.scalars(select(ResumeExportTask)).all()
            cleaned = False
            for task in tasks:
                if task.status in ('expired', 'invalidated'):
                    cleanup_task_files(db, task)
                elif not self._valid(db, task):
                    cleaned = True
            db.commit()
            task = db.scalar(select(ResumeExportTask).where(ResumeExportTask.status.in_(['queued', 'processing'])).order_by(ResumeExportTask.id))
            if task is None:
                return cleaned
            task_id = task.id
            items = db.scalars(select(ResumeExportItem).where(ResumeExportItem.task_id == task_id).order_by(ResumeExportItem.id)).all()
            if len(items) > 10 or not items:
                db.execute(update(ResumeExportTask).where(ResumeExportTask.id == task_id, ResumeExportTask.status.in_(['queued', 'processing'])).values(status='failed', error_message='批量任务必须包含1至10名学生。'))
                db.commit()
                return True
            item = next((item for item in items if item.status == 'pending'), None)
            if item is not None:
                changed = db.execute(update(ResumeExportItem).where(ResumeExportItem.id == item.id, ResumeExportItem.status == 'pending').values(status='processing')).rowcount
                if not changed:
                    db.rollback()
                    return True
                parent_changed = db.execute(update(ResumeExportTask).where(ResumeExportTask.id == task_id, ResumeExportTask.status.in_(['queued', 'processing'])).values(status='processing')).rowcount
                if not parent_changed:
                    db.rollback()
                    return True
                item_id, snapshot, job_snapshot = item.id, item.snapshot_json, task.job_snapshot
                db.commit()
            elif any(item.status == 'processing' for item in items):
                return False
            else:
                db.rollback()
                item_id = None
        if item_id is not None:
            self._generate(task_id, item_id, snapshot, job_snapshot)
        else:
            self._package(task_id)
        return True

    def _generate(self, task_id, item_id, snapshot, job_snapshot):
        path = None
        adopted = False
        try:
            user = SimpleNamespace(**snapshot['user'])
            profile = SimpleNamespace(**snapshot['profile'])
            job_data = dict(job_snapshot)
            job_data['skills'] = [SimpleNamespace(name=s.get('name', '') if isinstance(s, dict) else s) for s in job_data.get('skills', [])]
            job = SimpleNamespace(**job_data)
            content = generate_resume(user, profile, job, self.llm).model_dump()
            contact = snapshot['contact']
            content.update(phone=contact['phone'] if contact['allowed'] else '', email=contact['email'] if contact['allowed'] else '')
            content = ResumeContent.model_validate(content)
            path = atomic_file(export_resume_docx(content), '.docx')
            with self.sessions() as db:
                task = db.get(ResumeExportTask, task_id)
                if self._valid(db, task) and task.status in ('queued', 'processing'):
                    changed = bool(db.execute(update(ResumeExportItem).where(ResumeExportItem.id == item_id, ResumeExportItem.status == 'processing', ResumeExportItem.task_id.in_(select(ResumeExportTask.id).where(ResumeExportTask.status.in_(['queued', 'processing'])))).values(status='completed', file_path=path, filename=safe_filename(user.real_name, user.id, job.title), error_message=None)).rowcount)
                    if changed:
                        self._event(db, task, 'completed', user.id)
                else:
                    changed = False
                db.commit()
                adopted = changed
        except Exception as exc:
            logger.warning('resume_export_item_failed task_id=%s item_id=%s error_type=%s', task_id, item_id, type(exc).__name__)
            with self.sessions() as db:
                task = db.get(ResumeExportTask, task_id)
                if self._valid(db, task):
                    db.execute(update(ResumeExportItem).where(ResumeExportItem.id == item_id, ResumeExportItem.status == 'processing', ResumeExportItem.task_id.in_(select(ResumeExportTask.id).where(ResumeExportTask.status.in_(['queued', 'processing'])))).values(status='failed', error_message='简历生成失败，请重试。'))
                    self._event(db, task, 'failed', snapshot['user']['id'])
                db.commit()
        finally:
            if not adopted:
                discard_file(path)

    def _package(self, task_id):
        path = None
        adopted = False
        old = None
        try:
            with self.sessions() as db:
                task = db.get(ResumeExportTask, task_id)
                if not self._valid(db, task):
                    db.commit()
                    return
                items = db.scalars(select(ResumeExportItem).where(ResumeExportItem.task_id == task_id)).all()
                rows = [(i.student_id, i.snapshot_json['user']['real_name'], i.status, i.error_message, i.file_path, i.filename) for i in items]
            success = [row for row in rows if row[2] == 'completed']
            if success:
                output = BytesIO()
                manifest = StringIO(newline='')
                writer = csv.writer(manifest)
                writer.writerow(['student_id', 'name', 'status', 'error'])
                for row in rows:
                    writer.writerow([csvsafe(value) for value in row[:4]])
                with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
                    for row in success:
                        archive.write(resolve_export_file(row[4]), row[5])
                    archive.writestr('manifest.csv', manifest.getvalue().encode('utf-8-sig'))
                path = atomic_file(output.getvalue(), '.zip')
            with self.sessions() as db:
                task = db.get(ResumeExportTask, task_id)
                if self._valid(db, task) and task.status in ('queued', 'processing'):
                    previous = task.archive_path
                    status = ('completed' if len(success) == len(rows) else 'partial') if success else 'failed'
                    changed = db.execute(update(ResumeExportTask).where(
                        ResumeExportTask.id == task_id,
                        ResumeExportTask.status.in_(['queued', 'processing'])
                    ).values(archive_path=path, status=status, error_message=None if success else '所有简历均生成失败，请重试。')).rowcount
                    if changed:
                        self._event(db, task, status)
                    db.commit()
                    adopted = bool(changed)
                    if adopted:
                        old = previous
                else:
                    db.commit()
        except Exception as exc:
            logger.warning('resume_export_package_failed task_id=%s error_type=%s', task_id, type(exc).__name__)
            with self.sessions() as db:
                task = db.get(ResumeExportTask, task_id)
                if self._valid(db, task):
                    db.execute(update(ResumeExportTask).where(ResumeExportTask.id == task_id, ResumeExportTask.status.in_(['queued', 'processing'])).values(status='failed', error_message='压缩包生成失败，请重试。'))
                db.commit()
        finally:
            discard_file(old if adopted else path)
