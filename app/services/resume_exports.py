"""Snapshot and bounded filesystem operations for durable teacher exports."""
from copy import deepcopy
from datetime import datetime
from pathlib import Path, PureWindowsPath
from sqlalchemy import select
from app.config import settings
from app.models import ResumeExportItem, StudentProfile


def snapshot_student(user, profile):
    allowed = bool(profile and profile.share_contacts)
    return dict(user=dict(id=user.id, real_name=user.real_name), profile={
        key: deepcopy(getattr(profile, key, '' if key == 'summary' else []) or ('' if key == 'summary' else []))
        for key in ('summary', 'education_json', 'skills_json', 'projects_json', 'internships_json', 'awards_json')
    }, contact=dict(allowed=allowed, revision=getattr(profile, 'contact_revision', 0) or 0,
                    phone=(profile.phone or '') if allowed else '', email=(profile.email or '') if allowed else ''))


def export_root():
    return (settings.data_dir / 'resume_exports').resolve()


def resolve_export_file(relative):
    if not relative or Path(relative).is_absolute() or PureWindowsPath(relative).is_absolute() or PureWindowsPath(relative).drive:
        raise ValueError('Invalid export path')
    path = (export_root() / relative).resolve()
    if not path.is_relative_to(export_root()) or path == export_root() or '..' in PureWindowsPath(relative).parts:
        raise ValueError('Invalid export path')
    return path


def contacts_current(db, task):
    for item in db.scalars(select(ResumeExportItem).where(ResumeExportItem.task_id == task.id)):
        contact = item.snapshot_json.get('contact', {})
        if contact.get('allowed'):
            profile = db.get(StudentProfile, item.student_id, populate_existing=True)
            if (profile is None or not profile.share_contacts or profile.contact_revision != contact['revision']
                    or (profile.phone or '') != contact['phone'] or (profile.email or '') != contact['email']):
                return False
    return True


def discard_file(relative):
    """Retain a persisted reference when deletion fails, so cleanup can retry."""
    if not relative:
        return True
    try:
        resolve_export_file(relative).unlink(missing_ok=True)
        return True
    except (OSError, ValueError):
        return False


def cleanup_task_files(db, task):
    if discard_file(task.archive_path):
        task.archive_path = None
    scrub = task.status in ('expired', 'invalidated') or task.expires_at <= datetime.utcnow()
    for item in db.scalars(select(ResumeExportItem).where(ResumeExportItem.task_id == task.id)):
        if discard_file(item.file_path):
            item.file_path = None
        if scrub:
            item.snapshot_json = {'user': deepcopy(item.snapshot_json.get('user', {}))}
    if scrub:
        task.job_snapshot = {}
