from types import SimpleNamespace
import pytest
from app.services.resume_exports import snapshot_student, resolve_export_file

def test_snapshot_redacts_contacts_and_is_detached():
    p = SimpleNamespace(summary='真实', education_json=[], skills_json=[], projects_json=[], internships_json=[], awards_json=[], phone='123', email='x@y', share_contacts=False, contact_revision=2)
    snap = snapshot_student(SimpleNamespace(id=1, real_name='学生'), p)
    assert snap['contact'] == dict(allowed=False, revision=2, phone='', email='')
    p.skills_json.append({'name': 'Python'})
    assert snap['profile']['skills_json'] == []

@pytest.mark.parametrize('path', ['../escape', '/absolute', 'C:\\private', '..\\escape'])
def test_path_escape_rejected(path):
    with pytest.raises(ValueError):
        resolve_export_file(path)
